#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main_bot.py - AI ট্রেডিং বট এন্ট্রি পয়েন্ট
Multi-agent Trading System Entry Point with Enhanced Logging & Health Checks
"""
import time
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path

# কনফিগারেশন ম্যানেজার ইম্পোর্ট (যদি উপলব্ধ)
try:
    from config_manager import ConfigManager
    HAS_CONFIG_MANAGER = True
except ImportError:
    HAS_CONFIG_MANAGER = False
    ConfigManager = None

from voting_orchestrator import VotingOrchestrator

# ===== লগিং সেটআপ =====
def setup_logging(log_dir: str = "logs", log_level: str = "INFO") -> logging.Logger:
    """
    মাল্টি-লেভেল লগিং সেটআপ (কনসোল + ফাইল)
    
    Args:
        log_dir: লগ ফাইলের ডিরেক্টরি
        log_level: লগিং লেভেল (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        কনফিগার করা লগার
    """
    # লগ ডিরেক্টরি তৈরি করুন
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # রুট লগার কনফিগ করুন
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    
    # বিদ্যমান হ্যান্ডলার পরিষ্কার করুন
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # ফরম্যাট ডিফাইন করুন
    detailed_format = logging.Formatter(
        fmt='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ===== কনসোল হ্যান্ডলার (INFO+) =====
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_format)
    logger.addHandler(console_handler)
    
    # ===== ফাইল হ্যান্ডলার (DEBUG+, দৈনিক + রোটেশন) =====
    log_filename = os.path.join(
        log_dir, 
        f"bot_{datetime.now().strftime('%Y%m%d')}.log"
    )
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_filename,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_format)
    logger.addHandler(file_handler)
    
    # ===== এরর ফাইল হ্যান্ডলার (ERROR+) =====
    error_filename = os.path.join(
        log_dir,
        f"bot_errors_{datetime.now().strftime('%Y%m%d')}.log"
    )
    
    error_handler = logging.handlers.RotatingFileHandler(
        error_filename,
        maxBytes=10*1024*1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_format)
    logger.addHandler(error_handler)
    
    logger.info(f"✅ লগিং সিস্টেম ইনিশিয়ালাইজড")
    logger.info(f"   লগ লেভেল: {log_level}")
    logger.info(f"   লগ ডিরেক্টরি: {log_dir}")
    logger.info(f"   লগ ফাইল: {log_filename}")
    
    return logger


# ===== হেলথ চেক ফাংশন =====
def perform_startup_checks(config: dict = None) -> bool:
    """
    স্টার্টআপ হেলথ চেক পারফর্ম করুন
    
    Args:
        config: কনফিগারেশন ডিকশনারি (অপশনাল)
        
    Returns:
        সত্য যদি সব চেক পাস, মিথ্যা অন্যথায়
    """
    logger = logging.getLogger(__name__)
    logger.info("\n🔍 স্টার্টআপ হেলথ চেক শুরু...")
    
    all_passed = True
    
    # ১. কনফিগ যাচাইকরণ
    if config and HAS_CONFIG_MANAGER:
        logger.info("  ① কনফিগারেশন যাচাইকরণ...")
        if not ConfigManager.validate_config(config):
            logger.error("  ❌ কনফিগারেশন যাচাইকরণ ব্যর্থ")
            all_passed = False
        else:
            logger.info("  ✅ কনফিগারেশন বৈধ")
    else:
        logger.info("  ① কনফিগ ম্যানেজার উপলব্ধ নয় - স্কিপ করছি")
    
    # ২. প্রয়োজনীয় মডিউল চেক
    logger.info("  ② প্রয়োজনীয় মডিউল চেক...")
    
    required_modules = {
        'MetaTrader5': 'MT5',
        'numpy': 'NumPy',
        'pandas': 'Pandas (অপশনাল)'
    }
    
    for module_name, display_name in required_modules.items():
        try:
            __import__(module_name)
            logger.info(f"  ✅ {display_name} মডিউল উপলব্ধ")
        except ImportError:
            if module_name == 'pandas':  # অপশনাল
                logger.warning(f"  ⚠️ {display_name} মডিউল উপলব্ধ নয় (অপশনাল)")
            else:
                logger.error(f"  ❌ {display_name} মডিউল খুঁজে পাওয়া যায়নি - ইনস্টল করুন: pip install {module_name}")
                all_passed = False
    
    # ৩. লগ ডিরেক্টরি চেক
    logger.info("  ③ লগ ডিরেক্টরি চেক...")
    log_dir = "logs"
    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        if os.access(log_dir, os.W_OK):
            logger.info(f"  ✅ লগ ডিরেক্টরি লেখনযোগ্য: {log_dir}")
        else:
            logger.error(f"  ❌ লগ ডিরেক্টরিতে লেখার অনুমতি নেই: {log_dir}")
            all_passed = False
    except Exception as e:
        logger.error(f"  ❌ লগ ডিরেক্টরি তৈরিতে ত্রুটি: {e}")
        all_passed = False
    
    # ৪. ডিস্ক স্পেস চেক (অপশনাল)
    logger.info("  ④ ডিস্ক স্পেস চেক...")
    try:
        import shutil
        disk_usage = shutil.disk_usage("/")
        free_gb = disk_usage.free / (1024**3)
        if free_gb > 1:
            logger.info(f"  ✅ পর্যাপ্ত ডিস্ক স্পেস: {free_gb:.1f} GB")
        else:
            logger.warning(f"  ⚠️ কম ডিস্ক স্পেস: {free_gb:.1f} GB")
    except Exception as e:
        logger.warning(f"  ⚠️ ডিস্ক স্পেস চেক ত্রুটি: {e}")
    
    # ৫. কনফিগ ফাইল চেক
    logger.info("  ⑤ কনফিগ ফাইল চেক...")
    if os.path.exists("exness_config.json"):
        try:
            file_stat = os.stat("exness_config.json")
            if os.name == 'posix' and (file_stat.st_mode & 0o077):
                logger.critical("  🔐 নিরাপত্তা ঝুঁকি: exness_config.json অন্যদের জন্য অ্যাক্সেসযোগ্য!")
                logger.info("     ঠিক করুন: chmod 600 exness_config.json")
                all_passed = False
            else:
                logger.info("  ✅ কনফিগ ফাইল পাওয়া গেছে এবং সুরক্ষিত")
        except Exception as e:
            logger.error(f"  ❌ কনফিগ ফাইল চেক ত্রুটি: {e}")
    else:
        logger.warning("  ⚠️ exness_config.json পাওয়া যায়নি - ডেমো মোড ব্যবহার করছি")
    
    # সামারি
    if all_passed:
        logger.info("✅ সব কঠোর হেলথ চেক পাস হয়েছে\n")
    else:
        logger.warning("⚠️ কিছু হেলথ চেক ব্যর্থ হয়েছে - সতর্ক থাকুন\n")
    
    return all_passed


# ===== মেইন এন্ট্রি পয়েন্ট =====
def main():
    """মূল এক্সিকিউশন ফাংশন"""
    
    # লগিং সেটআপ করুন
    logger = setup_logging(log_dir="logs", log_level="INFO")
    
    logger.info("=" * 80)
    logger.info("🚀 AI ট্রেডিং বট স্টার্ট হচ্ছে...")
    logger.info(f"   সময়: {datetime.now().isoformat()}")
    logger.info(f"   পাইথন: {sys.version}")
    logger.info(f"   প্ল্যাটফর্ম: {sys.platform}")
    logger.info("=" * 80)
    
    orchestrator = None
    config = None
    
    try:
        # ===== কনফিগ লোড করুন (যদি পাওয়া যায়) =====
        if HAS_CONFIG_MANAGER:
            logger.info("\n📋 কনফিগারেশন লোড হচ্ছে...")
            try:
                config = ConfigManager.load_config("exness_config.json")
                if not ConfigManager.validate_config(config):
                    logger.warning("⚠️ কনফিগারেশন যাচাইকরণ ব্যর্থ - ডিফল্ট ব্যবহার করছি")
                    config = None
                else:
                    logger.info("✅ কনফিগারেশন লোড এবং যাচাই সফল")
            except Exception as e:
                logger.error(f"❌ কনফিগ লোডিং ত্রুটি: {e}")
                config = None
        else:
            logger.info("ℹ️ ConfigManager উপলব্ধ নয় - ডিফল্ট কনফিগ ব্যবহার করছি")
        
        # ===== হেলথ চেক পারফর্ম করুন =====
        health_check_passed = perform_startup_checks(config)
        
        if not health_check_passed:
            logger.warning("⚠️ কিছু হেলথ চেক ব্যর্থ হয়েছে - সতর্কতার সাথে এগিয়ে যাচ্ছি...")
        
        # ===== অর্কেস্ট্রেটর ইনিশিয়ালাইজ করুন =====
        logger.info("\n🤖 অর্কেস্ট্রেটর ইনিশিয়ালাইজ করছি...")
        
        if config:
            orchestrator = VotingOrchestrator(config=config)
        else:
            orchestrator = VotingOrchestrator()
        
        logger.info("✅ অর্কেস্ট্রেটর প্রস্তুত")
        
        # ===== ট্রেডিং সিম্বল =====
        if config and HAS_CONFIG_MANAGER:
            trading_config = ConfigManager.get_trading_config(config)
            symbols_to_trade = trading_config.get("symbols", ["XAUUSD", "BTCUSD"])
            cycle_interval = config.get("cycle", {}).get("interval_seconds", 900)
            symbol_delay = config.get("cycle", {}).get("symbol_delay_seconds", 5)
        else:
            symbols_to_trade = ["XAUUSD", "BTCUSD"]
            cycle_interval = 900  # 15 মিনিট
            symbol_delay = 5
        
        logger.info(f"\n📊 ট্রেডিং সিম্বল: {', '.join(symbols_to_trade)}")
        logger.info(f"   চক্র ইন্টারভাল: {cycle_interval}s ({cycle_interval/60:.0f} মিনিট)")
        logger.info(f"   সিম্বল বিলম্ব: {symbol_delay}s")
        
        # ===== মূল ট্রেডিং লুপ =====
        logger.info("\n🔄 মূল ট্রেডিং লুপ শুরু হচ্ছে...\n")
        
        cycle_count = 0
        error_count = 0
        max_consecutive_errors = 5
        
        while True:
            cycle_count += 1
            logger.info(f"\n{'='*80}")
            logger.info(f"🔁 চক্র #{cycle_count} - {datetime.now().isoformat()}")
            logger.info(f"{'='*80}")
            
            cycle_errors = 0
            
            for symbol in symbols_to_trade:
                logger.info(f"\n🔄 {symbol} এর জন্য চক্র শুরু করছি...")
                
                try:
                    orchestrator.run_voting_cycle(symbol)
                    logger.info(f"✅ {symbol} চক্র সম্পন্ন সফলভাবে")
                    error_count = 0  # রিসেট এরর কাউন্ট
                    
                except KeyboardInterrupt:
                    logger.info("\n🛑 ব্যবহারকারী ইন্টারাপ্ট (Ctrl+C)")
                    raise
                    
                except Exception as e:
                    logger.error(
                        f"❌ {symbol} চক্র এক্সিকিউশন ত্রুটি: {e}",
                        exc_info=True
                    )
                    cycle_errors += 1
                    error_count += 1
                    
                    # পরপর অনেক ত্রুটি হলে সতর্ক দিন
                    if error_count >= max_consecutive_errors:
                        logger.critical(
                            f"🚨 {max_consecutive_errors} টি পরপর ত্রুটি ঘটেছে - সমস্যা সমাধানের চেষ্টা করছি..."
                        )
                        time.sleep(10)  # দীর্ঘ বিলম্ব
                
                # সিম্বলের মধ্যে বিলম্ব
                if symbol != symbols_to_trade[-1]:  # শেষ সিম্বল নয় হলে
                    logger.info(f"⏳ পরবর্তী সিম্বলের জন্য {symbol_delay}s অপেক্ষা করছি...")
                    time.sleep(symbol_delay)
            
            # চক্র সামারি
            logger.info(f"\n✅ চক্র #{cycle_count} সম্পন্ন - {len(symbols_to_trade)} সিম্বল প্রক্রিয়া করা হয়েছে")
            
            if cycle_errors > 0:
                logger.warning(f"⚠️ এই চক্রে {cycle_errors} টি ত্রুটি ��টেছে")
            
            # চক্রের মধ্যে বিলম্ব (১৫ মিনিট)
            logger.info(f"\n⏳ পরবর্তী চক্রের জন্য {cycle_interval}s অপেক্ষা করছি ({cycle_interval/60:.0f} মিনিট)...")
            logger.info(f"   পরবর্তী চক্র সময়: {(datetime.now().timestamp() + cycle_interval)}")
            
            time.sleep(cycle_interval)
            
    except KeyboardInterrupt:
        logger.info("\n\n🛑 ব্যবহারকারী দ্বারা প্রোগ্রাম বন্ধ করা হয়েছে (Ctrl+C)")
        return 0
        
    except Exception as e:
        logger.error(
            f"\n\n❌ মূল লুপে অপ্রত্যাশিত ত্রুটি: {e}",
            exc_info=True
        )
        return 1
        
    finally:
        # গ্রেসফুল শাটডাউন
        logger.info("\n\n" + "="*80)
        logger.info("🛑 শাটডাউন শুরু হচ্ছে...")
        logger.info("="*80)
        
        if orchestrator:
            try:
                logger.info("🔌 অর্কেস্ট্রেটর শাটডাউন করছি...")
                orchestrator.shutdown()
                logger.info("✅ অর্কেস্ট্রেটর শাটডাউন সম্পন্ন")
            except Exception as e:
                logger.error(f"❌ অর্কেস্ট্রেটর শাটডাউন ত্রুটি: {e}", exc_info=True)
        
        logger.info("\n✅ প্রোগ্রাম সম্পন্ন")
        logger.info("=" * 80)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
