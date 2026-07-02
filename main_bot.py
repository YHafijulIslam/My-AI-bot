import os
import json
import time
import MetaTrader5 as mt5
import google.generativeai as genai
from common import logger, VoteDirection, AgentVote
from order_flow import TechnicalAgent
from lstm_model import PredictiveAgent
from liquidity_sweep import LiquiditySweepVoter
from ai_judge import SentimentAgent
from risk_manager import RiskManager
from trade_executor import TradeExecutor
from metrics import VotingMetrics

# ক্লাউড এআই (Gemini) কনফিগারেশন
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY"))

class VotingOrchestrator:
    def __init__(self, config_path="exness_config.json"):
        self.config_path = config_path
        self.load_config()
        self.risk_manager = RiskManager()
        self.trade_executor = TradeExecutor()
        self.metrics = VotingMetrics()
        
        # আপনার ফোল্ডারের আসল ৪টি এজেন্ট ইনিশিয়েলাইজেশন
        self.agents = {
            "technical": TechnicalAgent(candle_provider=self.fetch_live_market_data),
            "predictive": PredictiveAgent(candle_provider=self.fetch_live_market_data),
            "liquidity": LiquiditySweepVoter(candle_provider=self.fetch_live_market_data),
            "sentiment": SentimentAgent(news_provider=self.fetch_cloud_ai_sentiment)
        }
        
    def load_config(self):
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
            
    def connect_exness(self):
        """মেটাট্রেডার ৫ এর মাধ্যমে এক্সনেস লাইভ অ্যাকাউন্টে কানেক্ট করা"""
        if not mt5.initialize(path=self.config["paths"]["terminal_path"]):
            logger.error("MetaTrader5 initialization failed")
            return False
        login = int(self.config.get("exness_login"))
        password = self.config.get("exness_password")
        server = self.config.get("exness_server")
        if mt5.login(login=login, password=password, server=server):
            logger.info(f"Connected to Exness Server: {server}")
            return True
        logger.error(f"Exness authentication failed: {mt5.last_error()}")
        return False

    def fetch_live_market_data(self, symbol, lookback=100):
        """এক্সনেস MT5 থেকে সরাসরি রিয়েল-টাইম ক্যান্ডেল ডাটা নিয়ে লিস্ট আকারে রিটার্ন করা"""
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, lookback)
        if rates is None or len(rates) == 0:
            return []
        return [{"open": float(r['open']), "high": float(r['high']), "low": float(r['low']), "close": float(r['close']), "volume": float(r['tick_volume'])} for r in rates]

    def fetch_cloud_ai_sentiment(self, symbol, lookback=20):
        """Gemini Cloud AI ব্যবহার করে রিয়েল-টাইম মার্কেট নিউজ ও সেন্টিমেন্ট অ্যানালাইসিস"""
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"Analyze global news for {symbol}. Return JSON only: {{\"sentiment\": \"0.5\"}} range -1.0 to 1.0."
            response = model.generate_content(prompt)
            return json.loads(response.text.strip()) if response else {"sentiment": 0.0}
        except:
            return {"sentiment": 0.0}

    def run_voting_cycle(self, symbol):
        """পুরো ভোটিং ENGINE রিয়েল ডাটা দিয়ে রান করার মেইন লুপ"""
        if not self.connect_exness(): return
        votes_list, votes_dict = [], {}
        
        for name, agent in self.agents.items():
            try:
                vote_result = agent.vote(symbol)
                votes_list.append(vote_result)
                votes_dict[name] = int(vote_result.vote)
            except Exception as e:
                votes_dict[name] = int(VoteDirection.NEUTRAL)
                
        self.metrics.record_votes(symbol, votes_list)
        action_counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
        for v in votes_dict.values():
            if v == int(VoteDirection.BULLISH): action_counts["BUY"] += 1
            elif v == int(VoteDirection.BEARISH): action_counts["SELL"] += 1
            else: action_counts["HOLD"] += 1
                
        final_decision = "HOLD"
        if action_counts["BUY"] >= 3: final_decision = "BUY"
        elif action_counts["SELL"] >= 3: final_decision = "SELL"
            
        self.metrics.record_decision(symbol, final_decision)
        logger.info(f"Decision: {final_decision}")
        
        if final_decision in ["BUY", "SELL"]:
            candles = self.fetch_live_market_data(symbol, lookback=2)
            if candles:
                current_price = candles[-1]["close"]
                # রিস্ক ক্যালকুলেশন এবং পজিশন সাইজিং
                sl_dist = 2.0 # গোল্ডের জন্য ২ ডলার বা ২০০ পিপ্স এসএল ডিস্ট্যান্স
                sl_price = current_price - sl_dist if final_decision == "BUY" else current_price + sl_dist
                risk_result = self.risk_manager.calculate_position(current_price, sl_price, symbol)
                
                if risk_result and risk_result.get("status") == "Success":
                    logger.info(f"Execution logic trigger for {final_decision} with lot: {risk_result['lot_size']}")
                    # এখানে লাইভ ট্রেড এক্সিকিউট করার জন্য রিকোয়েস্ট পাঠানো যাবে
        mt5.shutdown()

if __name__ == "__main__":
    orchestrator = VotingOrchestrator()
    while True:
        orchestrator.run_voting_cycle("XAUUSD")
        time.sleep(900) # প্রতি ১৫ মিনিট পর পর চেক করবে
