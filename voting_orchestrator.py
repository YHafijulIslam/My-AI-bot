#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
voting_orchestrator.py - ভোটিং সিস্টেম এবং ট্রেড এক্সিকিউশন অর্কেস্ট্রেটর মডিউল
"""
import logging
import time
import json
from typing import List, Optional, Dict
import MetaTrader5 as mt5

from agent_interface import BaseAgent
from ai_judge import SentimentAgent
from lstm_model import PredictiveAgent
from transformer_agent import TransformerAgent
from order_flow import TechnicalAgent
from liquidity_sweep import LiquiditySweepVoter
from common import AgentVote, VoteDirection
from metrics import VotingMetrics
from risk_manager import RiskManager
from trade_executor import TradeExecutor

logger = logging.getLogger(__name__)

class VotingOrchestrator:
    def __init__(self, config_path: str = "exness_config.json"):
        """ভোটিং অর্কেস্ট্রেটর ইনিশিয়ালাইজ করুন"""
        logger.info("🚀 ভোটিং অর্কেস্ট্রেটর শুরু হচ্ছে...")
        
        # MT5 সংযোগ স্থাপন করুন
        self._mt5_connected = False
        self._initialize_mt5(config_path)
        
        # এজেন্টস ইনিশিয়ালাইজ করুন
        self.agents: List[BaseAgent] = self._init_agents()
        
        # ম্যানেজমেন্ট সিস্টেম
        self.metrics = VotingMetrics()
        self.risk_manager = RiskManager(account_balance=10000.0, risk_percentage=1.0)
        self.trade_executor = TradeExecutor()
        
        logger.info(f"✅ অর্কেস্ট্রেটর প্রস্তুত - {len(self.agents)}টি এজেন্ট লোড হয়েছে")
    
    def _initialize_mt5(self, config_path: str) -> bool:
        """MT5 সংযোগ এবং কনফিগারেশন"""
        try:
            # MT5 ইনিশিয়ালাইজ করুন
            if not mt5.initialize():
                logger.error(f"MT5 ইনিশিয়ালাইজেশন ব্যর্থ: {mt5.last_error()}")
                return False
            
            # কনফিগ লোড করুন (সংবেদনশীল তথ্য)
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                logger.info("✅ Exness কনফিগারেশন লোড হয়েছে")
            except FileNotFoundError:
                logger.warning(f"⚠️ কনফিগ ফাইল পাওয়া যায়নি: {config_path}")
                logger.info("ডেমো মোডে চলছে...")
            
            self._mt5_connected = True
            logger.info("✅ MT5 সংযোগ সফল")
            return True
            
        except Exception as e:
            logger.error(f"❌ MT5 সেটআপ ত্রুটি: {e}")
            self._mt5_connected = False
            return False
    
    def _init_agents(self) -> List[BaseAgent]:
        """সমস্ত এজেন্ট ইনিশিয়ালাইজ করুন"""
        agents = [
            SentimentAgent(news_provider=None),
            PredictiveAgent(candle_provider=self.fetch_live_market_data),
            TransformerAgent(candle_provider=self.fetch_live_market_data),
            TechnicalAgent(candle_provider=self.fetch_live_market_data),
            LiquiditySweepVoter(candle_provider=self.fetch_live_market_data),
        ]
        logger.info(f"✅ {len(agents)}টি এজেন্ট ইনিশিয়ালাইজড")
        return agents
    
    def fetch_live_market_data(self, symbol: str, lookback: int = 50) -> list:
        """MT5 থেকে লাইভ মার্কেট ডেটা আনুন"""
        if not self._mt5_connected:
            logger.warning(f"⚠️ MT5 সংযুক্ত নয় - {symbol} এর জন্য ডেটা পাওয়া যাচ্ছে না")
            return []
        
        try:
            symbol = symbol.upper().strip()
            # সর্বশেষ N ক্যান্ডেল আনুন
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, lookback)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"⚠️ {symbol} এর জন্য কোনো ডেটা পাওয়া যায়নি")
                return []
            
            # ডিকশনারি ফরম্যাটে রূপান্তর
            candles = []
            for rate in rates:
                candles.append({
                    'time': rate['time'],
                    'open': float(rate['open']),
                    'high': float(rate['high']),
                    'low': float(rate['low']),
                    'close': float(rate['close']),
                    'volume': int(rate['tick_volume'])
                })
            
            logger.debug(f"✅ {symbol}: {len(candles)} ক্যান্ডেল আনা হয়েছে")
            return candles
            
        except Exception as e:
            logger.error(f"❌ {symbol} থেকে মার্কেট ডেটা আনতে ত্রুটি: {e}")
            return []
    
    def run_voting_cycle(self, symbol: str):
        """একটি সম্পূর্ণ ভোটিং চক্র চালান"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 {symbol} এর জন্য ভোটিং চক্র শুরু")
        logger.info(f"{'='*60}")
        
        # সমস্ত এজেন্টদের কাছ থেকে ভোট সংগ্রহ করুন
        votes: List[AgentVote] = []
        for agent in self.agents:
            try:
                vote = agent.vote(symbol)
                votes.append(vote)
                logger.info(f"✅ {vote.agent_name}: {vote}")
            except Exception as e:
                logger.error(f"❌ {agent.name} থেকে ভোট নিতে ত্রুটি: {e}")
        
        # মেট্রিক্স রেকর্ড করুন
        self.metrics.record_votes(symbol, votes)
        
        # ভোট গণনা করুন
        action_counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
        for v in votes:
            if v == int(VoteDirection.BULLISH):
                action_counts["BUY"] += 1
            elif v == int(VoteDirection.BEARISH):
                action_counts["SELL"] += 1
            else:
                action_counts["HOLD"] += 1
        
        # চূড়ান্ত সিদ্ধান্ত
        final_decision = "HOLD"
        if action_counts["BUY"] >= 3:
            final_decision = "BUY"
        elif action_counts["SELL"] >= 3:
            final_decision = "SELL"
        
        self.metrics.record_decision(symbol, final_decision)
        logger.info(f"📊 {symbol} এর জন্য চূড়ান্ত সিদ্ধান্ত: {final_decision}")
        logger.info(f"   BUY: {action_counts['BUY']}, SELL: {action_counts['SELL']}, HOLD: {action_counts['HOLD']}")
        
        # ট্রেড এক্সিকিউট করুন যদি সিদ্ধান্ত হয়
        if final_decision in ["BUY", "SELL"]:
            self._execute_trade(symbol, final_decision)
    
    def _execute_trade(self, symbol: str, decision: str):
        """ট্রেড এক্সিকিউশন লজিক"""
        try:
            candles = self.fetch_live_market_data(symbol, lookback=2)
            if not candles:
                logger.error(f"❌ {symbol} এর জন্য কোনো ক্যান্ডেল ডেটা পাওয়া যায়নি")
                return
            
            last_candle = candles[-1]
            
            # প্রাইস নিরাপদে আনুন (ডিকশনারি বা অবজেক্ট উভয় থেকে)
            current_price = float(last_candle['close'] if isinstance(last_candle, dict) else getattr(last_candle, 'close', 0.0))
            
            if current_price == 0:
                logger.error(f"❌ {symbol} এর জন্য কোনো প্রাইস পাওয়া যায়নি")
                return
            
            # বিটকয়েন এবং গোল্ডের জন্য আলাদা স্টপ লস
            if "BTC" in symbol:
                sl_dist = 150.0  # বিটকয়েনের জন্য ১৫০ ডলার
            else:
                sl_dist = 2.0    # গোল্ডের জন্য ২ ডলার
            
            sl_price = current_price - sl_dist if decision == "BUY" else current_price + sl_dist
            
            # রিস্ক ক্যালকুলেশন
            risk_result = self.risk_manager.calculate_position(current_price, sl_price, symbol)
            
            if risk_result and risk_result.get("status") == "Success":
                logger.info(f"🚀 {symbol} এর জন্য এক্সিকিউশন লজিক ট্রিগার হয়েছে")
                logger.info(f"   সিদ্ধান্ত: {decision}")
                logger.info(f"   লট সাইজ: {risk_result['lot_size']}")
                logger.info(f"   স্টপ লস: {sl_price}")
                
                # লাইভ ট্রেড এক্সিকিউট করুন
                if self._mt5_connected:
                    self.trade_executor.execute_trade(decision, risk_result['lot_size'], sl_price, symbol)
                else:
                    logger.warning(f"⚠️ MT5 সংযুক্ত নয় - ডেমো মোডে সিমুলেট করছি")
            else:
                logger.error(f"❌ {symbol} এর জন্য রিস্ক ক্যালকুলেশন ব্যর্থ: {risk_result}")
                
        except Exception as e:
            logger.error(f"❌ ট্রেড এক্সিকিউশনে ত্রুটি: {e}")
    
    def shutdown(self):
        """অর্কেস্ট্রেটর শাটডাউন করুন"""
        logger.info("\n🛑 শাটডাউন শুরু হচ্ছে...")
        
        # মেট্রিক্স সামারি লগ করুন
        summary = self.metrics.get_summary()
        logger.info(f"📈 মেট্রিক্স সামারি:")
        logger.info(f"   মোট সিদ্ধান্ত: {summary['total_decisions']}")
        logger.info(f"   কনসেনসাস সাফল্যের হার: {summary['consensus_success_rate']}%")
        logger.info(f"   আপটাইম: {summary['uptime_seconds']} সেকেন্ড")
        
        # MT5 সংযোগ বন্ধ করুন
        if self._mt5_connected:
            try:
                mt5.shutdown()
                logger.info("✅ MT5 সংযোগ বন্ধ হয়েছে")
            except Exception as e:
                logger.error(f"❌ MT5 শাটডাউন ত্রুটি: {e}")
            self._mt5_connected = False
        
        logger.info("✅ শাটডাউন সম্পন্ন")


