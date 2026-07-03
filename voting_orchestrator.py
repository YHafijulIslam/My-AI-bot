#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
voting_orchestrator.py - উন্নত ভোটিং অর্কেস্ট্রেটর MT5 ইন্টিগ্রেশন সহ
Enhanced Voting Orchestrator with MT5 Integration, Retry Logic & Error Handling
"""
import logging
import time
import json
from typing import List, Optional, Dict
from datetime import datetime

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
    """উন্নত ভোটিং অর্কেস্ট্রেটর MT5 ইন্টিগ্রেশন সহ"""
    
    def __init__(self, config: Dict = None, config_path: str = "exness_config.json"):
        """
        অর্কেস্ট্রেটর ইনিশিয়ালাইজ করুন
        
        Args:
            config: কনফিগারেশন ডিকশনারি
            config_path: কনফিগ ফাইলের পাথ
        """
        logger.info("🚀 ভোটিং অর্কেস্ট্রেটর ইনিশিয়ালাইজ হচ্ছে...")
        
        self.config = config or {}
        
        # MT5 সংযোগ ফ্ল্যাগ
        self._mt5_connected = False
        self._mt5_retry_count = 0
        
        # MT5 কনফিগ
        mt5_config = self.config.get("mt5", {
            "timeout": 10,
            "max_retries": 3,
            "retry_delay": 5
        })
        
        self.mt5_timeout = mt5_config.get("timeout", 10)
        self.mt5_max_retries = mt5_config.get("max_retries", 3)
        self.mt5_retry_delay = mt5_config.get("retry_delay", 5)
        
        # MT5 সংযোগ স্থাপন করুন (রিট্রাই লজিক সহ)
        self._initialize_mt5_with_retry()
        
        # ট্রেডিং কনফিগ
        trading_config = self.config.get("trading", {})
        self.consensus_threshold = float(trading_config.get("consensus_threshold", 0.6))
        self.max_agent_failure_rate = float(trading_config.get("max_agent_failure_rate", 0.4))
        
        # বৈধতা কনফিগ
        validation_config = self.config.get("validation", {})
        self.max_price = float(validation_config.get("max_price", 1_000_000))
        self.price_jump_threshold = float(validation_config.get("price_jump_threshold", 0.1))
        
        # এজেন্ট ইনিশিয়ালাইজ করুন
        self.agents: List[BaseAgent] = self._init_agents()
        
        # ম্যানেজমেন্ট সিস্টেম
        self.metrics = VotingMetrics()
        
        # রিস্ক ম্যানেজার (১% রিস্ক)
        account_balance = float(trading_config.get("account_balance", 10000.0))
        risk_percentage = float(trading_config.get("risk_percentage", 1.0))
        self.risk_manager = RiskManager(
            account_balance=account_balance,
            risk_percentage=risk_percentage
        )
        
        # ট্রেড এক্সিকিউটর
        self.trade_executor = TradeExecutor()
        
        # মূল্য ট্র্যাকিং (মূল্য জাম্প সনাক্ত করার জন্য)
        self.previous_prices: Dict[str, float] = {}
        
        logger.info(f"✅ অর্কেস্ট্রেটর প্রস্তুত - {len(self.agents)}টি এজেন্ট লোড হয়েছে")
        logger.info(f"   কনসেনসাস থ্রেশহোল্ড: {self.consensus_threshold*100}%")
        logger.info(f"   MT5 সংযোগ: {'✅ সংযুক্ত' if self._mt5_connected else '❌ ডিসকানেক্টেড'}")
    
    # ===== MT5 সংযোগ ম্যানেজমেন্ট =====
    
    def _initialize_mt5_with_retry(self):
        """রিট্রাই লজিক সহ MT5 ইনিশিয়ালাইজ করুন"""
        logger.info("\n🔗 MT5 সংযোগ স্থাপনের চেষ্টা করছি...")
        
        for attempt in range(self.mt5_max_retries):
            try:
                logger.info(f"  প্রচেষ্টা {attempt + 1}/{self.mt5_max_retries}...")
                
                # MT5 ইনিশিয়ালাইজ করুন
                if mt5.initialize(timeout=self.mt5_timeout):
                    self._mt5_connected = True
                    self._mt5_retry_count = 0
                    logger.info(f"✅ MT5 সংযোগ সফল (প্রচেষ্টা {attempt + 1})")
                    return
                
                # ব্যর্থতার ক্ষেত্রে তথ্য লগ করুন
                last_error = mt5.last_error()
                logger.warning(f"  MT5 ইনিশিয়ালাইজেশন ব্যর্থ: {last_error}")
                
                # শেষ প্রচেষ্টা নয় হলে অপেক্ষা করুন
                if attempt < self.mt5_max_retries - 1:
                    logger.info(f"  {self.mt5_retry_delay}s অপেক্ষা করে পুনরায় চেষ্টা করছি...")
                    time.sleep(self.mt5_retry_delay)
                    
            except Exception as e:
                logger.error(f"  MT5 ইনিশিয়ালাইজেশন ত্রুটি (প্রচেষ্টা {attempt + 1}): {e}")
                
                if attempt < self.mt5_max_retries - 1:
                    time.sleep(self.mt5_retry_delay)
        
        # সব প্রচেষ্টা ব্যর্থ
        self._mt5_connected = False
        self._mt5_retry_count = self.mt5_max_retries
        logger.error(f"❌ MT5 সংযোগ ব্যর্থ {self.mt5_max_retries} প্রচেষ্টার পরে")
        logger.warning("⚠️ ডেমো মোডে চলছি (ট্রেড এক্সিকিউট হবে না)")
    
    def _check_mt5_connection(self) -> bool:
        """MT5 সংযোগ অবস্থা চেক করুন"""
        if not self._mt5_connected:
            return False
        
        try:
            # সিম্বল তথ্য চেক করে সংযোগ যাচাই করুন
            info = mt5.symbol_info("XAUUSD")
            if info is None:
                logger.warning("⚠️ MT5 সংযোগ হারিয়েছে")
                self._mt5_connected = False
                return False
            return True
        except Exception as e:
            logger.error(f"❌ MT5 সংযোগ চেক ত্রুটি: {e}")
            self._mt5_connected = False
            return False
    
    def _init_agents(self) -> List[BaseAgent]:
        """সমস্ত এজেন্ট ইনিশিয়ালাইজ করুন"""
        logger.info("\n🤖 এজেন্ট ইনিশিয়ালাইজ হচ্ছে...")
        
        agents = [
            SentimentAgent(news_provider=None),
            PredictiveAgent(candle_provider=self.fetch_live_market_data),
            TransformerAgent(candle_provider=self.fetch_live_market_data),
            TechnicalAgent(candle_provider=self.fetch_live_market_data),
            LiquiditySweepVoter(candle_provider=self.fetch_live_market_data),
        ]
        
        logger.info(f"✅ {len(agents)}টি এজেন্ট ইনিশিয়ালাইজড:")
        for agent in agents:
            logger.info(f"   • {agent.name}")
        
        return agents
    
    # ===== মার্কেট ডেটা ফাংশন =====
    
    def fetch_live_market_data(self, symbol: str, lookback: int = 50) -> list:
        """
        MT5 থেকে লাইভ মার্কেট ডেটা আনুন
        
        Args:
            symbol: ট্রেড সিম্বল (যেমন XAUUSD)
            lookback: ফিরিয়ে আনতে হবে এমন ��্যান্ডেলের সংখ্যা
            
        Returns:
            ক্যান্ডেল ডেটার তালিকা
        """
        if not self._mt5_connected or not self._check_mt5_connection():
            logger.debug(f"⚠️ MT5 সংযুক্ত নয় - {symbol} এর ডেটা পাওয়া যাচ্ছে না")
            return []
        
        try:
            symbol = symbol.upper().strip()
            
            # H1 টাইমফ্রেমে সর্বশেষ ক্যান্ডেল আনুন
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, lookback)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"⚠️ {symbol} এর কোনো ডেটা পাওয়া যায়নি")
                return []
            
            # ডিকশনারি ফরম্যাটে রূপান্তর
            candles = []
            for rate in rates:
                candle = {
                    'time': int(rate['time']),
                    'open': float(rate['open']),
                    'high': float(rate['high']),
                    'low': float(rate['low']),
                    'close': float(rate['close']),
                    'volume': int(rate['tick_volume'])
                }
                candles.append(candle)
            
            logger.debug(f"✅ {symbol}: {len(candles)} ক্যান্ডেল আনা হয়েছে")
            return candles
            
        except Exception as e:
            logger.error(f"❌ {symbol} থেকে মার্কেট ডেটা ত্রুটি: {e}")
            return []
    
    # ===== মূল্য বৈধতা =====
    
    def _validate_price(self, price: float, symbol: str) -> bool:
        """
        মূল্য বৈধতা (একাধিক চেক)
        
        Args:
            price: যাচাই করার মূল্য
            symbol: সিম্বল
            
        Returns:
            সত্য যদি বৈধ, মিথ্যা অন্যথায়
        """
        # চেক ১: ইতিবাচক মূল্য
        if price <= 0:
            logger.error(f"❌ {symbol}: অবৈধ মূল্য (≤ 0): {price}")
            return False
        
        # চেক ২: অযৌক্তিক সর্বোচ্চ মূল্য
        if price > self.max_price:
            logger.error(f"❌ {symbol}: অযৌক্তিক মূল্য (> {self.max_price}): {price}")
            return False
        
        # চেক ৩: মূল্য জাম্প (পূর্ববর্তী মূল্যের সাথে)
        if symbol in self.previous_prices:
            prev_price = self.previous_prices[symbol]
            if prev_price > 0:
                price_change = abs(price - prev_price) / prev_price
                if price_change > self.price_jump_threshold:
                    logger.warning(
                        f"⚠️ {symbol}: বড় মূল্য জাম্প সনাক্ত - "
                        f"{prev_price:.2f} → {price:.2f} ({price_change*100:.1f}%)"
                    )
        
        # চেক ৪: টাইপ যাচাইকরণ
        try:
            float(price)
        except (ValueError, TypeError):
            logger.error(f"❌ {symbol}: মূল্য টাইপ রূপান্তর ব্যর্থ: {price}")
            return False
        
        # মূল্য সংরক্ষণ করুন পরবর্তী তুলনার জন্য
        self.previous_prices[symbol] = price
        
        return True
    
    # ===== ভোটিং চক্র =====
    
    def run_voting_cycle(self, symbol: str):
        """
        একটি সম্পূর্ণ ভোটিং চক্র চালান
        
        Args:
            symbol: ট্রেড করার সিম্বল
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 {symbol} ভোটিং চক্র শুরু - {datetime.now().isoformat()}")
        logger.info(f"{'='*70}")
        
        # ===== ১. এজেন্ট ভোট সংগ্রহ করুন =====
        votes: List[AgentVote] = []
        failed_agents = []
        
        logger.info(f"\n🗳️ এজেন্ট ভোট সংগ্রহ করছি ({len(self.agents)} এজেন্ট)...")
        
        for agent in self.agents:
            try:
                logger.debug(f"  ⏳ {agent.name} থেকে ভোট নিচ্ছি...")
                vote = agent.vote(symbol)
                
                if vote is None:
                    logger.warning(f"  ⚠️ {agent.name}: None ভোট রিটার্ন করেছে")
                    failed_agents.append(agent.name)
                    continue
                
                votes.append(vote)
                vote_str = {-1: "🔴 BEARISH", 0: "⚪ NEUTRAL", 1: "🟢 BULLISH"}[int(vote.vote)]
                logger.info(f"  ✅ {agent.name}: {vote_str} ({vote.confidence:.1f}%)")
                
            except Exception as e:
                logger.error(f"  ❌ {agent.name} ভোট সংগ্রহ ত্রুটি: {e}")
                failed_agents.append(agent.name)
        
        # ===== ২. এজেন্ট ব্যর্থতার হার চেক করুন =====
        failure_rate = len(failed_agents) / len(self.agents) if self.agents else 0
        
        if failed_agents:
            logger.warning(f"  ⚠️ ব্যর্থ এজেন্ট ({failure_rate*100:.0f}%): {', '.join(failed_agents)}")
        
        if failure_rate > self.max_agent_failure_rate:
            logger.critical(
                f"🚨 অত্যধিক এজেন্ট ব্যর্থ ({failure_rate*100:.1f}% > {self.max_agent_failure_rate*100:.1f}%) - "
                f"ট্রেডিং সাইকেল বাতিল করছি"
            )
            return
        
        if not votes:
            logger.error(f"❌ {symbol}: কোনো বৈধ ভোট পাওয়া যায়নি - বাতিল করছি")
            return
        
        # ===== ३. মেট্রিক্স রেকর্ড করুন =====
        self.metrics.record_votes(symbol, votes)
        
        # ===== ४. ভোট গণনা এবং শতাংশ গণনা করুন =====
        bullish_count = sum(1 for v in votes if v.vote == int(VoteDirection.BULLISH))
        bearish_count = sum(1 for v in votes if v.vote == int(VoteDirection.BEARISH))
        neutral_count = len(votes) - bullish_count - bearish_count
        
        bullish_pct = bullish_count / len(votes) if votes else 0
        bearish_pct = bearish_count / len(votes) if votes else 0
        
        # ===== ५. চূড়ান্ত সিদ্ধান্ত নিন =====
        final_decision = "HOLD"
        confidence_score = 0.0
        
        if bullish_pct >= self.consensus_threshold:
            final_decision = "BUY"
            confidence_score = bullish_pct
        elif bearish_pct >= self.consensus_threshold:
            final_decision = "SELL"
            confidence_score = bearish_pct
        else:
            final_decision = "HOLD"
            confidence_score = max(bullish_pct, bearish_pct)
        
        # ===== ६. সিদ্ধান্ত লগ করুন =====
        decision_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}[final_decision]
        logger.info(f"\n📊 ভোটিং ফলাফল {symbol}:")
        logger.info(f"  {decision_emoji} চূড়ান্ত সিদ্ধান্ত: {final_decision}")
        logger.info(f"     • BUY:  {bullish_count}/{len(votes)} ({bullish_pct*100:.1f}%)")
        logger.info(f"     • SELL: {bearish_count}/{len(votes)} ({bearish_pct*100:.1f}%)")
        logger.info(f"     • HOLD: {neutral_count}/{len(votes)} ({(neutral_count/len(votes))*100:.1f}%)")
        logger.info(f"     • সম্মতি আত্মবিশ্বাস: {confidence_score*100:.1f}%")
        logger.info(f"     • থ্রেশহোল্ড: {self.consensus_threshold*100:.0f}%")
        
        # সিদ্ধান্ত রেকর্ড করুন
        self.metrics.record_decision(symbol, final_decision)
        
        # ===== ७. সিদ্ধান্ত যথেষ্ট আত্মবিশ্বাসী হলে ট্রেড এক্সিকিউট করুন =====
        if final_decision in ["BUY", "SELL"] and confidence_score >= self.consensus_threshold:
            logger.info(f"\n🚀 {symbol} এর জন্য ট্রেড এক্সিকিউশন ট্রিগার করছি...")
            self._execute_trade(symbol, final_decision)
        else:
            logger.info(f"\n⏭️ {symbol}: সিদ্ধান্ত: {final_decision} - ট্রেড এক্সিকিউশন বাতিল")
    
    # ===== ট্রেড এক্সিকিউশন =====
    
    def _execute_trade(self, symbol: str, decision: str):
        """
        ট্রেড এক্সিকিউট করুন (MT5 সহ বা ডেমো)
        
        Args:
            symbol: ট্রেড করার সিম্বল
            decision: BUY বা SELL
        """
        try:
            # ১. মার্কেট ডেটা আনুন
            logger.info(f"  ① মার্কেট ডেটা আনছি...")
            candles = self.fetch_live_market_data(symbol, lookback=2)
            
            if not candles or len(candles) < 1:
                logger.error(f"  ❌ {symbol}: কোনো ক্যান্ডেল ডেটা পাওয়া যায়নি")
                return
            
            last_candle = candles[-1]
            
            # २. মূল্য নিরাপদে আনুন এবং বৈধতা করুন
            logger.info(f"  ② মূল্য বৈধতা করছি...")
            try:
                current_price = float(
                    last_candle['close'] if isinstance(last_candle, dict)
                    else getattr(last_candle, 'close', 0.0)
                )
            except (ValueError, TypeError, AttributeError) as e:
                logger.error(f"  ❌ {symbol}: মূল্য রূপান্তর ত্রুটি: {e}")
                return
            
            # মূল্য বৈধতা
            if not self._validate_price(current_price, symbol):
                logger.error(f"  ❌ {symbol}: মূল্য বৈধতা ব্যর্থ")
                return
            
            logger.info(f"  ✅ মূল্য বৈধ: {current_price:.2f}")
            
            # ३. স্টপ লস ডিস্ট্যান্স সেট করুন
            logger.info(f"  ③ স্টপ লস ডিস্ট্যান্স গণনা করছি...")
            
            if "BTC" in symbol.upper():
                sl_dist = 150.0  # বিটকয়েনের জন্য ১৫০ ডলার
                logger.debug(f"     BTC সিম্বল সনাক্ত - SL: {sl_dist}")
            elif "XAU" in symbol.upper() or "GOLD" in symbol.upper():
                sl_dist = 2.0    # গোল্ডের জন্য ২ ডলার
                logger.debug(f"     GOLD সিম্বল সনাক্ত - SL: {sl_dist}")
            else:
                sl_dist = 1.0    # ডিফল্ট
                logger.debug(f"     ডিফল্ট সিম্বল - SL: {sl_dist}")
            
            sl_price = current_price - sl_dist if decision == "BUY" else current_price + sl_dist
            logger.info(f"     SL দূরত্ব: {sl_dist}, SL মূল্য: {sl_price:.2f}")
            
            # ४. রিস্ক ক্যালকুলেশন
            logger.info(f"  ④ রিস্ক এবং লট সাইজ গণনা করছি...")
            risk_result = self.risk_manager.calculate_position(current_price, sl_price, symbol)
            
            if not risk_result or risk_result.get("status") != "Success":
                logger.error(f"  ❌ {symbol}: রিস্ক ক্যালকুলেশন ব্যর্থ: {risk_result}")
                return
            
            lot_size = risk_result['lot_size']
            logger.info(f"     লট সাইজ: {lot_size}")
            logger.info(f"     অনুমোদিত রিস্ক: ${risk_result['allowed_risk']:.2f}")
            
            # ५. ট্রেড এক্সিকিউশন
            logger.info(f"  ⑤ ট্রেড এক্সিকিউট করছি...")
            logger.info(f"     সিম্বল: {symbol}")
            logger.info(f"     সিদ্ধান্ত: {decision}")
            logger.info(f"     এন্ট্রি: {current_price:.2f}")
            logger.info(f"     স্টপ লস: {sl_price:.2f}")
            
            if self._mt5_connected and self._check_mt5_connection():
                # MT5 এ লাইভ এক্সিকিউট করুন
                result = self.trade_executor.execute_trade(
                    decision,
                    lot_size,
                    sl_price,
                    symbol
                )
                
                if result['status'] == 'success':
                    logger.info(f"  ✅ ট্রেড সফল এক্সিকিউট হয়েছে")
                    logger.info(f"     টিকেট: {result['ticket']}")
                else:
                    logger.error(f"  ❌ ট্রেড এক্সিকিউশন ব্যর্থ: {result}")
            else:
                logger.warning(f"  ⚠️ MT5 সংযুক্ত নয় - ডেমো মোড সিমুলেশন")
                logger.info(f"     [DEMO] {decision} {lot_size} লট @ {current_price:.2f}")
            
        except Exception as e:
            logger.error(f"  ❌ ট্রেড এক্সিকিউশন অপ্রত্যাশিত ত্রুটি: {e}", exc_info=True)
    
    # ===== শাটডাউন =====
    
    def shutdown(self):
        """অর্কেস্ট্রেটর গ্রেসফুলি শাটডাউন করুন"""
        logger.info("\n\n🛑 শাটডাউন শুরু হচ্ছে...")
        
        # মেট্রিক্স সামারি
        logger.info("\n📈 ফাইনাল মেট্রিক্স সামারি:")
        summary = self.metrics.get_summary()
        logger.info(f"   • মোট সিদ্ধান্ত: {summary['total_decisions']}")
        logger.info(f"   • কনসেনসাস সাফল্যের হার: {summary['consensus_success_rate']}%")
        logger.info(f"   • আপটাইম: {summary['uptime_seconds']/60:.1f} মিনিট")
        
        # এজেন্ট পারফরম্যান্স
        if summary['agent_metrics']:
            logger.info(f"\n   এজেন্ট পারফরম্যান্স:")
            for agent_name, metrics in summary['agent_metrics'].items():
                logger.info(f"     • {agent_name}:")
                logger.info(f"       - মোট ভোট: {metrics['total_votes']}")
                logger.info(f"       - গড় আত্মবিশ্বাস: {metrics['avg_confidence']:.1f}%")
        
        # MT5 সংযোগ বন্ধ করুন
        if self._mt5_connected:
            try:
                logger.info("\n🔌 MT5 সংযোগ বন্ধ করছি...")
                mt5.shutdown()
                logger.info("✅ MT5 সংযোগ বন্ধ হয়েছে")
            except Exception as e:
                logger.error(f"❌ MT5 শাটডাউন ত্রুটি: {e}")
        
        logger.info("\n✅ শাটডাউন সম্পন্ন")
