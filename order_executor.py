import logging
import MetaTrader5 as mt5

logger = logging.getLogger("TradeExecutor")

class TradeExecutor:
    def __init__(self, deviation: int = 15):
        self.deviation = deviation
        self.magic_number = 202699
        self.active_trades = {}

    def execute_live_deal(self, symbol: str, order_type: str, volume: float, sl_points: float = 70.0, tp_points: float = 30.0) -> dict:
        symbol = symbol.upper().strip()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"status": "failed"}

        price = tick.ask if order_type.upper() == "BUY" else tick.bid
        action = mt5.ORDER_TYPE_BUY if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL
        
        sl = price - sl_points if order_type.upper() == "BUY" else price + sl_points
        tp = price + tp_points if order_type.upper() == "BUY" else price - tp_points

        trade_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": action,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": self.deviation,
            "magic": self.magic_number,
            "comment": "Exness Live Order",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        result = mt5.order_send(trade_request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"status": "failed", "code": result.retcode}
        
        self.active_trades[str(result.order)] = {
            "entry_price": price, "stop_loss": sl, "tp1": price + (tp_points*0.5) if order_type=="BUY" else price - (tp_points*0.5),
            "current_lot": volume, "direction": order_type.upper(), "status": "OPEN", "tp1_hit": False
        }
        return {"status": "success", "ticket": result.order, "entry_price": result.price}

    def process_market_update(self, trade_id: str, current_price: float) -> list:
        logs = []
        if trade_id not in self.active_trades: return ["ট্রেডটি খুঁজে পাওয়া যায়নি"]
        t = self.active_trades[trade_id]
        if t["status"] == "CLOSED": return ["ট্রেডটি অলরেডি ক্লোজড হয়ে গেছে"]

        if not t["tp1_hit"]:
            if (t["direction"] == "BUY" and current_price >= t["tp1"]) or (t["direction"] == "SELL" and current_price <= t["tp1"]):
                t["tp1_hit"] = True
                t["stop_loss"] = t["entry_price"]
                t["current_lot"] = round(t["current_lot"] * 0.5, 2)
                logs.append(f"TP1 হিট! ৫০% প্রফিট বুকড। স্টপ লস ব্রেক-ইভেনে আনা হয়েছে।")

        if (t["direction"] == "BUY" and current_price <= t["stop_loss"]) or (t["direction"] == "SELL" and current_price >= t["stop_loss"]):
            t["status"] = "CLOSED"
            logs.append(f"ট্রেড ক্লোজড! কারেন্ট প্রাইস: {current_price}")
        return logs
