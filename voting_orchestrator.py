float(last_candle['close'] if isinstance(last_candle, dict) else getattr(last_candle, 'close', 0.0))
                
                # আপনার অনুরোধ অনুযায়ী বিটকয়েনের স্টপ লসও ২ ডলার করা হলো
                if "BTC" in symbol:
                    sl_dist = 2.0   # বিটকয়েনের জন্য ২ ডলার এসএল ডিস্ট্যান্স
                else:
                    sl_dist = 2.0   # গোল্ডের জন্য ২ ডলার এসএল ডিস্ট্যান্স
                    
                sl_price = current_price - sl_dist if final_decision == "BUY" else current_price + sl_dist
                risk_result = self.risk_manager.calculate_position(current_price, sl_price, symbol)
                
                if risk_result and risk_result.get("status") == "Success":
                    logger.info(f"🚀 Execution logic trigger for {symbol} ({final_decision}) with lot: {risk_result['lot_size']}")
                    self.trade_executor.execute_trade(final_decision, risk_result['lot_size'], sl_price, symbol)
                    
        mt5.shutdown()

if __name__ == "__main__":
    orchestrator = VotingOrchestrator()
    
    # গোল্ড এবং বিটকয়েন মাল্টি-অ্যাসেট লিস্ট
    symbols_to_trade = ["XAUUSD", "BTCUSD"]
    
    while True:
        for symbol in symbols_to_trade:
            logger.info(f"🔄 Processing automated cycle for: {symbol}")
            orchestrator.run_voting_cycle(symbol)
            time.sleep(5)  # দুই সিম্বলের মাঝে ৫ সেকেন্ডের সেফটি গ্যাপ
            
        logger.info("⏳ All symbols checked. Waiting for next cycle (15 minutes)...")
        time.sleep(900)  # প্রতি ১৫ মিনিট পর পর চক্রটি পুনরায় চলবে
