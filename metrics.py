#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metrics.py - থ্রেড-সেফ পারফরম্যান্স মেট্রিকেস এবং ট্র্যাকিং মডিউল
"""
import threading
from datetime import datetime
from collections import defaultdict
from typing import Dict, List
from dataclasses import dataclass, field
from common import AgentVote, VoteDirection

@dataclass
class AgentMetrics:
    agent_name: str
    total_votes: int = 0
    bullish_votes: int = 0
    bearish_votes: int = 0
    neutral_votes: int = 0
    avg_confidence: float = 0.0
    confidence_scores: List[float] = field(default_factory=list)
    
    def update_confidence(self, confidence: float):
        self.confidence_scores.append(confidence)
        self.avg_confidence = sum(self.confidence_scores) / len(self.confidence_scores)
    
    def to_dict(self) -> Dict:
        return {
            "agent_name": self.agent_name,
            "total_votes": self.total_votes,
            "bullish_votes": self.bullish_votes,
            "bearish_votes": self.bearish_votes,
            "neutral_votes": self.neutral_votes,
            "avg_confidence": round(self.avg_confidence, 2)
        }

class VotingMetrics:
    def __init__(self):
        self._lock = threading.RLock()
        self.agent_metrics: Dict[str, AgentMetrics] = defaultdict(lambda: AgentMetrics(agent_name="Pending"))
        self.decision_history: List[Dict] = []
        self.consensus_success_count = 0
        self.total_decisions = 0
        self.start_time = datetime.now()
    
    def record_votes(self, symbol: str, votes: List[AgentVote]):
        with self._lock:
            for vote in votes:
                name = vote.agent_name
                if name not in self.agent_metrics or self.agent_metrics[name].agent_name == "Pending":
                    self.agent_metrics[name] = AgentMetrics(agent_name=name)
                m = self.agent_metrics[name]
                m.total_votes += 1
                m.update_confidence(vote.confidence)
                v = int(vote.vote)
                if v == VoteDirection.BULLISH:
                    m.bullish_votes += 1
                elif v == VoteDirection.BEARISH:
                    m.bearish_votes += 1
                else:
                    m.neutral_votes += 1

    def record_decision(self, symbol: str, decision: str):
        with self._lock:
            self.total_decisions += 1
            if decision in ("BUY", "SELL"):
                self.consensus_success_count += 1
            self.decision_history.append({"timestamp": datetime.now().isoformat(), "symbol": symbol, "decision": decision})
            
    def get_summary(self) -> Dict:
        with self._lock:
            uptime = (datetime.now() - self.start_time).total_seconds()
            rate = (self.consensus_success_count / self.total_decisions * 100) if self.total_decisions > 0 else 0.0
            return {
                "uptime_seconds": round(uptime, 1),
                "total_decisions": self.total_decisions,
                "consensus_success_rate": round(rate, 2),
                "agent_metrics": {n: m.to_dict() for n, m in self.agent_metrics.items()}
            }
