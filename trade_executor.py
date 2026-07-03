#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trade_executor.py - উন্নত MT5 ট্রেড এক্সিকিউশন রিট্রাই লজিক সহ
Enhanced Trade Execution with Retry Logic & Error Classification
"""
import logging
import time
from typing import Dict
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


class TradeExecutor:
    """MT5 ট্রেড এক্সিকিউশন যা রিট্রাই এবং ত্রুটি শ্রেণীকরণ সহ"""
    
    def __init__(self, deviation: int = 15, magic_number: int = 202699):
        """
        ট্রেড এক্সিকিউটর ইনিশিয়ালাইজ করুন
        
        Args:
            deviation: MT5 অর্ডার deviation পরামিতি
            magic_number: ট্রেড সনাক্তকরণের জন্য magic number
        """
        self.deviation = deviation
        self.magic_number = magic_number
        self.active_trades = {}
        
        logger.info(f"✅ ট্রেড এক্সিকিউটর ইনিশিয়ালাইজড")
        logger.info(f"   Deviation: {self.deviation}")
        logger.info(f"   Magic Number: {self.magic_number}")
    
    # ===== ত্রুটি শ্রেণীকরণ =====
    
    @staticmethod
    def _classify_error(retcode: int) -> str:
        """
        MT5 ত্রুটি কোড শ্রেণীকরণ করুন
        
        Args:
            retcode: MT5 রিটার্ন কোড
            
        Returns:
            'RETRYABLE', 'PERMANENT', বা 'UNKNOWN'
        """
        # পুনর্চেষ্টাযোগ্য ত্রুটি (অস্থায়ী সমস্যা)
        RETRYABLE_ERRORS = {
            mt5.TRADE_RETCODE_REQUOTE: "মূল্য পরিবর্তিত হয়েছে",
            mt5.TRADE_RETCODE_TIMEOUT: "অর্ডার সময় শেষ হয়েছে",
            10: "নেটওয়ার্ক ত্রুটি",
        }
        
        # স্থায়ী ত্রুটি (রিট্রাই করা বৃথা)
        PERMANENT_ERRORS = {
            mt5.TRADE_RETCODE_INVALID_PRICE: "অবৈধ মূল্য",
            mt5.TRADE_RETCODE_INVALID_VOLUME: "অবৈধ ভলিউম/লট",
            mt5.TRADE_RETCODE_INVALID_STOPS: "অবৈধ SL/TP",
            mt5.TRADE_RETCODE_SYMBOL_NOT_FOUND: "সিম্বল খুঁজে পাওয়া যায়নি",
        }
        
        if retcode in RETRYABLE_ERRORS:
            return "RETRYABLE"
        elif retcode in PERMANENT_ERRORS:
            return "PERMANENT"
        else:
            return "UNKNOWN"
    
    # ===== ট্রেড বৈধতা =====
    
    @staticmethod
    def _validate_trade_parameters(symbol: str, lot_size: float, 
                                   entry_price: float, sl_price: float) -> bool:
        """
        ট্রেড পরামিতি বৈধতা
        
        Args:
            symbol: ট্রেড সিম্বল
            lot_size: ভলিউম/লট
            entry_price: এন্ট্রি মূল্য
            sl_price: স্টপ লস মূল্য
            
        Returns:
            সত্য যদি বৈধ, মিথ্যা অন্যথায়
        """
        # লট সাইজ চেক
        if lot_size <= 0:
            logger.error(f"❌ অবৈধ লট সাইজ: {lot_size}")
            return False
        
        if lot_size > 100:
            logger.error(f"❌ লট সাইজ অত্যধিক বড়: {lot_size}")
            return False
        
        # মূল্য চেক
        if entry_price <= 0:
            logger.error(f"❌ অবৈধ এন্ট্রি মূল্য: {entry_price}")
            return False
        
        if sl_price <= 0:
            logger.error(f"❌ অবৈধ SL মূল্য: {sl_price}")
            return False
        
        # SL এবং এন্ট্রি সমান চেক
        if abs(entry_price - sl_price) < 0.00001:
            logger.error(f"❌ এন্ট্রি এবং SL প্রায় সমান")
            return False
        
        return True
    
    # ===== প্রধান ট্রেড এক্সিকিউশন =====
    
    def execute_trade(self, direction: str, lot_size: float, sl_price: float, 
                     symbol: str, max_retries: int = 3) -> Dict:
        """
        রিট্রাই লজিক সহ MT5 ট্রেড এক্সিকিউট করুন
        
        Args:
            direction: "BUY" বা "SELL"
            lot_size: পজিশন সাইজ (লট)
            sl_price: স্টপ লস মূল্য
            symbol: ট্রেড সিম্বল
            max_retries: সর্বোচ্চ পুনর্চেষ্টা সংখ্যা
            
        Returns:
            স্ট্যাটাস এবং বিস্তারিত সহ ডিকশনারি
        """
        symbol = symbol.upper().strip()
        direction = direction.upper().strip()
        
        logger.info(f"\n🚀 ট্রেড এক্সিকিউশন শুরু: {direction} {lot_size}L {symbol}")
        
        # রিট্রাই লুপ
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.warning(f"  প্রচেষ্টা {attempt + 1}/{max_retries} - {2 ** attempt}s অপেক্ষার পর...")
                    time.sleep(2 ** attempt)  # এক্সপোনেনশিয়াল ব্যাকঅফ
                
                # সিম্বল নির্বাচন করুন
                if not mt5.symbol_select(symbol, True):
                    if attempt < max_retries - 1:
                        logger.warning(f"  সিম্বল নির্বাচন ব্যর্থ - রিট্রাই করছি...")
                        continue
                    logger.error(f"  ❌ সিম্বল নির্বাচন ব্যর্থ: {symbol}")
                    return {"status": "failed", "reason": "সিম্বল নির্বাচন ব্যর্থ"}
                
                # টিক তথ্য আনুন
                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    if attempt < max_retries - 1:
                        logger.warning(f"  টিক তথ্য পাওয়া যাচ্ছে না - রিট্রাই করছি...")
                        continue
                    logger.error(f"  ❌ {symbol} এর জন্য টিক তথ্য পাওয়া যায়নি")
                    return {"status": "failed", "reason": "টিক ডেটা উপলব্ধ নেই"}
                
                # এন্ট্রি মূল্য নির্ধারণ করুন
                entry_price = tick.ask if direction == "BUY" else tick.bid
                action = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
                
                # পরামিতি বৈধতা
                if not self._validate_trade_parameters(symbol, lot_size, entry_price, sl_price):
                    logger.error(f"  ❌ ট্রেড পরামিতি বৈধতা ব্যর্থ")
                    return {"status": "failed", "reason": "ট্রেড পরামিতি বৈধ নয়"}
                
                # TP ক্যালকুলেট করুন
                sl_distance = abs(entry_price - sl_price)
                tp_price = entry_price + sl_distance if direction == "BUY" else entry_price - sl_distance
                
                logger.debug(f"  এন্ট্রি: {entry_price:.2f}, SL: {sl_price:.2f}, TP: {tp_price:.2f}")
                
                # ট্রেড রিকোয়েস্ট তৈরি করুন
                trade_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot_size,
                    "type": action,
                    "price": entry_price,
                    "sl": sl_price,
                    "tp": tp_price,
                    "deviation": self.deviation,
                    "magic": self.magic_number,
                    "comment": f"AI Bot {direction}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC
                }
                
                # অর্ডার পাঠান
                logger.debug(f"  অর্ডার পাঠাচ্ছি...")
                result = mt5.order_send(trade_request)
                
                # ফলাফল পরীক্ষা করুন
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    # সফল!
                    ticket = result.order
                    self.active_trades[str(ticket)] = {
                        "ticket": ticket,
                        "symbol": symbol,
                        "direction": direction,
                        "entry_price": entry_price,
                        "stop_loss": sl_price,
                        "take_profit": tp_price,
                        "current_lot": lot_size,
                        "remaining_lot": lot_size,
                        "status": "OPEN",
                        "tp1_hit": False,
                        "tp1_price": entry_price + (sl_distance * 0.5) if direction == "BUY" 
                                   else entry_price - (sl_distance * 0.5),
                        "created_at": time.time()
                    }
                    
                    logger.info(f"  ✅ ট্রেড সফল!")
                    logger.info(f"     টিকেট: {ticket}")
                    logger.info(f"     এন্ট্রি: {entry_price:.2f}")
                    logger.info(f"     SL: {sl_price:.2f}")
                    logger.info(f"     TP: {tp_price:.2f}")
                    
                    return {
                        "status": "success",
                        "ticket": ticket,
                        "entry_price": entry_price,
                        "lot_size": lot_size,
                        "attempt": attempt + 1
                    }
                
                # অর্থপূর্ণ ত্রুটি কোড
                error_classification = self._classify_error(result.retcode)
                error_msg = mt5.last_error()
                
                logger.warning(f"  অর্ডার রিটার্ন কোড: {result.retcode} ({error_msg})")
                logger.warning(f"  ত্রুটি শ্রেণী: {error_classification}")
                
                if error_classification == "RETRYABLE" and attempt < max_retries - 1:
                    logger.warning(f"  পুনর্চেষ্টাযোগ্য ত্রুটি - রিট্রাই করছি...")
                    continue
                else:
                    logger.error(f"  স্থায়ী ত্রুটি বা সর্বোচ্চ প্রচেষ্টা পৌঁছেছে")
                    return {
                        "status": "failed",
                        "retcode": result.retcode,
                        "reason": f"অর্ডার ব্যর্থ: {error_msg}",
                        "attempt": attempt + 1
                    }
                
            except Exception as e:
                logger.error(f"  এক্সিকিউশন ত্রুটি (প্রচেষ্টা {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    logger.warning(f"  রিট্রাই করছি...")
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"  সর্বোচ্চ প্রচেষ্টা অতিক্রম করেছে")
                    return {"status": "failed", "reason": str(e), "attempt": attempt + 1}
        
        # সব প্রচেষ্টা শেষ
        logger.error(f"❌ ট্রেড এক্সিকিউশন সব প্রচেষ্টার পরে ব্যর্থ")
        return {"status": "failed", "reason": "সর্বোচ্চ রিট্রাই সংখ্যা অতিক্রম করেছে"}
    
    # ===== হেল্পার মেথড =====
    
    def _get_current_price(self, symbol: str, direction: str) -> float:
        """বর্তমান মূল্য আনুন"""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return tick.ask if direction == "BUY" else tick.bid
        except:
            pass
        return 0.0
    
    def process_market_update(self, ticket: str, current_price: float) -> list:
        """
        লাইভ মার্কেট আপডেট প্রসেস করুন
        (পার্শিয়াল প্রফিট এবং ব্রেক-ইভেন)
        
        Args:
            ticket: ট্রেড টিকেট নম্বর
            current_price: বর্তমান মার্কেট প্রাইস
            
        Returns:
            লগ মেসেজের তালিকা
        """
        logs = []
        
        if str(ticket) not in self.active_trades:
            logs.append(f"❌ ট্রেড খুঁজে পাওয়া যায়নি: {ticket}")
            return logs
        
        trade = self.active_trades[str(ticket)]
        
        if trade["status"] == "CLOSED":
            logs.append(f"⏸️ ট্রেড ইতিমধ্যে বন্ধ: {ticket}")
            return logs
        
        # TP1 চেক (৫০% পার্শিয়াল)
        if not trade["tp1_hit"]:
            tp1_triggered = False
            if trade["direction"] == "BUY" and current_price >= trade["tp1_price"]:
                tp1_triggered = True
            elif trade["direction"] == "SELL" and current_price <= trade["tp1_price"]:
                tp1_triggered = True
            
            if tp1_triggered:
                trade["tp1_hit"] = True
                trade["stop_loss"] = trade["entry_price"]
                trade["remaining_lot"] = round(trade["remaining_lot"] * 0.5, 2)
                logs.append(f"🎉 TP1 হিট! ৫০% প্রফিট বুকড")
                logs.append(f"   স্টপ লস ব্রেক-ইভেনে: {trade['entry_price']:.2f}")
        
        # SL/BE চেক
        sl_hit = False
        if trade["direction"] == "BUY" and current_price <= trade["stop_loss"]:
            sl_hit = True
        elif trade["direction"] == "SELL" and current_price >= trade["stop_loss"]:
            sl_hit = True
        
        if sl_hit:
            trade["status"] = "CLOSED"
            if trade["tp1_hit"]:
                logs.append(f"✅ ব্রেক-ইভেনে ট্রেড ক্লোজড")
            else:
                logs.append(f"🚨 স্টপ লস ট্রিগার - ১% লস")
        
        return logs
