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
            "symbols": ["XAUUSD", "BTCUSD"],
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
            
            # Unix পারমিশন চেক: অন্যদের জন্য পঠনযোগ্য?
            if os.name == 'posix':  # Linux/Mac
                if file_stat.st_mode & 0o077:  # অন্যরা পড়তে/লিখতে পারবে?
                    logger.critical(f"🔐 নিরাপত্তা ঝুঁকি: {config_path} অন্যদের জন্য অ্যাক্সেসযোগ্য!")
                    logger.info(f"ঠিক করুন: chmod 600 {config_path}")
                    return config
            
            # JSON লোড করুন
            with open(config_path, 'r') as f:
                user_config = json.load(f)
            
            logger.info(f"✅ কনফিগারেশন লোড সফল: {config_path}")
            
            # ব্যবহারকারী কনফিগ ডিফল্টের সাথে মার্জ করুন
            merged_config = ConfigManager._merge_configs(config, user_config)
            
            return merged_config
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ কনফিগ JSON ডিকোড ত্রুটি: {e}")
            logger.info("ডিফল্ট কনফিগারেশন ব্যবহার করছি")
            return config
        except PermissionError as e:
            logger.error(f"❌ কনফিগ ফাইল অনুমতি ত্রুটি: {e}")
            return config
        except Exception as e:
            logger.error(f"❌ কনফিগ লোডিং অপ্রত্যাশিত ত্রুটি: {e}", exc_info=True)
            return config
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """
        কনফিগারেশন যাচাইকরণ
        
        Args:
            config: যাচাই করার কনফিগ
            
        Returns:
            সত্য যদি বৈধ, মিথ্যা অন্যথায়
        """
        # প্রয়োজনীয় কী চেক করুন
        required_keys = ["account_number", "password", "server"]
        
        for key in required_keys:
            if key not in config or not config[key]:
                logger.error(f"❌ প্রয়োজনীয় কনফিগ কী নেই: {key}")
                return False
        
        # মূল্য বৈধতা
        try:
            trading_config = config.get("trading", {})
            
            # account_balance চেক
            balance = float(trading_config.get("account_balance", 10000))
            if balance <= 0:
                logger.error("❌ account_balance অবশ্যই > 0 হতে হবে")
                return False
            
            # risk_percentage চেক
            risk = float(trading_config.get("risk_percentage", 1.0))
            if not 0 < risk <= 10:
                logger.error("❌ risk_percentage 0-10% এর মধ্যে হতে হবে")
                return False
            
            # consensus_threshold চেক
            threshold = float(trading_config.get("consensus_threshold", 0.6))
            if not 0 < threshold < 1:
                logger.error("❌ consensus_threshold 0-1 এর মধ্যে হতে হবে")
                return False
            
            logger.info("✅ কনফিগারেশন যাচাইকরণ সফল")
            return True
            
        except (ValueError, TypeError) as e:
            logger.error(f"❌ কনফিগ মূল্য ত্রুটি: {e}")
            return False
    
    @staticmethod
    def _merge_configs(defaults: Dict[str, Any], 
                       user_config: Dict[str, Any]) -> Dict[str, Any]:
        """ডিফল্ট এবং ব্যবহারকারী কনফিগ মার্জ করুন"""
        result = defaults.copy()
        for key, value in user_config.items():
            if isinstance(value, dict) and key in result:
                result[key].update(value)
            else:
                result[key] = value
        return result
    
    @staticmethod
    def get_mt5_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """MT5 নির্দিষ্ট কনফিগ আনুন"""
        return config.get("mt5", ConfigManager.DEFAULTS["mt5"])
    
    @staticmethod
    def get_trading_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """ট্রেডিং নির্দিষ্ট কনফিগ আনুন"""
        return config.get("trading", ConfigManager.DEFAULTS["trading"])
    
    @staticmethod
    def get_validation_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """বৈধতা নির্দিষ্ট কনফিগ আনুন"""
        return config.get("validation", ConfigManager.DEFAULTS["validation"])
