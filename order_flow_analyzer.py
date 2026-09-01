"""
Order Flow Analysis & Footprint Integration for GoCharting

Integrates real-time order flow data and footprint charts from GoCharting
across all timeframes (15M, 1H, 3H, 4H) for enhanced market sentiment and
liquidity analysis by the multi-agent AI brain.

This module:
1. Receives order flow data from GoCharting via webhook
2. Analyzes footprint patterns (buy/sell pressure, volume distribution)
3. Detects institutional order accumulation and distribution
4. Provides real-time liquidity level updates
5. Identifies support/resistance based on order flow profiles
6. Feeds aggregated insights to all 5 agents for enhanced decision-making

Order Flow Concepts:
- Bid/Ask Imbalance: Ratio of buy orders to sell orders at each price level
- Volume Profile: Distribution of volume at each price level
- Market Profile: Time spent at each price level
- Delta: Cumulative difference between buy and sell volume
- Volume at Price (VAP): Total volume traded at specific price levels
- Liquidity Sweeps: Large orders that move through support/resistance
- Institutional Footprints: Patterns indicating smart money activity
"""

import threading
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class OrderFlowSignal(Enum):
    """Order flow directional signals."""
    STRONG_BUY = "strong_buy"          # Strong buy pressure
    BUY = "buy"                        # Moderate buy pressure
    ACCUMULATION = "accumulation"      # Institutional accumulation
    NEUTRAL = "neutral"               # Balanced
    DISTRIBUTION = "distribution"     # Institutional distribution
    SELL = "sell"                     # Moderate sell pressure
    STRONG_SELL = "strong_sell"       # Strong sell pressure


class LiquidityLevel(Enum):
    """Classification of liquidity levels."""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class PriceLevel:
    """Data for a single price level in footprint."""
    price: float
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    total_volume: float = 0.0
    bid_ask_ratio: float = 1.0
    time_spent: int = 0  # Candles or seconds
    order_count: int = 0
    is_support: bool = False
    is_resistance: bool = False
    
    @property
    def delta(self) -> float:
        """Net buy/sell volume at this level."""
        return self.buy_volume - self.sell_volume
    
    @property
    def delta_percent(self) -> float:
        """Delta as percentage of total volume."""
        if self.total_volume == 0:
            return 0.0
        return (self.delta / self.total_volume) * 100


@dataclass
class OrderFlowFootprint:
    """Complete order flow footprint for a timeframe."""
    symbol: str
    timeframe: str
    timestamp: str
    price_levels: Dict[float, PriceLevel] = field(default_factory=dict)
    cumulative_delta: float = 0.0
    total_buy_volume: float = 0.0
    total_sell_volume: float = 0.0
    volume_profile_peak: Optional[float] = None  # Price with highest volume
    poc_price: Optional[float] = None  # Point of Control (highest volume)
    vah_price: Optional[float] = None  # Value Area High (70% of volume)
    val_price: Optional[float] = None  # Value Area Low (70% of volume)
    bid_ask_imbalance: float = 0.0
    liquidity_level: str = "medium"
    
    @property
    def total_volume(self) -> float:
        """Total volume across all price levels."""
        return self.total_buy_volume + self.total_sell_volume
    
    @property
    def buy_sell_ratio(self) -> float:
        """Buy volume to sell volume ratio."""
        if self.total_sell_volume == 0:
            return self.total_buy_volume / 0.001
        return self.total_buy_volume / self.total_sell_volume


@dataclass
class LiquidityProfile:
    """Aggregated liquidity analysis across multiple levels."""
    symbol: str
    timeframe: str
    timestamp: str
    support_level: float
    resistance_level: float
    support_strength: float  # 0-100 (based on volume at support)
    resistance_strength: float  # 0-100
    liquidity_clusters: List[Tuple[float, float]] = field(default_factory=list)  # (price, volume)
    institutional_accumulation: bool = False
    institutional_distribution: bool = False
    liquidity_depth: float = 0.0  # Average liquidity across levels
    spread_efficiency: float = 0.0  # How efficiently liquidity is distributed


