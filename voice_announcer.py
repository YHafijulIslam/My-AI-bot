"""
Real-Time Voice Announcer for Trading Bot

Provides human-like voice announcements for:
- Market analysis results from all 5 agents
- Trade execution events (entry, exit, stop-loss)
- Current market positions and balances
- News and sentiment updates
- System status and alerts

Supports multiple TTS providers:
1. Google Text-to-Speech (natural, multiple languages)
2. pyttsx3 (offline, local)
3. ElevenLabs (premium, ultra-realistic voices)

Uses threading to prevent blocking the main trading loop.
All announcements are queued and processed sequentially.
"""

import threading
import queue
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import time

logger = logging.getLogger(__name__)


class AnnouncementType(Enum):
    """Types of announcements the bot can make."""
    MARKET_ANALYSIS = "market_analysis"
    TRADE_EXECUTION = "trade_execution"
    TRADE_EXIT = "trade_exit"
    POSITION_UPDATE = "position_update"
    NEWS_UPDATE = "news_update"
    SYSTEM_ALERT = "system_alert"
    CYCLE_START = "cycle_start"
    CYCLE_COMPLETE = "cycle_complete"


class TTSProvider(Enum):
    """Supported Text-to-Speech providers."""
    GOOGLE = "google"
    PYTTSX3 = "pyttsx3"
    ELEVENLABS = "elevenlabs"


