#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trade_executor.py - পার্শিয়াল প্রফিট বুকিং এবং ব্রেক-ইভেন ট্রেলিং মডিউল
"""
import logging

log = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self):
        # রানিং ট্রেডগুলো জমা রাখার ডিকশনারি
        self.active_trades = {}

    def process_market_update(self, trade_id: str, current_price: float) -> list:
        """
        লাইভ মার্কেট প্রাইস আপডেট নিয়ে পার্শিয়াল ক্লোজ এবং ব্রেক-ইভেনে আনার কাজ করে।
        """
        logs = []
        if trade_id not in self.active_trades:
            return ["ট্রেডটি খুঁজে পাওয়া যায়নি"]
            
        t = self.active_trades[trade_id]
        if t["status"] == "CLOSED":
            return ["ট্রেডটি অলরেডি ক্লোজড হয়ে গেছে"]

        # ১. টার্গেট ১ বা পার্শিয়াল বুকিং (TP1) চেক
        if not t["tp1_hit"]:
            if (t["direction"] == "BUY" and current_price >= t["tp1"]) or \
               (t["direction"] == "SELL" and current_price <= t["tp1"]):
                t["tp1_hit"] = True
                t["stop_loss"] = t["entry_price"]  # স্টপ লস ব্রেক-ইভেনে (এন্ট্রি প্রাইসে) নিয়ে আসা
                t["current_lot"] = round(t["current_lot"] * 0.5, 2)  # ৫০% ভলিউম বা লট ক্লোজ করা
                logs.append(f"🎉 TP1 হিট করেছে! ৫০% প্রফিট বুকড। স্টপ লস এন্ট্রি প্রাইস {t['entry_price']}-এ ট্রেল করা হয়েছে। অবশিষ্ট লট: {t['current_lot']}")

        # ২. স্টপ লস বা ব্রেক-ইভেন হিট করেছে কিনা চেক
        if (t["direction"] == "BUY" and current_price <= t["stop_loss"]) or \
           (t["direction"] == "SELL" and current_price >= t["stop_loss"]):
            t["status"] = "CLOSED"
            reason = "ব্রেক-ইভেনে ক্লোজ হয়েছে (কোনো লস হয়নি)" if t["tp1_hit"] else "স্টপ লস হিট করেছে (১% রিস্ক লস)"
            logs.append(f"🚨 ট্রেড ক্লোজড! কারণ: {reason} @ কারেন্ট প্রাইস: {current_price}")
            
        if not logs:
            logs.append(f"ট্রেড রানিং... কারেন্ট প্রাইস: {current_price}, কারেন্ট এসএল: {t['stop_loss']}")
        return logs
