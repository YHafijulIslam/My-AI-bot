#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_manager.py - নিরাপদ কনফিগারেশন ম্যানেজমেন্ট এবং যাচাইকরণ মডিউল
Secure Configuration Management with Validation & Security Checks
Consolidated Exness Trading Configuration & Credentials Management
"""
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import base64
import hashlib

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


class CredentialsManager:
    """সংবেদনশীল শংসাপত্র এবং API কী ব্যবস্থাপনা"""
    
    # সমস্ত সংবেদনশীল ক্ষেত্র
    SENSITIVE_FIELDS = {
        "account_number", "password", "api_key", "secret_key",
        "token", "access_token", "refresh_token",
        "news_api_key", "crypto_api_key", "webhook_token",
        "slack_webhook", "telegram_token"
    }
    
    @staticmethod
    def mask_credential(value: str, show_chars: int = 4) -> str:
        """
        শংসাপত্র মাস্ক করুন (লগিংয়ের জন্য)
        
        Args:
            value: মূল শংসাপত্র
            show_chars: শেষ কতটি ক্যারেক্টার দেখাবেন
            
        Returns:
            মাস্কড শংসাপত্র
        """
        if not value or len(value) < show_chars + 4:
            return "***REDACTED***"
        return f"{value[:show_chars]}{'*' * (len(value) - show_chars * 2)}{value[-show_chars:]}"
    
    @staticmethod
    def hash_credential(value: str) -> str:
        """শংসাপত্র হ্যাশ করুন (যাচাইকরণের জন্য)"""
        if not value:
            return None
        return hashlib.sha256(value.encode()).hexdigest()


class MTConfigDefaults:
    """MT5 এবং ট্রেডিং প্ল্যাটফর্ম কনফিগারেশন"""
    
    # MT5 এক্সিকিউশন সেটিংস
    MT5_EXECUTION = {
        "magic_number": 202699,           # ট্রেড সনাক্তকরণ সংখ্যা
        "deviation": 15,                   # অর্ডার deviation পয়েন্ট
        "max_retries": 3,                  # সর্বোচ্চ পুনর্চেষ্টা
        "retry_delay": 2,                  # পুনর্চেষ্টার মধ্যে বিলম্ব
        "order_timeout": 10,               # অর্ডার টাইমআউট
        "comment_prefix": "AI_Bot"         # অর্ডার মন্তব্য উপসর্গ
    }
    
    # MT5 সিম্বল সেটিংস
    MT5_SYMBOL_DEFAULTS = {
        "min_volume": 0.01,                # ন্যূনতম ভলিউম
        "max_volume": 100.0,               # সর্বোচ্চ ভলিউম
        "volume_step": 0.01,               # ভলিউম ধাপ
        "enable_sl_tp": True,              # SL/TP সক্ষম
        "order_filling_policy": "IOC"      # অর্ডার পূরণ নীতি
    }
    
    # এজেন্ট কনফিগারেশন (ডিফল্ট লুকব্যাক পিরিয়ড)
    AGENT_LOOKBACK = {
        "TechnicalAgent": 20,
        "PredictiveAgent": 50,
        "TransformerAgent": 100,
        "LiquiditySweepVoter": 30,
        "SentimentAgent": 14  # দিন
    }
    
    # এজেন্ট মডেল পাথ
    AGENT_MODELS = {
        "TransformerAgent": "models/transformer_model.pt",
        "PredictiveAgent": "models/lstm_model.h5",
        "LiquiditySweepVoter": None  # কোন পূর্ব-প্রশিক্ষিত মডেল নেই
    }


class APICredentials:
    """তৃতীয় পক্ষের API শংসাপত্র"""
    
    # সংবাদ এবং সেন্টিমেন্ট বিশ্লেষণ
    NEWS_APIS = {
        "newsapi": {
            "provider_name": "NewsAPI",
            "api_key_field": "api_key",
            "endpoint": "https://newsapi.org/v2",
            "description": "বিশ্বব্যাপী সং��াদ এবং সেন্টিমেন্ট ডেটা",
            "rate_limit": 100  # প্রতি মিনিটে অনুরোধ
        },
        "alphavantage": {
            "provider_name": "AlphaVantage",
            "api_key_field": "api_key",
            "endpoint": "https://www.alphavantage.co",
            "description": "ঐতিহাসিক ডেটা এবং সূচক",
            "rate_limit": 5
        },
        "finnhub": {
            "provider_name": "Finnhub",
            "api_key_field": "api_key",
            "endpoint": "https://finnhub.io/api/v1",
            "description": "রিয়েল-টাইম বাজার ডেটা",
            "rate_limit": 60
        }
    }
    
    # বিজ্ঞপ্তি এবং সতর্কতা
    NOTIFICATION_APIS = {
        "slack": {
            "provider_name": "Slack",
            "credential_field": "webhook_url",
            "description": "Slack বিজ্ঞপ্তি এবং সতর্কতা"
        },
        "telegram": {
            "provider_name": "Telegram",
            "credential_fields": ["bot_token", "chat_id"],
            "description": "Telegram বার্তা এবং সতর্কতা"
        },
        "email": {
            "provider_name": "Email SMTP",
            "credential_fields": ["smtp_server", "smtp_port", "username", "password"],
            "description": "ইমেল বিজ্ঞপ্তি"
        }
    }
    
    # ওয়েবহুক এবং এক্সটার্নাল সার্ভিস
    WEBHOOK_CREDENTIALS = {
        "gocharting": {
            "provider_name": "GoCharting",
            "credential_field": "api_token",
            "description": "GoCharting চার্ট বিশ্লেষণ সতর্কতা",
            "webhook_secret": "webhook_secret"  # HMAC যাচাইকরণের জন্য
        },
        "tradingview": {
            "provider_name": "TradingView",
            "credential_field": "webhook_secret",
            "description": "TradingView সতর্কতা"
        }
    }


class ConfigManager:
    """নিরাপদ কনফিগারেশ��� লোডিং এবং যাচাইকরণ"""
    
    # ডিফল্ট কনফিগারেশন মান (সম্পূর্ণভাবে একীভূত)
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
            "retry_delay": 5,              # পুন��ায় চেষ্টার মধ্যে বিলম্ব (সেকেন্ড)
            "check_interval": 60,          # সংযোগ চেক বিরতি (সেকেন্ড)
            "enable_auto_reconnect": True, # স্বয়ংক্রিয় পুনঃসংযোগ সক্ষম
            "magic_number": MTConfigDefaults.MT5_EXECUTION["magic_number"],
            "deviation": MTConfigDefaults.MT5_EXECUTION["deviation"],
            "order_timeout": MTConfigDefaults.MT5_EXECUTION["order_timeout"]
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
        
        # ===== এজেন্ট কনফিগারেশন =====
        "agents": {
            "TechnicalAgent": {
                "enabled": True,
                "lookback": MTConfigDefaults.AGENT_LOOKBACK["TechnicalAgent"],
                "name": "TechnicalAgent",
                "weight": 1.0
            },
            "PredictiveAgent": {
                "enabled": True,
                "lookback": MTConfigDefaults.AGENT_LOOKBACK["PredictiveAgent"],
                "name": "PredictiveAgent",
                "model_path": MTConfigDefaults.AGENT_MODELS.get("PredictiveAgent"),
                "weight": 1.0
            },
            "TransformerAgent": {
                "enabled": True,
                "lookback": MTConfigDefaults.AGENT_LOOKBACK["TransformerAgent"],
                "name": "TransformerAgent",
                "model_path": MTConfigDefaults.AGENT_MODELS.get("TransformerAgent"),
                "weight": 1.0
            },
            "LiquiditySweepVoter": {
                "enabled": True,
                "lookback": MTConfigDefaults.AGENT_LOOKBACK["LiquiditySweepVoter"],
                "name": "LiquiditySweepVoter",
                "weight": 1.0
            },
            "SentimentAgent": {
                "enabled": True,
                "lookback": MTConfigDefaults.AGENT_LOOKBACK["SentimentAgent"],
                "name": "SentimentAgent",
                "weight": 1.0,
                "news_provider": None,
                "news_api_key": None  # সংবেদনশীল - .env থেকে আসে
            }
        },
        
        # ===== এক্সটার্নাল API এবং ওয়েবহুক =====
        "external_services": {
            "news_api": {
                "provider": "newsapi",                 # newsapi, alphavantage, finnhub
                "enabled": False,
                "api_key": None,                       # সংবেদনশীল - .env থেকে আসে
                "rate_limit": 100
            },
            "notification": {
                "slack": {
                    "enabled": False,
                    "webhook_url": None                # সংবেদনশীল - .env থেকে আসে
                },
                "telegram": {
                    "enabled": False,
                    "bot_token": None,                 # সংবেদনশীল - .env থেকে আসে
                    "chat_id": None
                },
                "email": {
                    "enabled": False,
                    "smtp_server": None,
                    "smtp_port": 587,
                    "username": None,                  # সংবেদনশীল - .env থেকে আসে
                    "password": None                   # সংবেদনশীল - .env থেকে আসে
                }
            },
            "webhooks": {
                "gocharting": {
                    "enabled": False,
                    "api_token": None,                 # সংবেদনশীল - .env থেকে আসে
                    "webhook_secret": None             # সংবেদনশীল - .env থেকে আসে
                },
                "tradingview": {
                    "enabled": False,
                    "webhook_secret": None             # সংবেদনশীল - .env থেকে আসে
                }
            }
        },
        
        # ===== লগিং সেটিংস =====
        "logging": {
            "level": "INFO",                          # লগিং লেভেল
            "file_dir": "logs",                       # লগ ডিরেক্টরি
            "max_bytes": 10485760,                    # ম্যাক্স ফাইল সাইজ (10 MB)
            "backup_count": 5,                        # ব্যাকআপ ফাইলের সংখ্যা
            "format": "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
            "mask_credentials": True                  # লগে শংসাপত্র মাস্ক করুন
        },
        
        # ===== সিকিউরিটি সেটিংস =====
        "security": {
            "require_2fa": False,                     # দুই-ফ্যাক্টর প্রমাণীকরণ
            "ssl_verify": True,                       # SSL প্রমাণীকরণ
            "file_permission": "0o600",               # কনফিগ ফাইল অনুমতি
            "encrypt_credentials": False,             # শংসাপত্র এনক্রিপশন
            "allowed_credential_sources": [           # অনুমোদিত উত্স
                "environment_variables",
                "config_file",
                "secure_vault"
            ]
        }
    }
    
    @staticmethod
    def load_config(config_path: str = "exness_config.json") -> Dict[str, Any]:
        """
        নিরাপদে কনফিগারেশন ফাইল লোড করুন এবং পরিবেশ ভেরিয়েবল মার্জ করুন
        
        Args:
            config_path: কনফিগ ফাইলের পাথ
            
        Returns:
            মার্জ করা কনফিগারেশন ডিকশনারি
        """
        config = ConfigManager.DEFAULTS.copy()
        
        # ১. ফাইল থেকে কনফিগ লোড করুন
        if os.path.exists(config_path):
            try:
                # ফাইল পারমিশন নিরাপত্তা চেক
                file_stat = os.stat(config_path)
                
                if os.name == 'posix' and (file_stat.st_mode & 0o077):
                    logger.critical(f"🔐 নিরাপত্তা ঝুঁকি: {config_path} অন্যদের জন্য অ্যাক্সেসযোগ্য!")
                    logger.info(f"ঠিক করুন: chmod 600 {config_path}")
                    return config
                
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                
                logger.info(f"✅ কনফিগারেশন লোড সফল: {config_path}")
                config = ConfigManager._merge_configs(config, user_config)
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ কনফিগ JSON ডিকোড ত্রুটি: {e}")
            except Exception as e:
                logger.error(f"❌ কনফিগ লোডিং ত্রুটি: {e}")
        else:
            logger.warning(f"⚠️ কনফিগ ফাইল পাওয়া যায়নি: {config_path}")
        
        # ২. পরিবেশ ভেরিয়েবল থেকে সংবেদনশীল ডেটা লোড করুন
        config = ConfigManager._load_credentials_from_env(config)
        
        return config
    
    @staticmethod
    def _load_credentials_from_env(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        পরিবেশ ভেরিয়েবল থেকে সংবেদনশীল শংসাপত্র লোড করুন
        
        পরিবেশ ভেরিয়েবল নাম অনুসরণ করে:
        - EXNESS_ACCOUNT_NUMBER
        - EXNESS_PASSWORD
        - NEWSAPI_KEY
        - SLACK_WEBHOOK_URL
        - TELEGRAM_BOT_TOKEN
        - GOCHARTING_TOKEN
        - ইত্যাদি
        
        Args:
            config: বর্তমান কনফিগ
            
        Returns:
            আপডেট করা কনফিগ
        """
        logger.info("🔐 পরিবেশ ভেরিয়েবল থেকে শংসাপত্র লোড করছি...")
        
        # Exness অ্যাকাউন্ট
        if os.getenv("EXNESS_ACCOUNT_NUMBER"):
            config["account"]["account_number"] = os.getenv("EXNESS_ACCOUNT_NUMBER")
        if os.getenv("EXNESS_PASSWORD"):
            config["account"]["password"] = os.getenv("EXNESS_PASSWORD")
        if os.getenv("EXNESS_SERVER"):
            config["account"]["server"] = os.getenv("EXNESS_SERVER")
        
        # সংবাদ API
        if os.getenv("NEWSAPI_KEY"):
            config["external_services"]["news_api"]["api_key"] = os.getenv("NEWSAPI_KEY")
        if os.getenv("ALPHAVANTAGE_KEY"):
            config["external_services"]["news_api"]["api_key"] = os.getenv("ALPHAVANTAGE_KEY")
        if os.getenv("FINNHUB_KEY"):
            config["external_services"]["news_api"]["api_key"] = os.getenv("FINNHUB_KEY")
        
        # Slack ওয়েবহুক
        if os.getenv("SLACK_WEBHOOK_URL"):
            config["external_services"]["notification"]["slack"]["webhook_url"] = os.getenv("SLACK_WEBHOOK_URL")
        
        # Telegram
        if os.getenv("TELEGRAM_BOT_TOKEN"):
            config["external_services"]["notification"]["telegram"]["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")
        if os.getenv("TELEGRAM_CHAT_ID"):
            config["external_services"]["notification"]["telegram"]["chat_id"] = os.getenv("TELEGRAM_CHAT_ID")
        
        # ইমেল
        if os.getenv("SMTP_USERNAME"):
            config["external_services"]["notification"]["email"]["username"] = os.getenv("SMTP_USERNAME")
        if os.getenv("SMTP_PASSWORD"):
            config["external_services"]["notification"]["email"]["password"] = os.getenv("SMTP_PASSWORD")
        
        # GoCharting
        if os.getenv("GOCHARTING_TOKEN"):
            config["external_services"]["webhooks"]["gocharting"]["api_token"] = os.getenv("GOCHARTING_TOKEN")
        if os.getenv("GOCHARTING_SECRET"):
            config["external_services"]["webhooks"]["gocharting"]["webhook_secret"] = os.getenv("GOCHARTING_SECRET")
        
        # TradingView
        if os.getenv("TRADINGVIEW_SECRET"):
            config["external_services"]["webhooks"]["tradingview"]["webhook_secret"] = os.getenv("TRADINGVIEW_SECRET")
        
        return config
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """
        সম্পূর্ণ কনফিগারেশন যাচাইকরণ (Exness + শংসাপত্র + এজেন্ট)
        
        Args:
            config: যাচাই করার কনফিগ
            
        Returns:
            সত্য যদি বৈধ, মিথ্যা অন্যথায়
        """
        logger.info("🔍 কনফিগারেশন যাচাইকরণ শুরু...")
        
        # ===== Exness অ্যাকাউন্ট সেটিংস যাচাইকরণ =====
        account_config = config.get("account", {})
        
        required_account_keys = ["account_number", "password", "server"]
        for key in required_account_keys:
            if key not in account_config or not account_config[key]:
                logger.error(f"❌ প্রয়োজনীয় অ্যাকাউন্ট কী নেই: {key}")
                return False
        
        # ===== MT5 কনফিগারেশন যাচাইকরণ =====
        mt5_config = config.get("mt5", {})
        if mt5_config.get("magic_number", 0) <= 0:
            logger.error("❌ MT5 magic_number অবশ্যই > 0 হতে হবে")
            return False
        
        # ===== ট্রেডিং কনফিগারেশন যাচাইকরণ =====
        trading_config = config.get("trading", {})
        
        try:
            balance = float(trading_config.get("account_balance", 10000))
            if balance <= 0:
                logger.error("❌ account_balance অবশ্যই > 0 হতে হবে")
                return False
            
            risk = float(trading_config.get("risk_percentage", 1.0))
            if not 0 < risk <= 10:
                logger.error("❌ risk_percentage 0-10% এর মধ্যে হতে হবে")
                return False
            
            logger.info("✅ কনফিগারেশন যাচাইকরণ সফল")
            return True
            
        except (ValueError, TypeError) as e:
            logger.error(f"❌ কনফিগ মূল্য ত্রুটি: {e}")
            return False
    
    @staticmethod
    def get_credential_safe(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
        """
        শংসাপত্র নিরাপদে পান এব��� লগে মাস্ক করুন
        
        Args:
            config: কনফিগ ডিকশনারি
            key_path: ডট-পৃথক পাথ (যেমন "external_services.slack.webhook_url")
            default: ডিফল্ট মান
            
        Returns:
            শংসাপত্র মান বা ডিফল্ট
        """
        keys = key_path.split(".")
        value = config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        
        return value if value is not None else default
    
    @staticmethod
    def log_config_safe(config: Dict[str, Any]) -> None:
        """
        শংসাপত্র মাস্ক করে নিরাপদে কনফিগ লগ করুন
        
        Args:
            config: কনফিগ ডিকশনারি
        """
        logger.info("📋 সক্রিয় কনফিগারেশন:")
        
        safe_config = ConfigManager._redact_config(config)
        for section, values in safe_config.items():
            if isinstance(values, dict):
                logger.info(f"   [{section}]")
                for key, value in values.items():
                    if isinstance(value, dict):
                        logger.info(f"      {key}:")
                        for subkey, subvalue in value.items():
                            logger.info(f"         {subkey}: {subvalue}")
                    else:
                        logger.info(f"      {key}: {value}")
    
    @staticmethod
    def _redact_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """কনফিগে সংবেদনশীল ক্ষেত্র রিডেক্ট করুন"""
        redacted = {}
        
        for key, value in config.items():
            if isinstance(value, dict):
                redacted[key] = ConfigManager._redact_config(value)
            elif key in CredentialsManager.SENSITIVE_FIELDS and value:
                redacted[key] = CredentialsManager.mask_credential(str(value))
            else:
                redacted[key] = value
        
        return redacted
    
    @staticmethod
    def _merge_configs(defaults: Dict[str, Any], 
                       user_config: Dict[str, Any]) -> Dict[str, Any]:
        """ডিফল্ট এবং ব্যবহারকারী কনফিগ মার্জ করুন"""
        result = {}
        
        for key, value in defaults.items():
            if isinstance(value, dict):
                result[key] = value.copy()
            else:
                result[key] = value
        
        for key, value in user_config.items():
            if isinstance(value, dict) and key in result:
                result[key].update(value)
            else:
                result[key] = value
        
        return result
    
    # Helper Methods
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
    def get_agents_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """এজেন্ট নির্দিষ্ট কনফিগ আনুন"""
        return config.get("agents", ConfigManager.DEFAULTS["agents"])
    
    @staticmethod
    def get_external_services_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """এক্সটার্নাল সার্ভিস কনফিগ আনুন"""
        return config.get("external_services", ConfigManager.DEFAULTS["external_services"])
    
    @staticmethod
    def get_exness_server(is_demo: bool = True, server_index: int = 0) -> str:
        """Exness MT5 সার্ভার পান"""
        server_type = "demo" if is_demo else "live"
        servers = ExnessConfig.EXNESS_SERVERS.get(server_type, [])
        
        if not servers:
            logger.warning(f"⚠️ {server_type} সার্ভার পাওয়া যায়নি")
            return "ExnessMT5Demo1"
        
        return servers[min(server_index, len(servers) - 1)]
    
    @staticmethod
    def get_symbol_config(symbol: str) -> Optional[Dict[str, Any]]:
        """সিম্বলের জন্য Exness নির্দিষ্ট কনফিগ পান"""
        return ExnessConfig.TRADING_SYMBOLS.get(symbol.upper(), None)
    
    @staticmethod
    def get_sl_distance(symbol: str, default: float = 1.0) -> float:
        """সিম্বলের জন্য স্টপ লস ডিস্ট্যান্স পান"""
        symbol_config = ConfigManager.get_symbol_config(symbol)
        if symbol_config:
            return symbol_config.get("sl_distance", default)
        return default
    
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
                "check_interval": 60,
                "magic_number": MTConfigDefaults.MT5_EXECUTION["magic_number"],
                "deviation": MTConfigDefaults.MT5_EXECUTION["deviation"]
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
            },
            "agents": {
                "SentimentAgent": {
                    "enabled": True,
                    "news_api_key": "YOUR_NEWSAPI_KEY"
                }
            },
            "external_services": {
                "news_api": {
                    "provider": "newsapi",
                    "enabled": False,
                    "api_key": "YOUR_NEWSAPI_KEY"
                },
                "notification": {
                    "slack": {
                        "enabled": False,
                        "webhook_url": "YOUR_SLACK_WEBHOOK_URL"
                    },
                    "telegram": {
                        "enabled": False,
                        "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
                        "chat_id": "YOUR_CHAT_ID"
                    }
                },
                "webhooks": {
                    "gocharting": {
                        "enabled": False,
                        "api_token": "YOUR_GOCHARTING_TOKEN",
                        "webhook_secret": "YOUR_WEBHOOK_SECRET"
                    }
                }
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
    
    @staticmethod
    def create_env_template() -> str:
        """
        .env ফাইলের জন্য টেমপ্লেট তৈরি করুন
        
        Returns:
            .env টেমপ্লেট সামগ্র��
        """
        template = """
# ===== Exness MT5 Credentials =====
EXNESS_ACCOUNT_NUMBER=your_account_number
EXNESS_PASSWORD=your_password
EXNESS_SERVER=ExnessMT5Demo1

# ===== News & Sentiment APIs =====
NEWSAPI_KEY=your_newsapi_key
ALPHAVANTAGE_KEY=your_alphavantage_key
FINNHUB_KEY=your_finnhub_key

# ===== Slack Notifications =====
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# ===== Telegram Notifications =====
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# ===== Email Notifications =====
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# ===== GoCharting Webhook =====
GOCHARTING_TOKEN=your_gocharting_token
GOCHARTING_SECRET=your_webhook_secret

# ===== TradingView Webhook =====
TRADINGVIEW_SECRET=your_tradingview_secret

# ===== Logging =====
LOG_LEVEL=INFO
MASK_CREDENTIALS=true
"""
        return template
