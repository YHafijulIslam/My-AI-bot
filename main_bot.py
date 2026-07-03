import time
import logging
from voting_orchestrator import VotingOrchestrator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    orchestrator = VotingOrchestrator()
    
    # গোল্ড এবং বিটকয়েন দুটোই রান করার জন্য মাল্টি-অ্যাসেট লিস্ট
    symbols_to_trade = ["XAUUSD", "BTCUSD"]
    
    while True:
        for symbol in symbols_to_trade:
            logger.info(f"🔄 Starting cycle from Main Bot for: {symbol}")
            try:
                orchestrator.run_voting_cycle(symbol)
            except Exception as e:
                logger.error(f"Error running cycle for {symbol}: {e}")
            time.sleep(5)  # দুই সিম্বলের মাঝে ৫ সেকেন্ডের সেফটি গ্যাপ
            
        logger.info("⏳ All symbols checked by Main Bot. Waiting 15 minutes...")
        time.sleep(900)  # প্রতি ১৫ মিনিট পর পর চক্রটি পুনরায় চলবে
