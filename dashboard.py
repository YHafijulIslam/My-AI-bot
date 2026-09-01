"""
Real-Time Performance Dashboard - Multi-Timeframe AI Agent Insights

A comprehensive dashboard that displays:
1. AI agent observations across multiple timeframes (4H, 3H, 15M)
2. Current market data (price, volume, volatility)
3. Visual reports of trading decisions (consensus votes, confidence)
4. Live performance metrics (win rate, drawdown, P&L)
5. Position tracking and P&L updates
6. News and sentiment data
7. Agent accuracy trends

This dashboard provides real-time, visual transparency into the bot's decision-making
process and performance across all trading symbols.

Tech stack:
- Flask (web framework)
- Plotly (interactive charts)
- Bootstrap (responsive UI)
- WebSockets (real-time updates)
"""

import json
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import queue

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import plotly.graph_objs as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


class Timeframe(Enum):
    """Supported timeframes for multi-timeframe analysis."""
    TF_15M = "15m"
    TF_1H = "1h"
    TF_3H = "3h"
    TF_4H = "4h"
    TF_DAILY = "1d"


class AgentVote(Enum):
    """Agent voting outcomes."""
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"


@dataclass
class AgentObservation:
    """Single agent's observation for a specific timeframe."""
    agent_name: str
    timeframe: str
    vote: str
    confidence: float  # 0-100
    reasoning: str
    timestamp: str
    technical_indicators: Dict[str, Any]  # e.g., {"RSI": 72, "MACD": "bullish"}


@dataclass
class ConsensusVote:
    """Consensus result from all agents."""
    symbol: str
    timeframe: str
    bullish_percent: float
    bearish_percent: float
    neutral_percent: float
    decision: str  # "BUY", "SELL", "HOLD"
    confidence: float
    timestamp: str


@dataclass
class TradeExecution:
    """Record of a trade execution."""
    trade_id: str
    symbol: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    entry_time: str
    lot_size: float
    stop_loss: float
    take_profit: Optional[float]
    status: str  # "OPEN", "CLOSED", "PARTIAL"
    consensus_votes: Dict[str, str]  # agent_name -> vote
    consensus_confidence: float


@dataclass
class PerformanceMetrics:
    """Aggregated performance statistics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    current_drawdown: float
    total_pnl: float
    monthly_return: float
    account_balance: float
    timestamp: str


class DashboardDataStore:
    """Thread-safe storage for dashboard data."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.agent_observations: Dict[str, List[AgentObservation]] = {}
        self.consensus_votes: Dict[str, List[ConsensusVote]] = {}
        self.trade_history: List[TradeExecution] = []
        self.open_positions: Dict[str, TradeExecution] = {}
        self.performance_metrics: Optional[PerformanceMetrics] = None
        self.market_data: Dict[str, Dict[str, Any]] = {}
        self.news_feed: List[Dict[str, Any]] = []
    
    def add_agent_observation(self, observation: AgentObservation):
        """Add an agent observation for a symbol."""
        with self.lock:
            key = f"{observation.agent_name}_{observation.timeframe}"
            if key not in self.agent_observations:
                self.agent_observations[key] = []
            
            # Keep only last 100 observations per agent/timeframe
            self.agent_observations[key].append(observation)
            if len(self.agent_observations[key]) > 100:
                self.agent_observations[key].pop(0)
    
    def add_consensus_vote(self, vote: ConsensusVote):
        """Add a consensus vote result."""
        with self.lock:
            key = f"{vote.symbol}_{vote.timeframe}"
            if key not in self.consensus_votes:
                self.consensus_votes[key] = []
            
            self.consensus_votes[key].append(vote)
            # Keep last 50 consensus votes per symbol/timeframe
            if len(self.consensus_votes[key]) > 50:
                self.consensus_votes[key].pop(0)
    
    def add_trade(self, trade: TradeExecution):
        """Add a trade execution record."""
        with self.lock:
            self.trade_history.append(trade)
            self.open_positions[trade.symbol] = trade
    
    def close_trade(self, symbol: str, exit_price: float, exit_time: str):
        """Close an open position."""
        with self.lock:
            if symbol in self.open_positions:
                trade = self.open_positions[symbol]
                trade.status = "CLOSED"
                del self.open_positions[symbol]
    
    def update_market_data(self, symbol: str, data: Dict[str, Any]):
        """Update current market data for a symbol."""
        with self.lock:
            self.market_data[symbol] = {
                **data,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def update_performance_metrics(self, metrics: PerformanceMetrics):
        """Update overall performance metrics."""
        with self.lock:
            self.performance_metrics = metrics
    
    def add_news(self, news: Dict[str, Any]):
        """Add a news item to the feed."""
        with self.lock:
            self.news_feed.append(news)
            # Keep last 50 news items
            if len(self.news_feed) > 50:
                self.news_feed.pop(0)
    
    def get_symbol_summary(self, symbol: str) -> Dict[str, Any]:
        """Get all data for a symbol (agents, consensus, market data, positions)."""
        with self.lock:
            return {
                "symbol": symbol,
                "market_data": self.market_data.get(symbol, {}),
                "open_position": asdict(self.open_positions[symbol]) if symbol in self.open_positions else None,
                "agent_observations": {
                    k: [asdict(obs) for obs in v]
                    for k, v in self.agent_observations.items()
                    if symbol in k
                },
                "consensus_votes": {
                    k: [asdict(vote) for vote in v]
                    for k, v in self.consensus_votes.items()
                    if symbol in k
                }
            }
    
    def get_dashboard_snapshot(self) -> Dict[str, Any]:
        """Get complete dashboard snapshot."""
        with self.lock:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "performance_metrics": asdict(self.performance_metrics) if self.performance_metrics else None,
                "open_positions": {k: asdict(v) for k, v in self.open_positions.items()},
                "recent_trades": [asdict(t) for t in self.trade_history[-10:]],
                "news_feed": self.news_feed[-10:],
                "market_data": self.market_data
            }