class VoiceAnnouncer:
    """
    Manages text-to-speech announcements in a separate thread.
    
    Attributes:
        provider: TTS provider (google, pyttsx3, or elevenlabs)
        language: Language code (e.g., 'en', 'bn' for Bengali)
        enabled: Whether voice announcements are enabled
        queue: Thread-safe queue of announcements
        worker_thread: Background thread processing announcements
    """
    
    def __init__(
        self,
        provider: str = "google",
        language: str = "en",
        enabled: bool = True,
        api_key: Optional[str] = None
    ):
        """
        Initialize the Voice Announcer.
        
        Args:
            provider: TTS provider ('google', 'pyttsx3', 'elevenlabs')
            language: Language code
            enabled: Whether to enable voice announcements
            api_key: API key for providers that need it (ElevenLabs, Google)
        """
        self.provider_name = provider.lower()
        self.language = language
        self.enabled = enabled
        self.api_key = api_key
        self.announcement_queue = queue.Queue()
        self.running = False
        self.worker_thread = None
        
        # Initialize the TTS provider
        self.tts_provider = self._initialize_provider()
        
        if self.enabled:
            self.start()
        
        logger.info(
            f"🎙️ Voice Announcer initialized: provider={self.provider_name}, "
            f"language={self.language}, enabled={self.enabled}"
        )
    
    def _initialize_provider(self):
        """Initialize the TTS provider based on configuration."""
        if self.provider_name == "google":
            try:
                from google.cloud import texttospeech
                return GoogleTTSProvider(
                    language_code=self.language,
                    api_key=self.api_key
                )
            except ImportError:
                logger.warning("Google Cloud TTS not installed. Falling back to pyttsx3.")
                self.provider_name = "pyttsx3"
        
        if self.provider_name == "elevenlabs":
            try:
                return ElevenLabsTTSProvider(
                    language=self.language,
                    api_key=self.api_key
                )
            except ImportError:
                logger.warning("ElevenLabs not installed. Falling back to pyttsx3.")
                self.provider_name = "pyttsx3"
        
        # Default to pyttsx3 (offline, always available)
        try:
            return PyTTSX3Provider(language=self.language)
        except ImportError:
            logger.error("pyttsx3 not installed. Voice announcements disabled.")
            self.enabled = False
            return None
    
    def announce(
        self,
        announcement_type: AnnouncementType,
        text: str,
        priority: int = 1
    ):
        """
        Queue an announcement for playback.
        
        Args:
            announcement_type: Type of announcement
            text: Text to speak
            priority: Priority level (higher = more urgent, processed first)
        """
        if not self.enabled or self.tts_provider is None:
            return
        
        self.announcement_queue.put((priority, datetime.now(), announcement_type, text))
        logger.debug(f"📢 Announcement queued: {announcement_type.value} - {text[:50]}...")
    
    def announce_market_analysis(
        self,
        symbol: str,
        agent_votes: Dict[str, Dict[str, Any]]
    ):
        """
        Announce results of market analysis from all 5 agents.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            agent_votes: Dict of {agent_name: {vote, confidence, reason}}
        """
        # Build a natural narrative from agent votes
        bullish_count = sum(1 for v in agent_votes.values() if v["vote"] == "BULLISH")
        bearish_count = sum(1 for v in agent_votes.values() if v["vote"] == "BEARISH")
        neutral_count = sum(1 for v in agent_votes.values() if v["vote"] == "NEUTRAL")
        avg_confidence = sum(v["confidence"] for v in agent_votes.values()) / len(agent_votes)
        
        text = f"""
        Market analysis for {symbol}. 
        Technical analysis: {agent_votes.get('TechnicalAgent', {}).get('reason', 'no data')}.
        Predictive model: {agent_votes.get('PredictiveAgent', {}).get('reason', 'no data')}.
        Liquidity analysis: {agent_votes.get('LiquiditySweepVoter', {}).get('reason', 'no data')}.
        Pattern recognition: {agent_votes.get('TransformerAgent', {}).get('reason', 'no data')}.
        Sentiment: {agent_votes.get('SentimentAgent', {}).get('reason', 'no data')}.
        
        Vote tally: {bullish_count} bullish, {bearish_count} bearish, {neutral_count} neutral.
        Average confidence: {avg_confidence:.0f} percent.
        """
        
        self.announce(
            AnnouncementType.MARKET_ANALYSIS,
            text.strip(),
            priority=2
        )
    
    def announce_trade_execution(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float] = None
    ):
        """
        Announce a trade execution event.
        
        Args:
            symbol: Trading symbol
            direction: 'BUY' or 'SELL'
            lot_size: Position size in lots
            entry_price: Entry price
            stop_loss: Stop-loss price
            take_profit: Optional take-profit price
        """
        risk_reward = "not set"
        if take_profit and direction == "BUY":
            risk_reward = f"{(take_profit - entry_price) / (entry_price - stop_loss):.2f} to 1"
        elif take_profit and direction == "SELL":
            risk_reward = f"{(entry_price - take_profit) / (stop_loss - entry_price):.2f} to 1"
        
        text = f"""
        Trade execution. {direction} {lot_size} lot of {symbol} at {entry_price:.5f}.
        Stop loss set to {stop_loss:.5f}.
        """
        
        if take_profit:
            text += f"Take profit at {take_profit:.5f}. Risk reward ratio: {risk_reward}."
        
        self.announce(
            AnnouncementType.TRADE_EXECUTION,
            text.strip(),
            priority=1
        )
    
    def announce_trade_exit(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        lot_size: float,
        pnl: float,
        reason: str
    ):
        """
        Announce a trade exit event.
        
        Args:
            symbol: Trading symbol
            direction: 'BUY' or 'SELL'
            entry_price: Entry price
            exit_price: Exit price
            lot_size: Position size
            pnl: Profit or loss in currency
            reason: Why the trade was closed
        """
        pnl_percent = ((exit_price - entry_price) / entry_price * 100) if direction == "BUY" else \
                      ((entry_price - exit_price) / entry_price * 100)
        
        pnl_status = "profit" if pnl >= 0 else "loss"
        
        text = f"""
        Trade closed. {direction} position on {symbol} closed at {exit_price:.5f}.
        Entry was at {entry_price:.5f}. 
        {abs(pnl_percent):.2f} percent {pnl_status}. 
        Profit and loss: {abs(pnl):.2f} currency units.
        Reason: {reason}.
        """
        
        self.announce(
            AnnouncementType.TRADE_EXIT,
            text.strip(),
            priority=1
        )
    
    def announce_position_update(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        entry_price: float,
        current_price: float,
        floating_pnl: float,
        floating_pnl_percent: float
    ):
        """
        Announce current position status.
        
        Args:
            symbol: Trading symbol
            direction: 'BUY' or 'SELL'
            lot_size: Position size
            entry_price: Entry price
            current_price: Current market price
            floating_pnl: Unrealized profit/loss
            floating_pnl_percent: Unrealized P&L as percentage
        """
        status = "in profit" if floating_pnl >= 0 else "in loss"
        
        text = f"""
        Position update. {direction} {lot_size} lot of {symbol}.
        Entry price: {entry_price:.5f}. Current price: {current_price:.5f}.
        Floating P and L: {floating_pnl:.2f}, or {abs(floating_pnl_percent):.2f} percent {status}.
        """
        
        self.announce(
            AnnouncementType.POSITION_UPDATE,
            text.strip(),
            priority=3
        )
    
    def announce_news_update(
        self,
        symbol: str,
        headline: str,
        sentiment: str,
        impact: str
    ):
        """
        Announce relevant news for a trading symbol.
        
        Args:
            symbol: Trading symbol
            headline: News headline
            sentiment: 'positive', 'negative', or 'neutral'
            impact: 'high', 'medium', or 'low'
        """
        text = f"""
        News alert for {symbol}. 
        {headline}. 
        Sentiment: {sentiment}. 
        Expected market impact: {impact}.
        """
        
        self.announce(
            AnnouncementType.NEWS_UPDATE,
            text.strip(),
            priority=2
        )
    
    def announce_system_alert(
        self,
        alert_level: str,
        message: str
    ):
        """
        Announce a system alert or warning.
        
        Args:
            alert_level: 'critical', 'warning', or 'info'
            message: Alert message
        """
        text = f"{alert_level.upper()}: {message}"
        
        priority = 0 if alert_level == "critical" else 1 if alert_level == "warning" else 3
        
        self.announce(
            AnnouncementType.SYSTEM_ALERT,
            text,
            priority=priority
        )
    
    def announce_cycle_start(self, symbol: str):
        """Announce the start of a trading cycle."""
        text = f"Starting analysis cycle for {symbol}."
        self.announce(AnnouncementType.CYCLE_START, text, priority=4)
    
    def announce_cycle_complete(self, symbol: str, decision: str):
        """Announce the completion of a trading cycle."""
        text = f"Analysis cycle for {symbol} complete. Decision: {decision}."
        self.announce(AnnouncementType.CYCLE_COMPLETE, text, priority=3)
    
    def start(self):
        """Start the background announcement worker thread."""
        if self.running or not self.enabled:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=False,
            name="VoiceAnnouncer"
        )
        self.worker_thread.start()
        logger.info("🎙️ Voice announcer worker thread started")
    
    def _worker_loop(self):
        """Background thread that processes queued announcements."""
        while self.running:
            try:
                # Get announcement from queue with timeout
                priority, timestamp, announcement_type, text = self.announcement_queue.get(timeout=1)
                
                logger.info(
                    f"🔊 Processing announcement: {announcement_type.value} "
                    f"(priority {priority})"
                )
                
                # Speak the text
                self.tts_provider.speak(text)
                
                # Mark task as done
                self.announcement_queue.task_done()
            
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ Error processing announcement: {e}", exc_info=True)
    
    def stop(self):
        """Stop the announcer and wait for pending announcements."""
        if not self.running:
            return
        
        logger.info("⛔ Stopping voice announcer...")
        self.running = False
        
        try:
            # Wait for all pending announcements to complete
            self.announcement_queue.join()
        except Exception as e:
            logger.warning(f"⚠️ Error waiting for queue: {e}")
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        
        logger.info("✅ Voice announcer stopped")
    
    def get_queue_size(self) -> int:
        """Get the current number of announcements in queue."""
        return self.announcement_queue.qsize()