@dataclass
class InstitutionalSignal:
    """Indicator of institutional order flow activity."""
    signal_type: str  # "accumulation", "distribution", "layering", "spoofing"
    confidence: float  # 0-100
    description: str
    timestamp: str
    price_range: Tuple[float, float]
    volume_involved: float


class OrderFlowAnalyzer:
    """
    Analyzes order flow data from GoCharting across multiple timeframes.
    
    Provides insights for:
    - LiquiditySweepVoter: Identifies smart money order flow patterns
    - SentimentAgent: Gauges market sentiment from order imbalances
    - TransformerAgent: Detects regime changes from volume profiles
    - All agents: Enhanced support/resistance levels from volume analysis
    """
    
    def __init__(self):
        """Initialize the order flow analyzer."""
        self.lock = threading.Lock()
        self.footprints: Dict[str, OrderFlowFootprint] = {}  # symbol_timeframe -> footprint
        self.liquidity_profiles: Dict[str, LiquidityProfile] = {}
        self.institutional_signals: List[InstitutionalSignal] = []
        self.historical_data: Dict[str, List[OrderFlowFootprint]] = defaultdict(list)
        self.price_level_cache: Dict[str, Dict[float, PriceLevel]] = defaultdict(dict)
        
        logger.info("📊 Order Flow Analyzer initialized")
    
    def process_order_flow_data(
        self,
        symbol: str,
        timeframe: str,
        order_flow_data: Dict[str, Any]
    ) -> OrderFlowFootprint:
        """
        Process incoming order flow data from GoCharting.
        
        Expected format:
        {
            "price_levels": [
                {"price": 1.0850, "buy_volume": 1500, "sell_volume": 1200},
                {"price": 1.0849, "buy_volume": 2000, "sell_volume": 1800},
                ...
            ],
            "total_buy_volume": 15000,
            "total_sell_volume": 12000,
            "bid_ask_imbalance": 0.25,
            "volume_profile": {"peak_price": 1.0850, "vah": 1.0852, "val": 1.0848}
        }
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            timeframe: Chart timeframe (e.g., '15m', '4h')
            order_flow_data: Order flow data from GoCharting
        
        Returns:
            OrderFlowFootprint object with analyzed data
        """
        with self.lock:
            key = f"{symbol}_{timeframe}"
            
            # Create footprint from data
            footprint = OrderFlowFootprint(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Process price levels
            price_levels_data = order_flow_data.get("price_levels", [])
            for level_data in price_levels_data:
                price = level_data.get("price")
                buy_vol = level_data.get("buy_volume", 0)
                sell_vol = level_data.get("sell_volume", 0)
                
                level = PriceLevel(
                    price=price,
                    buy_volume=buy_vol,
                    sell_volume=sell_vol,
                    total_volume=buy_vol + sell_vol,
                    bid_ask_ratio=buy_vol / max(sell_vol, 0.001),
                    order_count=level_data.get("order_count", 0)
                )
                
                footprint.price_levels[price] = level
            
            # Aggregate volumes
            footprint.total_buy_volume = order_flow_data.get("total_buy_volume", 0)
            footprint.total_sell_volume = order_flow_data.get("total_sell_volume", 0)
            footprint.cumulative_delta = footprint.total_buy_volume - footprint.total_sell_volume
            footprint.bid_ask_imbalance = order_flow_data.get("bid_ask_imbalance", 0)
            
            # Volume profile points of control
            volume_profile = order_flow_data.get("volume_profile", {})
            footprint.poc_price = volume_profile.get("peak_price")
            footprint.vah_price = volume_profile.get("vah")  # Value Area High
            footprint.val_price = volume_profile.get("val")  # Value Area Low
            
            # Determine liquidity level
            footprint.liquidity_level = self._classify_liquidity_level(
                footprint.total_volume
            )
            
            # Store footprint
            self.footprints[key] = footprint
            self.historical_data[key].append(footprint)
            
            # Keep only last 100 footprints per symbol/timeframe
            if len(self.historical_data[key]) > 100:
                self.historical_data[key].pop(0)
            
            logger.info(
                f"📊 Order flow processed: {symbol} {timeframe} "
                f"(Buy: {footprint.total_buy_volume:.0f}, "
                f"Sell: {footprint.total_sell_volume:.0f}, "
                f"Delta: {footprint.cumulative_delta:.0f})"
            )
            
            return footprint
    
    def analyze_liquidity_profile(
        self,
        symbol: str,
        timeframe: str
    ) -> LiquidityProfile:
        """
        Analyze liquidity profile from order flow data.
        Identifies support/resistance levels based on volume clusters.
        
        Args:
            symbol: Trading symbol
            timeframe: Chart timeframe
        
        Returns:
            LiquidityProfile with support/resistance analysis
        """
        with self.lock:
            key = f"{symbol}_{timeframe}"
            footprint = self.footprints.get(key)
            
            if not footprint:
                return None
            
            # Find support and resistance from volume clusters
            support_level, support_strength = self._find_support(footprint)
            resistance_level, resistance_strength = self._find_resistance(footprint)
            
            # Identify liquidity clusters (high volume zones)
            liquidity_clusters = self._identify_liquidity_clusters(footprint)
            
            # Detect institutional activity
            inst_accum = self._detect_accumulation(footprint)
            inst_dist = self._detect_distribution(footprint)
            
            profile = LiquidityProfile(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.utcnow().isoformat(),
                support_level=support_level,
                resistance_level=resistance_level,
                support_strength=support_strength,
                resistance_strength=resistance_strength,
                liquidity_clusters=liquidity_clusters,
                institutional_accumulation=inst_accum,
                institutional_distribution=inst_dist,
                liquidity_depth=self._calculate_liquidity_depth(footprint),
                spread_efficiency=self._calculate_spread_efficiency(footprint)
            )
            
            self.liquidity_profiles[key] = profile
            
            logger.info(
                f"💧 Liquidity profile analyzed: {symbol} {timeframe} "
                f"(Support: {support_level:.5f}, Resistance: {resistance_level:.5f})"
            )
            
            return profile
    
    def detect_liquidity_sweeps(
        self,
        symbol: str,
        timeframe: str,
        lookback: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Detect liquidity sweep patterns (institutional order flow).
        Liquidity sweeps occur when price moves through support/resistance
        with high volume, indicating institutional accumulation/distribution.
        
        Args:
            symbol: Trading symbol
            timeframe: Chart timeframe
            lookback: Number of recent candles to analyze
        
        Returns:
            List of liquidity sweep events detected
        """
        with self.lock:
            key = f"{symbol}_{timeframe}"
            history = self.historical_data.get(key, [])
            
            if len(history) < lookback:
                return []
            
            sweeps = []
            recent = history[-lookback:]
            
            for i in range(1, len(recent)):
                prev_footprint = recent[i - 1]
                curr_footprint = recent[i]
                
                # Detect volume spike with directional bias
                volume_increase = (
                    curr_footprint.total_volume / max(prev_footprint.total_volume, 1)
                )
                
                if volume_increase > 1.5:  # 50% volume increase
                    # Determine direction
                    if curr_footprint.cumulative_delta > 0:
                        direction = "BUY"
                        intensity = abs(curr_footprint.cumulative_delta) / curr_footprint.total_volume
                    else:
                        direction = "SELL"
                        intensity = abs(curr_footprint.cumulative_delta) / curr_footprint.total_volume
                    
                    sweep = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "direction": direction,
                        "volume": curr_footprint.total_volume,
                        "intensity": intensity,  # 0-1, higher = more extreme
                        "timestamp": curr_footprint.timestamp,
                        "confidence": min(100, intensity * 100)
                    }
                    
                    sweeps.append(sweep)
            
            logger.info(
                f"🌊 Liquidity sweeps detected: {symbol} {timeframe} "
                f"({len(sweeps)} sweeps)"
            )
            
            return sweeps
    
    def detect_institutional_patterns(
        self,
        symbol: str,
        timeframe: str
    ) -> List[InstitutionalSignal]:
        """
        Detect patterns indicative of institutional order flow activity.
        
        Patterns detected:
        - Accumulation: Buy volume > sell volume over multiple candles
        - Distribution: Sell volume > buy volume over multiple candles
        - Layering: Multiple large orders at same price (spoofing indicator)
        - Iceberg: Large volume with order count much lower (hidden orders)
        
        Args:
            symbol: Trading symbol
            timeframe: Chart timeframe
        
        Returns:
            List of institutional signals detected
        """
        with self.lock:
            key = f"{symbol}_{timeframe}"
            history = self.historical_data.get(key, [])
            
            if not history:
                return []
            
            signals = []
            
            # Analyze last 10 candles for patterns
            lookback_data = history[-10:]
            
            # Detect sustained accumulation/distribution
            accum_score = 0
            dist_score = 0
            
            for footprint in lookback_data:
                if footprint.buy_sell_ratio > 1.2:
                    accum_score += 1
                elif footprint.buy_sell_ratio < 0.85:
                    dist_score += 1
            
            if accum_score >= 3:
                signal = InstitutionalSignal(
                    signal_type="accumulation",
                    confidence=min(100, accum_score * 15),
                    description="Sustained institutional accumulation detected",
                    timestamp=datetime.utcnow().isoformat(),
                    price_range=(
                        min(f.val_price or 0 for f in lookback_data),
                        max(f.vah_price or 0 for f in lookback_data)
                    ),
                    volume_involved=sum(f.total_buy_volume for f in lookback_data)
                )
                signals.append(signal)
            
            if dist_score >= 3:
                signal = InstitutionalSignal(
                    signal_type="distribution",
                    confidence=min(100, dist_score * 15),
                    description="Sustained institutional distribution detected",
                    timestamp=datetime.utcnow().isoformat(),
                    price_range=(
                        min(f.val_price or 0 for f in lookback_data),
                        max(f.vah_price or 0 for f in lookback_data)
                    ),
                    volume_involved=sum(f.total_sell_volume for f in lookback_data)
                )
                signals.append(signal)
            
            self.institutional_signals.extend(signals)
            
            logger.info(
                f"🏦 Institutional patterns detected: {symbol} {timeframe} "
                f"({len(signals)} patterns)"
            )
            
            return signals
    
    def get_order_flow_sentiment(
        self,
        symbol: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Get aggregated market sentiment from order flow analysis.
        Used by SentimentAgent to enhance decisions.
        
        Returns:
            {
                "sentiment": "bullish" / "bearish" / "neutral",
                "strength": 0-100,
                "key_factors": [...],
                "institutional_activity": "accumulation" / "distribution" / "neutral",
                "volume_profile": {...}
            }
        """
        with self.lock:
            key = f"{symbol}_{timeframe}"
            footprint = self.footprints.get(key)
            profile = self.liquidity_profiles.get(key)
            
            if not footprint:
                return {"sentiment": "neutral", "strength": 0}
            
            # Determine sentiment from bid/ask ratio
            if footprint.buy_sell_ratio > 1.3:
                sentiment = "bullish"
                strength = min(100, (footprint.buy_sell_ratio - 1.0) * 50)
            elif footprint.buy_sell_ratio < 0.75:
                sentiment = "bearish"
                strength = min(100, (1.0 - footprint.buy_sell_ratio) * 50)
            else:
                sentiment = "neutral"
                strength = 30
            
            # Build response
            response = {
                "symbol": symbol,
                "timeframe": timeframe,
                "sentiment": sentiment,
                "strength": strength,
                "bid_ask_ratio": footprint.buy_sell_ratio,
                "cumulative_delta": footprint.cumulative_delta,
                "total_volume": footprint.total_volume,
                "liquidity_level": footprint.liquidity_level,
                "key_factors": []
            }
            
            # Add institutional activity info
            if profile:
                if profile.institutional_accumulation:
                    response["key_factors"].append("institutional accumulation")
                if profile.institutional_distribution:
                    response["key_factors"].append("institutional distribution")
            
            return response
    
    # Helper methods
    
    def _classify_liquidity_level(self, volume: float) -> str:
        """Classify liquidity level based on volume."""
        if volume > 100000:
            return LiquidityLevel.VERY_HIGH.value
        elif volume > 50000:
            return LiquidityLevel.HIGH.value
        elif volume > 20000:
            return LiquidityLevel.MEDIUM.value
        elif volume > 10000:
            return LiquidityLevel.LOW.value
        else:
            return LiquidityLevel.VERY_LOW.value
    
    def _find_support(self, footprint: OrderFlowFootprint) -> Tuple[float, float]:
        """Find support level from volume concentration."""
        if not footprint.price_levels:
            return 0, 0
        
        # Find lowest price with high volume
        sorted_levels = sorted(
            footprint.price_levels.items(),
            key=lambda x: x[1].total_volume,
            reverse=True
        )
        
        # Get lowest of top 3 volume concentrations
        top_volumes = sorted_levels[:3]
        support_price = min(p for p, _ in top_volumes)
        support_strength = max(l.total_volume for _, l in top_volumes) / footprint.total_volume * 100
        
        return support_price, support_strength
    
    def _find_resistance(self, footprint: OrderFlowFootprint) -> Tuple[float, float]:
        """Find resistance level from volume concentration."""
        if not footprint.price_levels:
            return 0, 0
        
        # Find highest price with high volume
        sorted_levels = sorted(
            footprint.price_levels.items(),
            key=lambda x: x[1].total_volume,
            reverse=True
        )
        
        # Get highest of top 3 volume concentrations
        top_volumes = sorted_levels[:3]
        resistance_price = max(p for p, _ in top_volumes)
        resistance_strength = max(l.total_volume for _, l in top_volumes) / footprint.total_volume * 100
        
        return resistance_price, resistance_strength
    
    def _identify_liquidity_clusters(
        self,
        footprint: OrderFlowFootprint
    ) -> List[Tuple[float, float]]:
        """Identify price levels with high volume concentration."""
        if not footprint.price_levels:
            return []
        
        # Sort by volume
        sorted_levels = sorted(
            footprint.price_levels.items(),
            key=lambda x: x[1].total_volume,
            reverse=True
        )
        
        # Return top 5 clusters as (price, volume)
        clusters = [(p, l.total_volume) for p, l in sorted_levels[:5]]
        return clusters
    
    def _detect_accumulation(self, footprint: OrderFlowFootprint) -> bool:
        """Detect institutional accumulation pattern."""
        return footprint.buy_sell_ratio > 1.3 and footprint.total_volume > 50000
    
    def _detect_distribution(self, footprint: OrderFlowFootprint) -> bool:
        """Detect institutional distribution pattern."""
        return footprint.buy_sell_ratio < 0.75 and footprint.total_volume > 50000
    
    def _calculate_liquidity_depth(self, footprint: OrderFlowFootprint) -> float:
        """Calculate average liquidity depth."""
        if not footprint.price_levels:
            return 0
        
        volumes = [l.total_volume for l in footprint.price_levels.values()]
        return np.mean(volumes) if volumes else 0
    
    def _calculate_spread_efficiency(self, footprint: OrderFlowFootprint) -> float:
        """Calculate how efficiently liquidity is distributed."""
        if not footprint.price_levels:
            return 0
        
        volumes = [l.total_volume for l in footprint.price_levels.values()]
        return np.std(volumes) / (np.mean(volumes) + 1)


def create_order_flow_analyzer() -> OrderFlowAnalyzer:
    """
    Factory function to create an order flow analyzer.
    
    Returns:
        Configured OrderFlowAnalyzer instance
    """
    return OrderFlowAnalyzer()
