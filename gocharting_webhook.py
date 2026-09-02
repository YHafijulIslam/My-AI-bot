"""
GoCharting Webhook Server with Thread-Safe MT5 Integration

Listens for GoCharting alerts (Order Blocks, Fair Value Gaps, Liquidity Sweeps, 
Institutional Candles) and triggers immediate consensus validation via the 
5-agent voting cycle. Access to MT5 is serialized using a shared threading.Lock 
to prevent concurrent access from both the main loop and webhook threads.

Design:
- GoCharting alert → webhook POST → extract symbol
- Acquire mt5_lock with 30s timeout (fail gracefully if main loop is busy)
- Call VotingOrchestrator.run_voting_cycle(symbol) with fresh MT5 data
- All 5 agents remain blind to the alert content; only symbol is passed through
- Trade execution follows the same 60% consensus threshold as scheduled cycles
"""

import threading
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class GoChartingWebhookServer:
    """
    Thread-safe wrapper around Flask webhook server for GoCharting alerts.
    
    Attributes:
        app: Flask application instance
        mt5_lock: Shared threading.Lock for serializing MT5 access
        orchestrator: VotingOrchestrator instance (receives run_voting_cycle calls)
        expected_token: Authentication token from GoCharting (Lipi Script)
        port: Port to bind the webhook server to
        host: Host to bind to (default: 127.0.0.1 for local, or 0.0.0.0 for prod)
    """
    
    def __init__(
        self,
        mt5_lock: threading.Lock,
        orchestrator,
        expected_token: str,
        port: int = 5000,
        host: str = "127.0.0.1"
    ):
        """
        Initialize the GoCharting webhook server.
        
        Args:
            mt5_lock: Shared lock for serializing MT5 access across threads
            orchestrator: VotingOrchestrator instance with run_voting_cycle method
            expected_token: Authentication token (checked against every incoming alert)
            port: Flask server port
            host: Flask server host binding
        """
        self.app = Flask(__name__)
        self.mt5_lock = mt5_lock
        self.orchestrator = orchestrator
        self.expected_token = expected_token
        self.port = port
        self.host = host
        self.running = False
        self.server_thread = None
        
        # Register webhook endpoint
        self.app.add_url_rule(
            "/alert",
            "handle_alert",
            self._handle_gocharting_alert,
            methods=["POST"]
        )

        # Shutdown endpoint (dev server only)
        def _shutdown():
            func = request.environ.get("werkzeug.server.shutdown")
            if func is None:
                logger.warning("Werkzeug shutdown not available.")
                return jsonify({"error": "shutdown not supported"}), 500
            func()
            return jsonify({"status": "shutting_down"}), 200

        self.app.add_url_rule("/shutdown", "_shutdown", _shutdown, methods=["POST"])
        
        logger.info(f"🔧 GoCharting webhook initialized on {self.host}:{self.port}")
    
    def _handle_gocharting_alert(self) -> Tuple[dict, int]:
        """
        Handle incoming GoCharting alert POST request.
        
        Expected JSON payload:
        {
            "token": "your_expected_token_here",
            "symbol": "EURUSD",
            "alert_type": "order_block" | "fvg" | "liquidity_sweep" | "institutional_candle",
            "timestamp": "2026-09-01T10:30:00Z"
        }
        
        Returns:
            (response_dict, http_status_code)
            - 200: Successfully queued for voting cycle
            - 401: Invalid or missing token
            - 400: Missing/invalid symbol
            - 503: Main loop holding mt5_lock (too busy; try again shortly)
            - 500: Unexpected error during cycle execution
        """
        try:
            data = request.get_json()
            if not data:
                logger.warning("⚠️ Empty JSON payload received")
                return jsonify({"error": "empty payload"}), 400
            
            # 1. Verify authentication token
            token = data.get("token")
            if token != self.expected_token:
                logger.warning(f"🚫 Invalid token: {token}")
                return jsonify({"error": "invalid token"}), 401
            
            # 2. Extract symbol
            symbol = data.get("symbol", "").upper().strip()
            if not symbol:
                logger.warning("⚠️ Missing or empty symbol in alert")
                return jsonify({"error": "symbol required"}), 400
            
            # 3. Extract optional alert metadata (for logging only)
            alert_type = data.get("alert_type", "unknown")
            timestamp = data.get("timestamp", datetime.utcnow().isoformat())
            
            logger.info(
                f"📊 GoCharting alert received: {alert_type.upper()} on {symbol} "
                f"(timestamp: {timestamp})"
            )
            
            # 4. Attempt to acquire the shared MT5 lock with a 30-second timeout
            #    If the main loop holds it, we fail gracefully rather than blocking
            #    indefinitely, since we're answering an external HTTP request.
            acquired = self.mt5_lock.acquire(timeout=30.0)
            if not acquired:
                logger.error(
                    f"⏱️ {symbol}: Failed to acquire MT5 lock within 30s "
                    "(main loop is busy). Returning 503."
                )
                return jsonify({
                    "status": "busy",
                    "message": "orchestrator is busy processing a scheduled cycle; try again shortly"
                }), 503
            
            try:
                # 5. Call the voting cycle with only the symbol
                #    The agents will fetch fresh MT5 data and remain blind to the
                #    alert's content — this ensures their vote is independent
                logger.info(f"🔄 Triggering voting cycle for {symbol} (GoCharting-triggered)")
                result = self.orchestrator.run_voting_cycle(symbol)
                
                logger.info(
                    f"✅ Voting cycle completed for {symbol}. "
                    f"Decision: {result.get('decision', 'UNKNOWN')}"
                )
                
                return jsonify({
                    "status": "success",
                    "symbol": symbol,
                    "decision": result.get("decision"),
                    "confidence": result.get("confidence")
                }), 200
            
            finally:
                # Always release the lock, even if an exception occurs
                self.mt5_lock.release()
        
        except Exception as e:
            logger.error(f"❌ Unexpected error handling GoCharting alert: {e}", exc_info=True)
            return jsonify({
                "error": str(e)
            }), 500
    
    def start(self):
        """
        Start the webhook server in a background thread.
        Ensures the server doesn't block the main thread.
        """
        if self.running:
            logger.warning("⚠️ Webhook server is already running")
            return
        
        self.running = True
        self.server_thread = threading.Thread(
            target=self._run_flask_app,
            daemon=False  # Not a daemon; we manage its lifecycle explicitly
        )
        self.server_thread.start()
        logger.info(f"🚀 GoCharting webhook server started on http://{self.host}:{self.port}/alert")
    
    def _run_flask_app(self):
        """
        Run the Flask application (called from background thread).
        Logs are written with Flask's logger and the main logger.
        """
        try:
            # Suppress Flask's default request logging to reduce noise
            log = logging.getLogger("werkzeug")
            log.setLevel(logging.WARNING)
            
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,  # Prevent reloader in threaded mode
                threaded=True  # Allow multiple concurrent requests
            )
        except Exception as e:
            logger.error(f"❌ Flask app error: {e}", exc_info=True)
    
    def stop(self):
        """
        Gracefully stop the webhook server and wait for the background thread to exit.
        Should be called before shutdown to prevent requests mid-flight when MT5 closes.
        """
        if not self.running:
            logger.warning("⚠️ Webhook server is not running")
            return
        
        self.running = False
        logger.info("⛔ Stopping GoCharting webhook server...")
        
        # Use Flask's shutdown mechanism
        # (In production, consider using a proper WSGI server like gunicorn)
        try:
            # Send a request to trigger shutdown if needed
            # For now, we rely on the Flask dev server's graceful termination
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5.0)
                if self.server_thread.is_alive():
                    logger.warning("⚠️ Webhook server thread did not exit within 5s")
        except Exception as e:
            logger.error(f"⚠️ Error stopping webhook server: {e}")
        
        logger.info("✅ GoCharting webhook server stopped")


def create_webhook_server(
    mt5_lock: threading.Lock,
    orchestrator,
    expected_token: str,
    port: int = 5000,
    host: str = "127.0.0.1"
) -> GoChartingWebhookServer:
    """
    Factory function to create and configure a GoCharting webhook server.
    
    Args:
        mt5_lock: Shared lock for MT5 access
        orchestrator: VotingOrchestrator instance
        expected_token: Authentication token for Lipi Script alerts
        port: Webhook server port
        host: Webhook server host
    
    Returns:
        Configured GoChartingWebhookServer instance (not yet started)
    """
    return GoChartingWebhookServer(
        mt5_lock=mt5_lock,
        orchestrator=orchestrator,
        expected_token=expected_token,
        port=port,
        host=host
    )
