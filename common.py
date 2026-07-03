#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
common.py - শেয়ার্ড ডাটা ক্লাস এবং কনফিগারেশন মডিউল
"""
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional
import os

class VoteDirection(IntEnum):
    BEARISH = -1
    NEUTRAL = 0
    BULLISH = 1

@dataclass
class AgentVote:
    agent_name: str
    vote: int
    confidence: float
    reason: str
    error: Optional[str] = None

    def __post_init__(self):
        valid_votes = (int(VoteDirection.BEARISH), int(VoteDirection.NEUTRAL), int(VoteDirection.BULLISH))
        if int(self.vote) not in valid_votes:
            raise ValueError(f"ভুল ভোট মান: {self.vote}")
        if not 0.0 <= self.confidence <= 100.0:
            raise ValueError(f"ভুল কনফিডেন্স মান: {self.confidence}")

    def __repr__(self):
        vote_str = {-1: "BEARISH", 0: "NEUTRAL", 1: "BULLISH"}[int(self.vote)]
        return f"AgentVote(agent={self.agent_name}, vote={vote_str}, confidence={self.confidence:.1f}%)"

class CandleWindowConfig:
    TECHNICAL_LOOKBACK = int(os.getenv('CANDLE_TECHNICAL_LOOKBACK', '50'))
    PREDICTIVE_LOOKBACK = int(os.getenv('CANDLE_PREDICTIVE_LOOKBACK', '60'))
    LIQUIDITY_LOOKBACK = int(os.getenv('CANDLE_LIQUIDITY_LOOKBACK', '30'))
    LIQUIDITY_SWEEP_WINDOW = int(os.getenv('CANDLE_SWEEP_WINDOW', '15'))
    SENTIMENT_LOOKBACK = int(os.getenv('CANDLE_SENTIMENT_LOOKBACK', '20'))
    
    @classmethod
    def validate(cls):
        for attr in ['TECHNICAL_LOOKBACK', 'PREDICTIVE_LOOKBACK', 'LIQUIDITY_LOOKBACK', 'LIQUIDITY_SWEEP_WINDOW', 'SENTIMENT_LOOKBACK']:
            value = getattr(cls, attr)
            if value <= 0:
                raise ValueError(f"{attr} অবশ্যই ০ থেকে বড় হতে হবে, পেয়েছেন {value}")

# কনফিগারেশন ভ্যালিডেশন রান
CandleWindowConfig.validate()
