#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lstm_model.py - এলএসটিএম প্রাইস প্রেডিকশন এজেন্ট মডিউল
"""
import logging
from typing import Callable, Optional
from agent_interface import BaseAgent
from common import AgentVote, VoteDirection, CandleWindowConfig

log = logging.getLogger(__name__)

class PredictiveAgent(BaseAgent):
    def __init__(self, candle_provider: Optional[Callable] = None):
        super().__init__(name="PredictiveAgent", candle_provider=candle_provider)
        self.lookback = CandleWindowConfig.PREDICTIVE_LOOKBACK
    
    def vote(self, symbol: str) -> AgentVote:
        try:
            candles = self._get_candles(symbol, self.lookback)
            if not self._validate_candles(candles, min_size=5):
                return AgentVote(self.name, VoteDirection.NEUTRAL, 0.0, "পর্যাপ্ত ক্যান্ডেল ডেটা নেই")
            
            current_close = candles[-1]["close"]
            predicted_close = self._predict_next_close(candles)
            confidence = self._calculate_confidence(candles, predicted_close, current_close)
            
            # যদি প্রেডিক্টেড প্রাইস কারেন্ট প্রাইস থেকে ০.১% বেশি হয়
            if predicted_close > current_close * 1.001:
                return AgentVote(self.name, VoteDirection.BULLISH, confidence, f"LSTM টার্গেট আপসাইড: {predicted_close:.2f}")
            # যদি প্রেডিক্টেড প্রাইস কারেন্ট প্রাইস থেকে ০.১% কম হয়
            elif predicted_close < current_close * 0.999:
                return AgentVote(self.name, VoteDirection.BEARISH, confidence, f"LSTM টার্গেট ডাউনসাইড: {predicted_close:.2f}")
            else:
                return AgentVote(self.name, VoteDirection.NEUTRAL, 55.0, "মার্কেট কনসোলিডেশন বা সাইডওয়েজ হওয়ার সম্ভাবনা")
        except Exception as e:
            log.error(f"{self.name} এ এক্সেপশন ঘটেছে: {e}")
            return AgentVote(agent_name=self.name, vote=VoteDirection.NEUTRAL, confidence=0.0, reason="Error", error=str(e))
    
    def _predict_next_close(self, candles: list) -> float:
        if not candles:
            return 0.0
        closes = [c["close"] for c in candles[-5:]]
        base_close = closes[0]
        if base_close == 0:
            return candles[-1]["close"]
        momentum = (closes[-1] - base_close) / base_close
        return candles[-1]["close"] * (1 + momentum * 0.5)
    
    def _calculate_confidence(self, candles: list, predicted: float, current: float) -> float:
        if current == 0:
            return 50.0
        change_percent = abs(predicted - current) / current * 100
        base_confidence = 50.0 + min(change_percent * 2, 30.0)
        return min(base_confidence, 90.0)