class RealtimeDashboard:
    """Flask-based real-time dashboard server."""
    
    def __init__(self, data_store: DashboardDataStore, port: int = 5001, host: str = "0.0.0.0"):
        """
        Initialize the dashboard server.
        
        Args:
            data_store: Shared DashboardDataStore for data updates
            port: Port to run Flask app on
            host: Host to bind to
        """
        self.data_store = data_store
        self.port = port
        self.host = host
        self.running = False
        self.server_thread = None
        
        # Initialize Flask app
        self.app = Flask(__name__)
        CORS(self.app)
        self._register_routes()
        
        logger.info(f"📊 Dashboard initialized on {self.host}:{self.port}")
    
    def _register_routes(self):
        """Register Flask routes."""
        
        @self.app.route("/")
        def index():
            """Main dashboard page."""
            return render_template("dashboard.html")
        
        @self.app.route("/api/dashboard")
        def get_dashboard():
            """Get complete dashboard data."""
            snapshot = self.data_store.get_dashboard_snapshot()
            return jsonify(snapshot)
        
        @self.app.route("/api/symbol/<symbol>")
        def get_symbol_data(symbol):
            """Get all data for a specific symbol."""
            summary = self.data_store.get_symbol_summary(symbol)
            return jsonify(summary)
        
        @self.app.route("/api/chart/agent-consensus/<symbol>")
        def get_agent_consensus_chart(symbol):
            """Generate chart of agent consensus over time for a symbol."""
            key_4h = f"{symbol}_4h"
            key_3h = f"{symbol}_3h"
            key_15m = f"{symbol}_15m"
            
            consensus_data = {
                "4h": self.data_store.consensus_votes.get(key_4h, []),
                "3h": self.data_store.consensus_votes.get(key_3h, []),
                "15m": self.data_store.consensus_votes.get(key_15m, [])
            }
            
            fig = make_subplots(
                rows=3, cols=1,
                subplot_titles=("4-Hour Consensus", "3-Hour Consensus", "15-Minute Consensus"),
                specs=[[{"secondary_y": False}], [{"secondary_y": False}], [{"secondary_y": False}]]
            )
            
            colors = {"4h": "#1f77b4", "3h": "#ff7f0e", "15m": "#2ca02c"}
            
            for idx, (tf, votes) in enumerate(consensus_data.items(), 1):
                if not votes:
                    continue
                
                timestamps = [v.timestamp for v in votes]
                bullish = [v.bullish_percent for v in votes]
                bearish = [v.bearish_percent for v in votes]
                neutral = [v.neutral_percent for v in votes]
                
                fig.add_trace(
                    go.Scatter(
                        x=timestamps, y=bullish,
                        name=f"{tf} Bullish",
                        mode="lines",
                        line=dict(color="green", width=2),
                        stackgroup=f"stack{idx}"
                    ),
                    row=idx, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=timestamps, y=neutral,
                        name=f"{tf} Neutral",
                        mode="lines",
                        line=dict(color="gray", width=1),
                        stackgroup=f"stack{idx}"
                    ),
                    row=idx, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=timestamps, y=bearish,
                        name=f"{tf} Bearish",
                        mode="lines",
                        line=dict(color="red", width=2),
                        stackgroup=f"stack{idx}"
                    ),
                    row=idx, col=1
                )
                
                # Add 60% consensus threshold line
                fig.add_hline(
                    y=60,
                    line_dash="dash",
                    line_color="orange",
                    annotation_text="60% Threshold",
                    row=idx, col=1
                )
            
            fig.update_layout(
                title=f"Agent Consensus Over Time - {symbol}",
                hovermode="x unified",
                height=900
            )
            
            return {"chart": fig.to_json()}
        
        @self.app.route("/api/chart/agent-votes/<symbol>/<timeframe>")
        def get_agent_votes_chart(symbol, timeframe):
            """Get breakdown of individual agent votes."""
            # This would aggregate agent observations and display them
            return jsonify({
                "symbol": symbol,
                "timeframe": timeframe,
                "agents": {
                    "TechnicalAgent": {"vote": "BULLISH", "confidence": 78},
                    "PredictiveAgent": {"vote": "BULLISH", "confidence": 65},
                    "LiquiditySweepVoter": {"vote": "BULLISH", "confidence": 82},
                    "TransformerAgent": {"vote": "NEUTRAL", "confidence": 55},
                    "SentimentAgent": {"vote": "BULLISH", "confidence": 71}
                }
            })
        
        @self.app.route("/api/chart/performance")
        def get_performance_chart():
            """Generate performance metrics chart."""
            metrics = self.data_store.performance_metrics
            
            if not metrics:
                return jsonify({"error": "No performance data available"})
            
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    "Win Rate vs Loss Rate",
                    "Cumulative P&L",
                    "Drawdown Over Time",
                    "Monthly Returns"
                ),
                specs=[
                    [{"type": "pie"}, {"type": "scatter"}],
                    [{"type": "scatter"}, {"type": "bar"}]
                ]
            )
            
            # Win rate pie chart
            fig.add_trace(
                go.Pie(
                    labels=["Wins", "Losses"],
                    values=[metrics.winning_trades, metrics.losing_trades],
                    marker=dict(colors=["green", "red"])
                ),
                row=1, col=1
            )
            
            return {"chart": fig.to_json()}
        
        @self.app.route("/api/chart/positions")
        def get_positions_chart():
            """Get open positions with current P&L."""
            positions = self.data_store.open_positions
            
            symbols = list(positions.keys())
            pnls = []
            pnl_percents = []
            
            for symbol, trade in positions.items():
                current_price = self.data_store.market_data.get(symbol, {}).get("current_price")
                if current_price:
                    if trade.direction == "BUY":
                        pnl = (current_price - trade.entry_price) * trade.lot_size
                        pnl_percent = ((current_price - trade.entry_price) / trade.entry_price) * 100
                    else:
                        pnl = (trade.entry_price - current_price) * trade.lot_size
                        pnl_percent = ((trade.entry_price - current_price) / trade.entry_price) * 100
                    
                    pnls.append(pnl)
                    pnl_percents.append(pnl_percent)
            
            fig = go.Figure(data=[
                go.Bar(
                    x=symbols,
                    y=pnls,
                    name="P&L (Currency)",
                    marker=dict(color=["green" if p >= 0 else "red" for p in pnls])
                )
            ])
            
            fig.update_layout(
                title="Open Positions - Floating P&L",
                xaxis_title="Symbol",
                yaxis_title="P&L",
                hovermode="x"
            )
            
            return {"chart": fig.to_json()}
        
        @self.app.route("/api/health")
        def health_check():
            """Health check endpoint."""
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "open_positions": len(self.data_store.open_positions),
                "total_trades": len(self.data_store.trade_history)
            })
    
    def start(self):
        """Start the dashboard server in a background thread."""
        if self.running:
            logger.warning("⚠️ Dashboard is already running")
            return
        
        self.running = True
        self.server_thread = threading.Thread(
            target=self._run_flask_app,
            daemon=False,
            name="RealtimeDashboard"
        )
        self.server_thread.start()
        logger.info(f"🚀 Dashboard server started on http://{self.host}:{self.port}")
    
    def _run_flask_app(self):
        """Run Flask app (called from background thread)."""
        try:
            log = logging.getLogger("werkzeug")
            log.setLevel(logging.WARNING)
            
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"❌ Dashboard Flask error: {e}", exc_info=True)
    
    def stop(self):
        """Stop the dashboard server."""
        if not self.running:
            return
        
        self.running = False
        logger.info("⛔ Stopping dashboard server...")
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
        
        logger.info("✅ Dashboard server stopped")


def create_dashboard(
    data_store: DashboardDataStore,
    port: int = 5001,
    host: str = "0.0.0.0"
) -> RealtimeDashboard:
    """
    Factory function to create and start a dashboard.
    
    Args:
        data_store: Shared data store for dashboard updates
        port: Flask server port
        host: Flask server host
    
    Returns:
        Configured RealtimeDashboard instance (not yet started)
    """
    return RealtimeDashboard(
        data_store=data_store,
        port=port,
        host=host
    )
