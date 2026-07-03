#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
risk_manager.py - ১% রিস্ক এবং পজিশন সাইজ ক্যালকুলেশন মডিউল
"""
import logging

log = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, account_balance: float = 10000.0, risk_percentage: float = 1.0):
        self.account_balance = account_balance
        self.risk_percentage = risk_percentage

    def calculate_position(self, entry_price: float, stop_loss_price: float, symbol: str) -> dict:
        """
        ১% রিস্ক অনুযায়ী সর্বোচ্চ কত লট নিয়ে এন্ট্রি করা যাবে তা হিসাব করে।
        """
        try:
            risk_amount = self.account_balance * (self.risk_percentage / 100.0)
            sl_distance = abs(entry_price - stop_loss_price)
            if sl_distance == 0:
                return {"status": "Error", "reason": "এন্ট্রি এবং স্টপ লস সমান হতে পারবে না"}
            
            # গোল্ডের স্পেশাল লট হিসাব (১ লটে ১ ডলার মুভমেন্ট = ১০০ ডলার লাভ/ক্ষতি)
            if "XAU" in symbol or "GOLD" in symbol:
                lot_size = risk_amount / (sl_distance * 100.0)
            else:
                # বিটকয়েন এবং সাধারণ কারেন্সি পেয়ার (১ লট = ১ ইউনিট)
                lot_size = risk_amount / sl_distance
                
            # ২ দশমিক স্থান পর্যন্ত রাউন্ড করা এবং সর্বনিম্ন ০.০১ লট নিশ্চিত করা
            lot_size = max(round(lot_size, 2), 0.01)
            return {
                "status": "Success",
                "allowed_risk": risk_amount,
                "lot_size": lot_size,
                "sl_distance": round(sl_distance, 2)
            }
        except Exception as e:
            log.error(f"রিস্ক ক্যালকুলেশনে ত্রুটি: {e}")
            return {"status": "Error", "reason": str(e)}