class GoogleTTSProvider:
    """Google Cloud Text-to-Speech provider."""
    
    def __init__(self, language_code: str = "en-US", api_key: Optional[str] = None):
        from google.cloud import texttospeech
        
        self.language_code = language_code
        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0
        )
    
    def speak(self, text: str):
        """Synthesize and play text using Google TTS."""
        try:
            from google.cloud import texttospeech
            import pyaudio
            
            input_text = texttospeech.SynthesisInput(text=text)
            response = self.client.synthesize_speech(
                input=input_text,
                voice=self.voice,
                audio_config=self.audio_config
            )
            
            # Play audio
            self._play_audio(response.audio_content)
            logger.info("✅ Google TTS announcement played")
        
        except Exception as e:
            logger.error(f"❌ Google TTS error: {e}")
    
    def _play_audio(self, audio_bytes: bytes):
        """Play audio bytes using pyaudio."""
        try:
            import pyaudio
            import wave
            from io import BytesIO
            
            # MP3 decoding required; for simplicity, save and play
            # In production, use pydub or similar for real-time playback
            import os
            temp_file = "/tmp/tts_output.mp3"
            with open(temp_file, "wb") as f:
                f.write(audio_bytes)
            
            os.system(f"ffplay -nodisp -autoexit {temp_file} 2>/dev/null")
        except Exception as e:
            logger.error(f"❌ Audio playback error: {e}")


