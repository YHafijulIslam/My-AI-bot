#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_manager.py - নিরাপদ কনফিগারেশন ম্যানেজমেন্ট এবং যাচাইকরণ মডিউল
Secure Configuration Management with Validation & Security Checks
"""
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """নিরাপদ কনফিগারেশন লোডিং এবং যাচাইকরণ"""
    
    # ডিফল্ট কনফিগারেশন মান
    DEFAULTS = {
        "mt5": {
            "timeout": 10,
            "max_retries": 3,
            "retry_delay": 5,
            "check_interval": 60
        },
        "trading": {
            "account_balance": 10000.0,
            "risk_percentage": 1.0,
            "consensus_threshold": 0.6,  # 60%
            # keep only Gold pair by default
            "symbols": ["XAUUSD"],
            "max_agent_failure_rate": 0.4  # 40%
        },
        "cycle": {
            "interval_seconds": 900,  # 15 মিনিট
            "symbol_delay_seconds": 5
        },
        "validation": {
            "max_price": 1_000_000,
            "price_jump_threshold": 0.1,  # 10%
            "min_lot_size": 0.01,
            "max_lot_size": 100.0
        },
        "logging": {
            "level": "INFO",
            "file_dir": "logs",
            "max_bytes": 10485760,  # 10 MB
            "backup_count": 5
        }
    }
    
    @staticmethod
    def load_config(config_path: str = "exness_config.json") -> Dict[str, Any]:
        """
        নিরাপদে কনফিগারেশন ফাইল লোড করুন
        
        Args:
            config_path: কনফিগ ফাইলের পাথ
            
        Returns:
            মার্জ করা কনফিগারেশন ডিকশনারি
        """
        config = ConfigManager.DEFAULTS.copy()
        
        if not os.path.exists(config_path):
            logger.warning(f"⚠️ কনফিগ ফাইল পাওয়া যায়নি: {config_path}")
            logger.info("ডিফল্ট কনফিগারেশন ব্যবহার করছি")
            return config
        
        try:
            # ফাইল পারমিশন নিরাপত্তা চেক
            file_stat = os.stat(config_path)
