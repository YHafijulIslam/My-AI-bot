#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
liquidity_sweep.py - এসএমসি লিকুইডিটি সুইপ এনালাইসিস এজেন্ট মডিউল
"""
import logging
from typing import Callable, Optional
from agent_interface import BaseAgent
from common import AgentVote, VoteDirection, CandleWindowConfig

log = logging.getLogger(__name__)

class LiquiditySweepVoter(BaseAgent):
    def __init__(self, candle_provider: Optional[Callable] = None):
        super().__init__(name="LiquiditySweepVoter", candle_provider=candle_provider)
        self.lookback = CandleWindowConfig.LIQUIDITY_LOOKBACK
        self.sweep_window = CandleWindowConfig.LIQUIDITY_SWEEP_WINDOW
    
    def vote(self, symbol: str) -> AgentVote:
        try:
            candles = self._get_candles(symbol, self.lookback)
            if not self._validate_candles(candles, min_size=3):
                return AgentVote(self.name, VoteDirection.NEUTRAL, 0.0, "পর্যাপ্ত ক্যান্ডেল ডেটা নেই")
            
            sweep_result = self._detect_sweep(candles)
            if sweep_result["direction"] == VoteDirection.BULLISH:
                return AgentVote(self.name, VoteDirection.BULLISH, sweep_result["confidence"], sweep_result["reason"])
            elif sweep_result["direction"] == VoteDirection.BEARISH:
                return AgentVote(self.name, VoteDirection.BEARISH, sweep_result["confidence"], sweep_result["reason"])
            else:
                return AgentVote(self.name, VoteDirection.NEUTRAL, 50.0, "কোনো লিকুইডিটি সুইপ সনাক্ত হয়নি")
        except Exception as e:
            log.error(f"{self.name} এ এক্সেপশন ঘটেছে: {e}")
            return AgentVote(agent_name=self.name, vote=VoteDirection.NEUTRAL, confidence=0.0, reason="Error", error=str(e))
    
    def _detect_sweep(self, candles: list) -> dict:
        if len(candles) < 3:
            return {"direction": VoteDirection.NEUTRAL, "confidence": 0.0, "reason": "Insufficient candles"}
        last_candle = candles[-1]
        target_idx = min(self.sweep_window + 1, len(candles))
        prev_window = candles[-target_idx:-1]
        
        if not prev_window:
            return {"direction": VoteDirection.NEUTRAL, "confidence": 50.0, "reason": "No window"}
            
        prev_high = max(c["high"] for c in prev_window)
        prev_low = min(c["low"] for c in prev_window)
        range_total = max(last_candle["high"] - last_candle["low"], 0.0001)
        
        # বুলিশ সুইপ: প্রাইস আগের লো সুইপ করে উপরে ক্লোজ হয়েছে
        if last_candle["low"] < prev_low and last_candle["close"] > prev_low:
            recovery_strength = (last_candle["close"] - last_candle["low"]) / range_total
            confidence = min(75.0 + (recovery_strength * 15.0), 95.0)
            return {"direction": VoteDirection.BULLISH, "confidence": confidence, "reason": f"SMC বুলিশ লিকুইডিটি সুইপ @ {prev_low:.2f}"}
        # বেয়ারিশ সুইপ: প্রাইস আগের হাই সুইপ করে নিচে ক্লোজ হয়েছে
        elif last_candle["high"] > prev_high and last_candle["close"] < prev_high:
            rejection_strength = (last_candle["high"] - last_candle["close"]) / range_total
            confidence = min(75.0 + (rejection_strength * 15.0), 95.0)
            return {"direction": VoteDirection.BEARISH, "confidence": confidence, "reason": f"SMC বেয়ারিশ লিকুইডিটি সুইপ @ {prev_high:.2f}"}
        return {"direction": VoteDirection.NEUTRAL, "confidence": 50.0, "reason": "No sweep pattern"}