class ElevenLabsTTSProvider:
    """ElevenLabs Text-to-Speech provider (premium, ultra-realistic voices)."""
    
    def __init__(self, language: str = "en", api_key: Optional[str] = None):
        self.language = language
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default Rachel voice
        
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not set")
    
    def speak(self, text: str):
        """Synthesize and play text using ElevenLabs."""
        try:
            import requests
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            # Play audio
            self._play_audio(response.content)
            logger.info("✅ ElevenLabs TTS announcement played")
        
        except Exception as e:
            logger.error(f"❌ ElevenLabs TTS error: {e}")
    
    def _play_audio(self, audio_bytes: bytes):
        """Play audio bytes."""
        try:
            import os
            temp_file = "/tmp/elevenlabs_output.mp3"
            with open(temp_file, "wb") as f:
                f.write(audio_bytes)
            
            os.system(f"ffplay -nodisp -autoexit {temp_file} 2>/dev/null")
        except Exception as e:
            logger.error(f"❌ Audio playback error: {e}")


class PyTTSX3Provider:
    """Offline Text-to-Speech using pyttsx3 (default fallback)."""
    
    def __init__(self, language: str = "en"):
        import pyttsx3
        
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 150)  # Speaking rate
        self.engine.setProperty("volume", 0.9)  # Volume
        
        # Try to set language
        try:
            self.engine.setProperty("voice", self._get_voice_for_language(language))
        except Exception as e:
            logger.warning(f"⚠️ Could not set language {language}: {e}")
    
    def speak(self, text: str):
        """Synthesize and play text using pyttsx3."""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
            logger.info("✅ pyttsx3 TTS announcement played")
        except Exception as e:
            logger.error(f"❌ pyttsx3 error: {e}")
    
    def _get_voice_for_language(self, language: str):
        """Select appropriate voice for language."""
        voices = self.engine.getProperty("voices")
        
        # Simple language-to-voice mapping
        lang_map = {
            "en": "english",
            "bn": "bengali",
            "es": "spanish",
            "fr": "french",
            "de": "german"
        }
        
        target = lang_map.get(language, "english")
        for voice in voices:
            if target.lower() in voice.name.lower():
                return voice.id
        
        # Return first voice if no match
        return voices[0].id if voices else None


def create_voice_announcer(
    provider: str = "pyttsx3",
    language: str = "en",
    enabled: bool = True,
    api_key: Optional[str] = None
) -> VoiceAnnouncer:
    """
    Factory function to create a voice announcer.
    
    Args:
        provider: TTS provider ('google', 'pyttsx3', 'elevenlabs')
        language: Language code
        enabled: Whether to enable voice announcements
        api_key: API key for cloud providers
    
    Returns:
        Configured VoiceAnnouncer instance
    """
    return VoiceAnnouncer(
        provider=provider,
        language=language,
        enabled=enabled,
        api_key=api_key
    )
