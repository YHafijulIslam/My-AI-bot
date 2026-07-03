#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_judge.py - নিউজ সেন্টিমেন্ট এবং ফান্ডামেন্টাল এনালাইসিস এজেন্ট মডিউল
"""
import logging
from typing import Callable, Optional
from agent_interface import BaseAgent
from common import AgentVote, VoteDirection, CandleWindowConfig

log = logging.getLogger(__name__)

class SentimentAgent(BaseAgent):
    def __init__(self, news_provider: Optional[Callable] = None):
        super().__init__(name="SentimentAgent", candle_provider=None)
        self._news_provider = news_provider
        self.lookback = CandleWindowConfig.SENTIMENT_LOOKBACK
    
    def vote(self, symbol: str) -> AgentVote:
        try:
            sentiment_score = self._analyze_sentiment(symbol)
            confidence = self._calculate_confidence(sentiment_score)
            
            if sentiment_score > 0.2:
                return AgentVote(self.name, VoteDirection.BULLISH, confidence, f"পজিটিভ মার্কেট সেন্টিমেন্ট: {sentiment_score:.2f}")
            elif sentiment_score < -0.2:
                return AgentVote(self.name, VoteDirection.BEARISH, confidence, f"নেগেটিভ মার্কেট সেন্টিমেন্ট: {sentiment_score:.2f}")
            else:
                return AgentVote(self.name, VoteDirection.NEUTRAL, 60.0, f"মিশ্র বা নিউট্রাল সেন্টিমেন্ট: {sentiment_score:.2f}")
        except Exception as e:
            log.error(f"{self.name} এ এক্সেপশন ঘটেছে: {e}")
            return AgentVote(agent_name=self.name, vote=VoteDirection.NEUTRAL, confidence=0.0, reason="Error", error=str(e))
    
    def _analyze_sentiment(self, symbol: str) -> float:
        if self._news_provider is None:
            return 0.0
        try:
            news_data = self._news_provider(symbol, lookback=self.lookback)
            if not news_data:
                return 0.0
            if isinstance(news_data, dict) and "sentiment" in news_data:
                return float(news_data["sentiment"])
            news_count = len(news_data) if isinstance(news_data, list) else 1
            return min(0.05 * news_count, 1.0)
        except Exception as e:
            log.error(f"{self.name} সেন্টিমেন্ট এনালাইসিস এরর: {e}")
            return 0.0
    
    def _calculate_confidence(self, sentiment_score: float) -> float:
        strength = abs(sentiment_score)
        confidence = 50.0 + (strength * 40.0)
      
