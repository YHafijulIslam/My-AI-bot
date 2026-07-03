#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
order_flow.py - টেকনিক্যাল ট্রেন্ড এনালাইসিস এজেন্ট মডিউল
"""
import logging
from typing import Callable, Optional
from agent_interface import BaseAgent
from common import AgentVote, VoteDirection, CandleWindowConfig

log = logging.getLogger(__name__)

class TechnicalAgent(BaseAgent):
    def __init__(self, candle_provider: Optional[Callable] = None):
        super().__init__(name="TechnicalAgent", candle_provider=candle_provider)
        self.lookback = CandleWindowConfig.TECHNICAL_LOOKBACK
    
    def vote(self, symbol: str) -> AgentVote:
        try:
            candles = self._get_candles(symbol, self.lookback)
            if not self._validate_candles(candles, min_size=2):
                return AgentVote(self.name, VoteDirection.NEUTRAL, 0.0, "পর্যাপ্ত ক্যান্ডেল ডেটা নেই")
            
            current_close = candles[-1]["close"]
            previous_close = candles[-2]["close"]
            
            if current_close > previous_close:
                confidence = self._calculate_confidence(candles, VoteDirection.BULLISH)
                return AgentVote(self.name, VoteDirection.BULLISH, confidence, "আপট্রেন্ড মার্কেট স্ট্রাকচার")
            elif current_close < previous_close:
                confidence = self._calculate_confidence(candles, VoteDirection.BEARISH)
                return AgentVote(self.name, VoteDirection.BEARISH, confidence, "ডাউনট্রেন্ড মার্কেট স্ট্রাকচার")
            else:
                return AgentVote(self.name, VoteDirection.NEUTRAL, 50.0, "কোনো স্পষ্ট ট্রেন্ড নেই (সাইডওয়েজ)")
        except Exception as e:
            log.error(f"{self.name} এ এক্সেপশন ঘটেছে: {e}")
            return AgentVote(agent_name=self.name, vote=VoteDirection.NEUTRAL, confidence=0.0, reason="Error", error=str(e))
    
    def _calculate_confidence(self, candles: list, direction: VoteDirection) -> float:
        if len(candles) < 5:
            return 60.0
        recent_closes = [c["close"] for c in candles[-5:]]
        if direction == VoteDirection.BULLISH:
            matching_moves = sum(1 for i in range(1, len(recent_closes)) if recent_closes[i] > recent_closes[i-1])
        else:
            matching_moves = sum(1 for i in range(1, len(recent_closes)) if recent_closes[i] < recent_closes[i-1])
        confidence = 50.0 + (matching_moves * 11.25)
        return min(confidence, 95.0)
