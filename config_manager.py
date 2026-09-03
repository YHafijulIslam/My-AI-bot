#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_manager.py - নিরাপদ কনফিগারেশন ম্যানেজমেন্ট এবং যাচাইকরণ মডিউল
Secure Configuration Management with Validation & Security Checks
Consolidated Exness Trading Configuration Management
"""
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class ExnessConfig:
    """Exness ব্রোকার নির্দিষ্ট কনফিগারেশন"""
    
    # Exness MT5 সার্ভার তালিকা
    EXNESS_SERVERS = {
        "demo": ["ExnessMT5Demo1", "ExnessMT5Demo2", "ExnessMT5Demo3"],
        "live": ["ExnessMT5Real1", "ExnessMT5Real2", "ExnessMT5Real3"]
    }
    
    # Exness অ্যাকাউন্ট প্রোফাইল
    ACCOUNT_PROFILES = {
        "standard": {
            "leverage": 1,
            "min_deposit": 10.0,
            "description": "স্ট্যান্ডার্ড প্রোফাইল - ন্যূনতম রিস্ক"
        },
        "professional": {
            "leverage": 100,
            "min_deposit": 200.0,
            "description": "প্রফেশনাল প্রোফাইল - উচ্চ লিভারেজ"
        },
        "exclusive": {
            "leverage": 500,
            "min_deposit": 5000.0,
            "description": "এক্সক্লুসিভ প্রোফাইল - সর্বোচ্চ লিভারেজ"
        }
    }
    
    # সমর্থিত ট্রেডিং জোড়া এবং সেটিংস
    TRADING_SYMBOLS = {
        "XAUUSD": {
            "description": "স্বর্ণ/ডলার",
            "sl_distance": 2.0,        # পয়েন্টে স্টপ লস ডিস্ট্যান্স
            "min_lot_size": 0.01,      # ন্যূনতম লট সাইজ
            "max_lot_size": 100.0,     # সর্বোচ্চ লট সাইজ
            "default_timeframe": "H1"  # ডিফল্ট টাইমফ্রেম
        },
        "BTCUSD": {
            "description": "বিটকয়েন/ডলার",
            "sl_distance": 150.0,      # বিটকয়েনের জন্য বৃহত্তর ডিস্ট্যান্স
            "min_lot_size": 0.01,
            "max_lot_size": 100.0,
            "default_timeframe": "H1"
        },
        "EURUSD": {
            "description": "ইউরো/ডলার",
            "sl_distance": 100.0,
            "min_lot_size": 0.01,
            "max_lot_size": 100.0,
            "default_timeframe": "H1"
        },
        "GBPUSD": {
            "description": "পাউন্ড/ডলার",
            "sl_distance": 100.0,
            "min_lot_size": 0.01,
            "max_lot_size": 100.0,
            "default_timeframe": "H1"
        }
    }


class ConfigManager:
    """নিরাপদ কনফিগারেশন লোডিং এবং যাচাইকরণ"""
    
    # ডিফল্ট ক��ফিগারেশন মান (সম্পূর্ণভাবে একীভূত)
    DEFAULTS = {
        # ===== Exness অ্যাকাউন্ট সেটিংস =====
        "account": {
            "account_number": None,        # বাধ্যতামূলক
            "password": None,              # বাধ্যতামূলক
            "server": "ExnessMT5Demo1",   # ডেমো সার্ভার (ডিফল্ট)
            "profile": "standard",         # অ্যাকাউন্ট প্রোফাইল
            "leverage": 1,                 # লিভারেজ স্তর
            "is_demo": True                # ডেমো অ্যাকাউন্ট ফ্ল্যাগ
        },
        
        # ===== MT5 সংযোগ সেটিংস =====
        "mt5": {
            "timeout": 10,                 # সংযোগ টাইমআউট (সেকেন্ড)
            "max_retries": 3,              # সর্বোচ্চ পুনরায় চেষ্টার সংখ্যা
            "retry_delay": 5,              # পুনরায় চেষ্টার মধ্যে বিলম্ব (সেকেন্ড)
            "check_interval": 60,          # সংযোগ চেক বিরতি (সেকেন্ড)
            "enable_auto_reconnect": True  # স্বয়ংক্রিয় পুনঃসংযোগ সক্ষম
        },
        
        # ===== ট্রেডিং কনফিগারেশন =====
        "trading": {
            "account_balance": 10000.0,                # অ্যাকাউন্ট ব্যালেন্স (ডলার)
            "risk_percentage": 1.0,                    # প্রতি ট্রেডে ঝুঁকি শতাংশ
            "consensus_threshold": 0.6,                # সিদ্ধান্তের জন্য সম্মতি (60%)
            "max_agent_failure_rate": 0.4,            # সর্বোচ্চ এজেন্ট ব্যর্থতার হার (40%)
            "symbols": ["XAUUSD", "BTCUSD"],          # ট্রেড করার সিম্বল
            "max_daily_trades": 10,                    # প্রতিদিন সর্বোচ্চ ট্রেড
            "max_open_positions": 3,                   # একযোগে খোলা অবস্থানের সংখ্যা
            "profit_target_percentage": 2.0,           # মুনাফা লক্ষ্য শতাংশ
            "breakeven_after_tp1": True                # TP1 এর পরে ব্রেক-ইভেন সেট করুন
        },
        
        # ===== ট্রেডিং চক্র সেটিংস =====
        "cycle": {
            "interval_seconds": 900,                   # চক্র বিরতি (15 মিনিট)
            "symbol_delay_seconds": 5,                 # সিম্বলের মধ্যে বিলম্ব
            "enable_weekend_trading": False,           # সপ্তাহান্তে ট্রেডিং সক্ষম করুন
            "trading_start_hour": 0,                   # ট্রেডিং শুরুর ঘন্টা (UTC)
            "trading_end_hour": 23                     # ট্রেডিং শেষ ঘন্টা (UTC)
        },
        
        # ===== মূল্য বৈধতা সেটিংস =====
        "validation": {
            "max_price": 1_000_000,                   # সর্বোচ্চ মূল্য সীমা
            "price_jump_threshold": 0.1,              # মূল্য জাম্প থ্রেশহোল্ড (10%)
            "min_lot_size": 0.01,                     # ন্যূনতম লট সাইজ
            "max_lot_size": 100.0                     # সর্বোচ্চ লট সাইজ
        },
        
        # ===== লগিং সেটিংস =====
        "logging": {
            "level": "INFO",                          # লগিং লেভেল
            "file_dir": "logs",                       # লগ ডিরেক্টরি
            "max_bytes": 10485760,                    # ম্যাক্স ফাইল সাইজ (10 MB)
            "backup_count": 5,                        # ব্যাকআপ ফাইলের সংখ্যা
            "format": "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"
        },
        
        # ===== সিকিউরিটি সেটিংস =====
        "security": {
            "require_2fa": False,                     # দুই-ফ্যাক্টর প্রমাণীকরণ
            "ssl_verify": True,                       # SSL প্রমাণীকরণ
            "file_permission": "0o600",               # কনফিগ ফাইল অনুমতি
            "encrypt_credentials": False              # শংসাপত্র এনক্রিপশন
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
        সম্পূর্ণ কনফিগারেশন যাচাইকরণ (Exness সংযোগ + ট্রেডিং সেটিংস)
        
        Args:
            config: যাচাই করার কনফিগ
            
        Returns:
            সত্য যদি বৈধ, মিথ্যা অন্যথায়
        """
        logger.info("🔍 কনফিগারেশন যাচাইকরণ শুরু...")
        
        # ===== Exness অ্যাকাউন্ট সেটিংস যাচাইকরণ =====
        account_config = config.get("account", {})
        
        # প্রয়োজনীয় অ্যাকাউন্ট কী
        required_account_keys = ["account_number", "password", "server"]
        for key in required_account_keys:
            if key not in account_config or not account_config[key]:
                logger.error(f"❌ প্রয়োজনীয় অ্যাকাউন��ট কনফিগ কী নেই: {key}")
                return False
        
        # সার্ভার বৈধতা
        server = account_config.get("server", "")
        all_servers = ExnessConfig.EXNESS_SERVERS["demo"] + ExnessConfig.EXNESS_SERVERS["live"]
        if server not in all_servers:
            logger.warning(f"⚠️ সার্ভার '{server}' স্বীকৃত নয়: {all_servers}")
        
        # প্রোফাইল বৈধতা
        profile = account_config.get("profile", "standard")
        if profile not in ExnessConfig.ACCOUNT_PROFILES:
            logger.error(f"❌ অজানা অ্যাকাউন্ট প্রোফাইল: {profile}")
            return False
        
        # ===== MT5 কনফিগারেশন যাচাইকরণ =====
        mt5_config = config.get("mt5", {})
        
        if mt5_config.get("timeout", 0) <= 0:
            logger.error("❌ MT5 টাইমআউট অবশ্যই > 0 হতে হবে")
            return False
        
        if mt5_config.get("max_retries", 0) < 0:
            logger.error("❌ MT5 max_retries অবশ্যই >= 0 হতে হবে")
            return False
        
        # ===== ট্রেডিং কনফিগারেশন যাচাইকরণ =====
        trading_config = config.get("trading", {})
        
        try:
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
            
            # সিম্বল বৈধতা
            symbols = trading_config.get("symbols", [])
            if not symbols:
                logger.error("❌ অন্তত একটি ট্রেডিং সিম্বল প্রয়োজন")
                return False
            
            for symbol in symbols:
                if symbol not in ExnessConfig.TRADING_SYMBOLS:
                    logger.warning(f"⚠️ সিম্বল '{symbol}' সুপারিশকৃত নয়")
            
            logger.info("✅ কনফিগারেশন যাচাইকরণ সফল")
            return True
            
        except (ValueError, TypeError) as e:
            logger.error(f"❌ কনফিগ মূল্য ত্রুটি: {e}")
            return False
    
    @staticmethod
    def get_exness_server(is_demo: bool = True, server_index: int = 0) -> str:
        """
        Exness MT5 সার্ভার পান
        
        Args:
            is_demo: ডেমো সার্ভার চাই কিনা
            server_index: সার্ভার তালিকায় ইন্ডেক্স
            
        Returns:
            Exness সার্ভার নাম
        """
        server_type = "demo" if is_demo else "live"
        servers = ExnessConfig.EXNESS_SERVERS.get(server_type, [])
        
        if not servers:
            logger.warning(f"⚠️ {server_type} সার্ভার পাওয়া যায়নি")
            return "ExnessMT5Demo1"
        
        return servers[min(server_index, len(servers) - 1)]
    
    @staticmethod
    def get_symbol_config(symbol: str) -> Optional[Dict[str, Any]]:
        """
        সিম্বলের জন্য Exness নির্দিষ্ট কনফিগ পান
        
        Args:
            symbol: ট্রেডিং সিম্বল (যেমন XAUUSD)
            
        Returns:
            সিম্বল কনফিগ ডিকশনারি বা None
        """
        return ExnessConfig.TRADING_SYMBOLS.get(symbol.upper(), None)
    
    @staticmethod
    def get_account_profile(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        অ্যাকাউন্ট প্রোফাইল বিস্তারিত পান
        
        Args:
            config: কনফিগারেশন ডিকশনারি
            
        Returns:
            প্রোফাইল বিস্তারিত
        """
        profile_name = config.get("account", {}).get("profile", "standard")
        return ExnessConfig.ACCOUNT_PROFILES.get(
            profile_name,
            ExnessConfig.ACCOUNT_PROFILES["standard"]
        )
    
    @staticmethod
    def get_sl_distance(symbol: str, default: float = 1.0) -> float:
        """
        সিম্বলের জন্য স্টপ লস ডিস্ট্যান্স পান
        
        Args:
            symbol: ট্রেডিং সিম্বল
            default: ডিফল্ট ডিস্ট্যান্স
            
        Returns:
            স্টপ লস ডিস্ট্যান্স (পয়েন্ট)
        """
        symbol_config = ConfigManager.get_symbol_config(symbol)
        if symbol_config:
            return symbol_config.get("sl_distance", default)
        return default
    
    @staticmethod
    def _merge_configs(defaults: Dict[str, Any], 
                       user_config: Dict[str, Any]) -> Dict[str, Any]:
        """ডিফল্ট এবং ব্যবহারকারী কনফিগ মার্জ করুন"""
        result = {}
        
        # প্রথমে ডিফল্ট কপি করুন
        for key, value in defaults.items():
            if isinstance(value, dict):
                result[key] = value.copy()
            else:
                result[key] = value
        
        # তারপর ব্যবহারকারী কনফিগ মার্জ করুন
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
    
    @staticmethod
    def get_account_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Exness অ্যাকাউন্ট নির্দিষ্ট কনফিগ আনুন"""
        return config.get("account", ConfigManager.DEFAULTS["account"])
    
    @staticmethod
    def get_cycle_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """ট্রেডিং চক্র নির্দিষ্ট কনফিগ আনুন"""
        return config.get("cycle", ConfigManager.DEFAULTS["cycle"])
    
    @staticmethod
    def create_sample_config_file(filepath: str = "exness_config_sample.json") -> bool:
        """
        নমুনা কনফিগ ফাইল তৈরি করুন (শুরু করার জন্য)
        
        Args:
            filepath: নমুনা ফাইলের পাথ
            
        Returns:
            সাফল্য বা ব্যর্থতা
        """
        sample_config = {
            "account": {
                "account_number": "YOUR_EXNESS_ACCOUNT_NUMBER",
                "password": "YOUR_EXNESS_PASSWORD",
                "server": "ExnessMT5Demo1",
                "profile": "standard",
                "leverage": 1,
                "is_demo": True
            },
            "mt5": {
                "timeout": 10,
                "max_retries": 3,
                "retry_delay": 5,
                "check_interval": 60
            },
            "trading": {
                "account_balance": 10000.0,
                "risk_percentage": 1.0,
                "consensus_threshold": 0.6,
                "symbols": ["XAUUSD", "BTCUSD"],
                "max_daily_trades": 10,
                "max_open_positions": 3
            },
            "cycle": {
                "interval_seconds": 900,
                "symbol_delay_seconds": 5
            }
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(sample_config, f, indent=2)
            logger.info(f"✅ নমুনা কনফিগ তৈরি: {filepath}")
            return True
        except Exception as e:
            logger.error(f"❌ নমুনা কনফিগ তৈরিতে ত্রুটি: {e}")
            return False