if __name__ == "__main__":
    orchestrator = None
    
    try:
        orchestrator = VotingOrchestrator()
        
        # গোল্ড এবং বিটকয়েন মাল্টি-অ্যাসেট লিস্ট
        symbols_to_trade = ["XAUUSD", "BTCUSD"]
        
        while True:
            for symbol in symbols_to_trade:
                logger.info(f"🔄 {symbol} এর জন্য অটোমেটেড চক্র শুরু করছি")
                try:
                    orchestrator.run_voting_cycle(symbol)
                except Exception as e:
                    logger.error(f"❌ {symbol} এর জন্য চক্র এক্সিকিউশন ত্রুটি: {e}")
                
                time.sleep(5)  # দুই সিম্বলের মাঝে ৫ সেকেন্ডের সেফটি গ্যাপ
            
            logger.info("⏳ সমস্ত সিম্বল চেক করা হয়েছে। ১৫ মিনিটের জন্য অপেক্ষা করছি...")
            time.sleep(900)  # প্রতি ১৫ মিনিট পর পর চক্রটি পুনরায় চলবে
            
    except KeyboardInterrupt:
        logger.info("🛑 ব্যবহারকারী দ্বারা স্ক্রিপ্ট বন্ধ করা হয়েছে")
    except Exception as e:
        logger.error(f"❌ মূল লুপে অপ্রত্যাশিত ত্রুটি: {e}")
    finally:
        if orchestrator:
            orchestrator.shutdown()
