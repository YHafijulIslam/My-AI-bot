#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_interface.py - সব এজেন্টের জন্য বেস বা মূল ইন্টারফেস মডিউল
"""
from abc import ABC, abstractmethod
from typing import Callable, Optional
import logging
from common import AgentVote, VoteDirection

log = logging.getLogger(__name__)

class BaseAgent(ABC):
    def __init__(self, name: str, candle_provider: Optional[Callable] = None):
        self.name = name
        self._candle_provider = candle_provider
        log.debug(f"{self.name} ইনিশিয়ালাইজড হয়েছে")

    @abstractmethod
    def vote(self, symbol: str) -> AgentVote:
        """সব এজেন্টকে অবশ্যই এই মেথডটি ব্যবহার করে ভোট দিতে হবে"""
        raise NotImplementedError("Agents must implement vote(symbol) -> AgentVote")

    def _get_candles(self, symbol: str, lookback: int) -> list:
        if self._candle_provider is None:
            log.warning(f"{self.name}: কোনো ক্যান্ডেল প্রোভাইডার সেট করা নেই")
            return []
        try:
            candles = self._candle_provider(symbol, lookback=lookback)
            if not isinstance(candles, list):
                log.error(f"{self.name}: ক্যান্ডেল প্রোভাইডার লিস্ট রিটার্ন করেনি")
                return []
            return candles
        except Exception as e:
            log.error(f"{self.name}: ক্যান্ডেল আনতে সমস্যা হয়েছে: {e}")
            return []

    def _validate_candles(self, candles: list, min_size: int = 2) -> bool:
        if not candles or len(candles) < min_size:
            return False
        required_keys = {"high", "low", "close", "open"}
        return all(required_keys.issubset(c.keys()) for c in candles)
