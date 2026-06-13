import sys
import time
import requests  
import MetaTrader5 as mt5
import pandas as pd
import pyqtgraph as pg
import numpy as np
from datetime import datetime, timedelta, time as dt_time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QDoubleSpinBox, QSpinBox, QGroupBox, 
                             QFrame, QComboBox, QCheckBox, QTabWidget, QSplitter, QGridLayout)
from PyQt5.QtCore import QThread, pyqtSignal, QRectF, Qt, QPointF
from PyQt5.QtGui import QColor, QBrush, QPen, QPainter, QPicture

# ==============================================================================
# 📡 TELEGRAM ENGINE (BACKGROUND THREAD)
# ==============================================================================
class TelegramEngine(QThread):
    cmd_signal = pyqtSignal(str)

    def __init__(self, token, chat_id, vps_name):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.vps_name = vps_name.lower().strip()
        self.is_running = False
        self.last_update_id = None

    def run(self):
        self.is_running = True
        self.send_msg(f"🟢 [{self.vps_name.upper()}] Systems Online & Connected!")
        
        while self.is_running:
            try:
                if not self.token or not self.chat_id:
                    time.sleep(5); continue
                    
                url = f"https://api.telegram.org/bot{self.token}/getUpdates"
                params = {"timeout": 5}
                if self.last_update_id:
                    params["offset"] = self.last_update_id + 1
                    
                res = requests.get(url, params=params, timeout=10).json()
                if res.get("ok"):
                    for item in res["result"]:
                        self.last_update_id = item["update_id"]
                        msg = item.get("message", {}).get("text", "").lower().strip()
                        
                        if msg == "/stop_all" or msg == f"/stop {self.vps_name}":
                            self.cmd_signal.emit("STOP")
                            self.send_msg(f"🛑 [{self.vps_name.upper()}] Trading Halted by Admin!")
                            
                        elif msg == "/start_all" or msg == f"/start {self.vps_name}":
                            self.cmd_signal.emit("START")
                            self.send_msg(f"🚀 [{self.vps_name.upper()}] Trading Resumed by Admin!")
                            
                        elif msg == "/status" or msg == f"/status {self.vps_name}":
                            self.cmd_signal.emit("STATUS")
            except Exception as e:
                pass
            time.sleep(1)
            
    def send_msg(self, text):
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(url, data={"chat_id": self.chat_id, "text": text}, timeout=5)
        except: pass

# ==============================================================================
# 🎨 1. CYBERPUNK CANDLESTICK CHART GRAPHICS SYSTEM
# ==============================================================================
class CandlestickItem(pg.GraphicsObject):
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data
        self.picture = None
        self.generatePicture()

    def generatePicture(self):
        self.picture = QPicture()
        p = QPainter(self.picture)
        w = (self.data[1][0] - self.data[0][0]) / 3.0 if len(self.data) > 1 else 0.5
        
        for (t, open, close, min_p, max_p) in self.data:
            p.setPen(pg.mkPen(color='#3b4f68', width=1))
            p.drawLine(QPointF(t, min_p), QPointF(t, max_p))
            
            if open > close:
                p.setBrush(pg.mkBrush('#ff3366')); p.setPen(pg.mkPen('#ff3366'))
            else:
                p.setBrush(pg.mkBrush('#00e5ff')); p.setPen(pg.mkPen('#00e5ff'))
                
            p.drawRect(QRectF(t-w, open, w*2, close-open))
        p.end()

    def paint(self, p, *args):
        if self.picture: self.picture.play(p)
    def boundingRect(self):
        return QRectF(self.picture.boundingRect()) if self.picture else QRectF()

# ==============================================================================
# 🧠 2. TRADING BOT ENGINE CORE (HYBRID SCALPING-GRID)
# ==============================================================================
class TradingBot(QThread):
    log_signal = pyqtSignal(str)
    chart_signal = pyqtSignal(list)
    info_signal = pyqtSignal(dict) 
    force_stop_signal = pyqtSignal()
    tel_alert_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.symbol = "XAUUSDm"        
        self.magic = 999111 
        self.timeframe = mt5.TIMEFRAME_M1 
        
        self.lot_size = 0.01          
        self.max_layers = 100 
        self.expansion_dist = 500 
        
        self.step_l1 = 100 
        self.step_l2 = 200 
        self.step_l3 = 400 
        
        self.sl_points = 99999          
        self.trigger_tp_per_001 = 0.30  
        
        self.rsi_period = 14
        self.rsi_buy_level = 50.0       
        self.rsi_sell_level = 50.0      
        self.bb_period = 20
        
        self.max_candle_size = 1000 
        self.auto_cleanup_enabled = True 
        self.max_cleanup_distance = 99999 
        self.equity_protection_pct = 30.0 
        
        self.use_time_filter = True 
        self.pause_start_time = dt_time(18, 30) 
        self.pause_end_time = dt_time(21, 30)   
        
        self.use_daily_close = True
        self.last_sleep_log = None              
        
        self.supa_url = ""
        self.supa_key = ""
        self.vps_name = "VPS_1"
        self.last_db_sync = 0

    # ------------------------------------------------------------------------
    # 🔒 MT5 ACCOUNT LICENSE VERIFICATION VIA SUPABASE
    # ------------------------------------------------------------------------
    def verify_license(self, account_id):
        if not self.supa_url or not self.supa_key:
            self.log_signal.emit("[SEC] ERROR: Supabase URL & API Key Missing!")
            self.log_signal.emit("[SEC] Please configure Cloud settings first.")
            return False
            
        endpoint = f"{self.supa_url}/rest/v1/mt5_licenses"
        params = {
            "account_number": f"eq.{account_id}",
            "is_active": "eq.true"
        }
        headers = {
            "apikey": self.supa_key,
            "Authorization": f"Bearer {self.supa_key}"
        }
        
        try:
            response = requests.get(endpoint, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if len(data) > 0:
                    client_name = data[0].get('client_name', 'Client')
                    self.log_signal.emit(f"[SEC] Welcome back, {client_name}!")
                    return True
            return False
        except Exception as e:
            self.log_signal.emit(f"[ERR] License Server Unreachable: {e}")
            return False 

    def get_fib_lot(self, count):
        multipliers = [1]*10 + [2, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
        if count <= len(multipliers):
            mult = multipliers[count - 1]
        else:
            a, b = multipliers[-2], multipliers[-1]
            for _ in range(len(multipliers), count):
                c = a + b; a = b; b = c
            mult = b
        return round(mult * self.lot_size, 2)

    def get_dynamic_grid_step(self, current_count):
        if current_count < 10:
            return self.step_l1 
        elif current_count < 15:
            return self.step_l2
        elif current_count < 20:
            return self.step_l3
        else:
            return self.expansion_dist

    def get_today_traded_lots(self):
        now = datetime.now()
        start_of_today = datetime(now.year, now.month, now.day, 0, 0, 0)
        deals = mt5.history_deals_get(start_of_today, now, group=f"*{self.symbol}*")
        total_lots = 0.0
        if deals:
            for d in deals:
                if d.magic == self.magic and d.entry == 0:  
                    total_lots += d.volume
        return round(total_lots, 2)

    def get_past_days_lots(self):
        now = datetime.now()
        start_date = datetime(now.year, now.month, now.day, 0, 0, 0) - timedelta(days=7)
        deals = mt5.history_deals_get(start_date, now, group=f"*{self.symbol}*")
        past_lots = {i: 0.0 for i in range(1, 8)} 
        if deals:
            for d in deals:
                if d.magic == self.magic and d.entry == 0:
                    deal_time = datetime.fromtimestamp(d.time)
                    days_diff = (now.date() - deal_time.date()).days
                    if 1 <= days_diff <= 7:
                        past_lots[days_diff] += d.volume
        return {k: round(v, 2) for k, v in past_lots.items()}

    def check_is_active_time(self, current_time):
        if not self.use_time_filter: return True
        if self.pause_start_time < self.pause_end_time:
            return not (self.pause_start_time <= current_time <= self.pause_end_time)
        return not (current_time >= self.pause_start_time or current_time <= self.pause_end_time)

    def sync_to_supabase(self, bal, eq, prof, total_pos, today_lots, time_status):
        if not self.supa_url or not self.supa_key or not self.vps_name:
            return
        
        endpoint = f"{self.supa_url}/rest/v1/bot_status"
        headers = {
            "apikey": self.supa_key,
            "Authorization": f"Bearer {self.supa_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        data = {
            "vps_name": self.vps_name,
            "status": time_status,
            "balance": bal,
            "equity": eq,
            "profit": prof,
            "total_pos": total_pos,
            "today_lots": today_lots,
            "last_updated": datetime.utcnow().isoformat()
        }
        try:
            requests.post(endpoint, headers=headers, json=data, timeout=3)
        except Exception:
            pass

    def run(self):
        if not mt5.initialize():
            self.log_signal.emit(f"[SYS] INITIALIZATION FAILED: {mt5.last_error()}")
            self.force_stop_signal.emit(); return
            
        acc = mt5.account_info()
        if acc is None:
            self.log_signal.emit("[SYS] ACCOUNT SYNC FAILED!")
            self.force_stop_signal.emit(); return

        self.log_signal.emit("[SEC] VALIDATING LICENSE PROTOCOL...")
        if not self.verify_license(acc.login):
            self.log_signal.emit(f"[SEC] ACCESS DENIED: Account ID ({acc.login}) Unauthorized.")
            self.force_stop_signal.emit(); return
            
        self.log_signal.emit(f"[SEC] ACCESS GRANTED: Protocol initialized.")
        
        orders = mt5.orders_get(symbol=self.symbol, magic=self.magic)
        if orders:
            for o in orders: mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket, "magic": self.magic})

        self.log_signal.emit(f"[AI] HYBRID SCALPING-GRID ONLINE. Awaiting confirmations...")
        self.last_sleep_log = None 
        self.last_db_sync = 0
        
        while self.is_running:
            try:
                acc = mt5.account_info()
                tick = mt5.symbol_info_tick(self.symbol)
                sym_info = mt5.symbol_info(self.symbol)
                
                if not (acc and tick and sym_info):
                    time.sleep(1); continue

                if self.equity_protection_pct > 0 and acc.balance > 0:
                    current_drawdown = ((acc.balance - acc.equity) / acc.balance) * 100
                    if current_drawdown >= self.equity_protection_pct:
                        msg = f"🚨 EQUITY BREACH DETECTED ({current_drawdown:.2f}%). EXECUTING EMERGENCY CUT LOSS!"
                        self.log_signal.emit(f"[WARN] {msg}")
                        self.tel_alert_signal.emit(msg)
                        self.close_all_positions_and_orders(comment="Eq_Protect_Close")
                        self.is_running = False
                        self.force_stop_signal.emit() 
                        break

                all_positions = mt5.positions_get(symbol=self.symbol, magic=self.magic)
                buy_count = sum(1 for p in all_positions if p.type == mt5.ORDER_TYPE_BUY) if all_positions else 0
                buy_lots = sum(p.volume for p in all_positions if p.type == mt5.ORDER_TYPE_BUY) if all_positions else 0.0
                sell_count = sum(1 for p in all_positions if p.type == mt5.ORDER_TYPE_SELL) if all_positions else 0
                sell_lots = sum(p.volume for p in all_positions if p.type == mt5.ORDER_TYPE_SELL) if all_positions else 0.0
                
                total_pos_count = len(all_positions) if all_positions else 0
                today_traded_lots = self.get_today_traded_lots() 
                past_days_lots = self.get_past_days_lots() 

                now = datetime.now()
                current_time = now.time()
                weekday = now.weekday() 
                
                daily_state = "ACTIVE"
                if self.use_daily_close:
                    if weekday == 5 and current_time >= dt_time(3, 50): daily_state = "FORCE_CLOSE_SLEEP" 
                    elif weekday == 6: daily_state = "FORCE_CLOSE_SLEEP" 
                    elif weekday == 0 and current_time < dt_time(5, 20): daily_state = "FORCE_CLOSE_SLEEP" 
                    elif dt_time(3, 40) <= current_time < dt_time(3, 50): daily_state = "WAITING_CLOSE"     
                    elif dt_time(3, 50) <= current_time < dt_time(5, 20): daily_state = "FORCE_CLOSE_SLEEP" 

                is_active_time = False
                if daily_state == "FORCE_CLOSE_SLEEP":
                    if all_positions or (mt5.orders_get(symbol=self.symbol, magic=self.magic)):
                        self.close_all_positions_and_orders(comment="Daily_Force_Close")
                        self.log_signal.emit("[SYS] FORCED CLOSE INITIATED.")
                    time_status_msg = "OFFLINE: SYSTEM MAINTENANCE"
                elif daily_state == "WAITING_CLOSE":
                    time_status_msg = "STANDBY: AWAITING NATURAL CLOSE"
                else: 
                    daily_active = self.check_is_active_time(current_time)
                    if not self.use_time_filter: is_active_time = True; time_status_msg = "ONLINE: 24/7 OVERRIDE"
                    elif daily_active: is_active_time = True; time_status_msg = "ONLINE: HUNTING MODE"
                    else: is_active_time = False; time_status_msg = "STANDBY: NEWS PROTECTION"
                
                self.info_signal.emit({
                    "bal": acc.balance, "eq": acc.equity, "prof": acc.profit, "price": tick.ask, "total_pos": total_pos_count,
                    "buy_count": buy_count, "buy_lots": round(buy_lots, 2), "sell_count": sell_count, "sell_lots": round(sell_lots, 2),
                    "today_traded_lots": today_traded_lots, "past_lots": past_days_lots, "time_status": time_status_msg, "is_active_time": is_active_time
                })

                if time.time() - self.last_db_sync > 5:
                    self.sync_to_supabase(acc.balance, acc.equity, acc.profit, total_pos_count, today_traded_lots, time_status_msg)
                    self.last_db_sync = time.time()

                self.check_hybrid_take_profit(all_positions, tick)
                if self.auto_cleanup_enabled and all_positions: self.execute_smart_cleanup_logic(all_positions, tick, sym_info.point)

                df = self.get_market_data()
                if df is not None and len(df) >= max(20, self.rsi_period):
                    df['sma'] = df['close'].rolling(window=self.bb_period).mean()
                    df['std'] = df['close'].rolling(window=self.bb_period).std()
                    delta = df['close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
                    rs = gain / (loss + 1e-10)
                    df['rsi'] = 100 - (100 / (1 + rs))
                    df['rsi'].fillna(50, inplace=True)
                    
                    current_rsi = df['rsi'].iloc[-1]
                    current_open = df['open'].iloc[-1]
                    current_high = df['high'].iloc[-1]
                    current_low = df['low'].iloc[-1]
                    
                    candle_size_points = (current_high - current_low) / sym_info.point
                    is_bullish = tick.ask > current_open  
                    is_bearish = tick.bid < current_open  
                    
                    chart_data = [(i, r['open'], r['close'], r['low'], r['high']) for i, r in df.iterrows()]
                    self.chart_signal.emit(chart_data)

                    if is_active_time:
                        self.execute_hybrid_entry_logic(all_positions, tick, sym_info.point, current_rsi, candle_size_points, is_bullish, is_bearish)
                        if self.last_sleep_log == True: self.last_sleep_log = None
                    else:
                        if self.last_sleep_log is None and daily_state == "ACTIVE":
                            self.log_signal.emit("[AI] Market Volatility Filter Activated. Halting Operations.")
                            self.last_sleep_log = True

                time.sleep(0.5)
            except Exception as e:
                self.log_signal.emit(f"[ERR] Data Stream Interrupted: {str(e)}")
                time.sleep(3)
        mt5.shutdown()

    def close_all_positions_and_orders(self, comment="Force_Close"):
        orders = mt5.orders_get(symbol=self.symbol, magic=self.magic)
        if orders:
            for o in orders: mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket, "magic": self.magic})

        positions = mt5.positions_get(symbol=self.symbol, magic=self.magic)
        if positions:
            for p in positions:
                self.close_single_position(p, mt5.symbol_info_tick(self.symbol).bid if p.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(self.symbol).ask, comment)

    def close_single_position(self, p, price, comment):
        order_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        mt5.order_send({
            "action": mt5.TRADE_ACTION_DEAL, "symbol": self.symbol, "volume": p.volume,
            "type": order_type, "position": p.ticket, "price": price,
            "magic": self.magic, "comment": comment, 
            "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC
        })

    def get_market_data(self):
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, 100)
        if rates is None or len(rates) == 0: return None
        return pd.DataFrame(rates)

    def check_hybrid_take_profit(self, positions, tick):
        if not positions: return
        
        buy_positions = sorted([p for p in positions if p.type == mt5.ORDER_TYPE_BUY], key=lambda x: x.ticket)
        sell_positions = sorted([p for p in positions if p.type == mt5.ORDER_TYPE_SELL], key=lambda x: x.ticket)

        if buy_positions:
            basket_closed = False
            if len(buy_positions) >= 8:
                basket = [buy_positions[0]] + buy_positions[7:min(len(buy_positions), 10)]
                total_profit = sum(p.profit for p in basket)
                target_profit = (sum(p.volume for p in basket) / 0.01) * self.trigger_tp_per_001
                
                if total_profit >= target_profit and total_profit > 0:
                    for p in basket:
                        self.close_single_position(p, tick.bid, "Rescue_Basket_L1_BUY")
                    self.log_signal.emit(f"[PROFIT] Layer 1 Rescue Basket (Long) Secured: ${total_profit:.2f}")
                    basket_closed = True

            for i, p in enumerate(buy_positions):
                if basket_closed and (i == 0 or (7 <= i <= 9)):
                    continue
                
                target_profit = (p.volume / 0.01) * self.trigger_tp_per_001
                if p.profit >= target_profit:
                    self.close_single_position(p, tick.bid, f"Indie_TP_BUY_Pos{i+1}")
                    self.log_signal.emit(f"[PROFIT] Micro Long Node (Pos {i+1}) Secured: ${p.profit:.2f}")

        if sell_positions:
            basket_closed = False
            if len(sell_positions) >= 8:
                basket = [sell_positions[0]] + sell_positions[7:min(len(sell_positions), 10)]
                total_profit = sum(p.profit for p in basket)
                target_profit = (sum(p.volume for p in basket) / 0.01) * self.trigger_tp_per_001
                
                if total_profit >= target_profit and total_profit > 0:
                    for p in basket:
                        self.close_single_position(p, tick.ask, "Rescue_Basket_L1_SELL")
                    self.log_signal.emit(f"[PROFIT] Layer 1 Rescue Basket (Short) Secured: ${total_profit:.2f}")
                    basket_closed = True

            for i, p in enumerate(sell_positions):
                if basket_closed and (i == 0 or (7 <= i <= 9)):
                    continue
                
                target_profit = (p.volume / 0.01) * self.trigger_tp_per_001
                if p.profit >= target_profit:
                    self.close_single_position(p, tick.ask, f"Indie_TP_SELL_Pos{i+1}")
                    self.log_signal.emit(f"[PROFIT] Micro Short Node (Pos {i+1}) Secured: ${p.profit:.2f}")

    def execute_smart_cleanup_logic(self, positions, tick, point):
        for p in positions:
            if abs(tick.ask - p.price_open) / point >= self.max_cleanup_distance:
                self.close_single_position(p, tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask, "Cleanup")
                self.log_signal.emit(f"[CLEANUP] Pruned distant node: Ticket {p.ticket}")

    def execute_hybrid_entry_logic(self, positions, tick, point, current_rsi, candle_size, is_bullish, is_bearish):
        active_buys = [p for p in positions if p.type == mt5.ORDER_TYPE_BUY] if positions else []
        active_sells = [p for p in positions if p.type == mt5.ORDER_TYPE_SELL] if positions else []
        is_crashing = candle_size > self.max_candle_size

        if is_crashing: return

        if not active_buys:
            if current_rsi <= self.rsi_buy_level and is_bullish:
                self.place_market_deal(mt5.ORDER_TYPE_BUY, tick.ask, 1, point)
                self.log_signal.emit(f"[EXEC] Layer 1 Long Initiated (RSI: {current_rsi:.1f}).")
                self.last_sleep_log = None
        elif len(active_buys) < self.max_layers:
            current_required_step = self.get_dynamic_grid_step(len(active_buys))
            if tick.ask <= min([p.price_open for p in active_buys]) - (current_required_step * point):
                if is_bullish: 
                    self.place_market_deal(mt5.ORDER_TYPE_BUY, tick.ask, len(active_buys) + 1, point)
                    self.log_signal.emit(f"[EXEC] Grid Long Pos {len(active_buys)+1} Added (Step: {current_required_step} Pts)")
                    self.last_sleep_log = None
                else:
                    if self.last_sleep_log != f"wait_buy_{len(active_buys)}":
                        self.log_signal.emit(f"[AI] Target distance {current_required_step} Pts reached. Waiting for Bullish Reversal...")
                        self.last_sleep_log = f"wait_buy_{len(active_buys)}"

        if not active_sells:
            if current_rsi >= self.rsi_sell_level and is_bearish:
                self.place_market_deal(mt5.ORDER_TYPE_SELL, tick.bid, 1, point)
                self.log_signal.emit(f"[EXEC] Layer 1 Short Initiated (RSI: {current_rsi:.1f}).")
                self.last_sleep_log = None
        elif len(active_sells) < self.max_layers:
            current_required_step = self.get_dynamic_grid_step(len(active_sells))
            if tick.bid >= max([p.price_open for p in active_sells]) + (current_required_step * point):
                if is_bearish: 
                    self.place_market_deal(mt5.ORDER_TYPE_SELL, tick.bid, len(active_sells) + 1, point)
                    self.log_signal.emit(f"[EXEC] Grid Short Pos {len(active_sells)+1} Added (Step: {current_required_step} Pts)")
                    self.last_sleep_log = None
                else:
                    if self.last_sleep_log != f"wait_sell_{len(active_sells)}":
                        self.log_signal.emit(f"[AI] Target distance {current_required_step} Pts reached. Waiting for Bearish Reversal...")
                        self.last_sleep_log = f"wait_sell_{len(active_sells)}"

    def place_market_deal(self, type, price, count, point):
        target_lot = self.get_fib_lot(count)
        sl = price - (self.sl_points * point) if type == mt5.ORDER_TYPE_BUY else price + (self.sl_points * point)
        mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": self.symbol, "volume": float(target_lot), "type": type, "price": price, "sl": sl, "magic": self.magic, "comment": f"Pos_{count}", "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC})

# ==============================================================================
# 💎 3. CONTROL CENTER USER INTERFACE (CYBERPUNK THEME)
# ==============================================================================
class HybridHunterGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ HYBRID HUNTER | PRO TERMINAL")
        self.setGeometry(100, 100, 1400, 850)
        
        self.setStyleSheet("""
            QMainWindow { background-color: #060a0f; color: #a0b2c6; font-family: 'Segoe UI', sans-serif;}
            QFrame#Sidebar { background-color: #0b1118; border-right: 1px solid #1a2639; }
            
            QTabWidget::pane { border: 1px solid #00e5ff; background-color: #0b1118; border-radius: 8px; margin-top: -1px; }
            QTabBar::tab { background-color: #141f2d; color: #5a718c; padding: 10px 20px; font-weight: bold; border: 1px solid #1a2639; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #00e5ff; color: #000000; border: 1px solid #00e5ff; }
            
            QLabel { color: #a0b2c6; font-weight: bold; }
            QLabel.YellowTitle { color: #00e5ff; font-weight: 900; font-size: 14px; text-transform: uppercase; margin-top: 15px; margin-bottom: 5px; letter-spacing: 1px;}
            QLabel[theme="value"] { color: #00ffa3; font-weight: bold; font-size: 18px; }
            
            QLabel#BuyText { color: #00e5ff; font-weight: bold; font-size: 15px; }
            QLabel#SellText { color: #ff3366; font-weight: bold; font-size: 15px; }
            
            QLineEdit, QSpinBox, QDoubleSpinBox { background-color: #060a0f; color: #00ffa3; border: 1px solid #1a2639; padding: 8px; border-radius: 4px; font-weight: bold; font-size: 14px;}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #00e5ff; }
            
            QCheckBox { color: #00e5ff; font-weight: bold; }
            QCheckBox::indicator { width: 16px; height: 16px; background-color: #060a0f; border: 1px solid #00e5ff; border-radius: 3px; }
            QCheckBox::indicator:checked { background-color: #00ffa3; border: 1px solid #00ffa3; }
            
            QPushButton#BtnStart { background-color: transparent; border: 2px solid #00ffa3; color: #00ffa3; padding: 15px; font-size: 14px; font-weight: 900; border-radius: 6px; text-transform: uppercase; letter-spacing: 1px; }
            QPushButton#BtnStart:hover { background-color: rgba(0, 255, 163, 0.1); }
            QPushButton#BtnStart:checked { background-color: #ff3366; border: 2px solid #ff3366; color: white; }
            
            QPushButton#BtnCleanup { background-color: transparent; border: 1px solid #ffaa00; color: #ffaa00; padding: 10px; font-size: 12px; font-weight: bold; border-radius: 4px; margin-top: 10px; }
            QPushButton#BtnCleanup:checked { background-color: #00ffa3; border: 1px solid #00ffa3; color: #000000; }
        """)
        
        self.bot = TradingBot()
        self.bot.log_signal.connect(self.log_msg)
        self.bot.chart_signal.connect(self.update_chart)
        self.bot.info_signal.connect(self.update_dash)
        self.bot.force_stop_signal.connect(self.handle_force_stop)
        self.bot.tel_alert_signal.connect(self.send_telegram_alert)
        self.initUI()

    def initUI(self):
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget); main_layout.setContentsMargins(0, 0, 0, 0)
        
        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(380)
        side_layout = QVBoxLayout(sidebar)
        
        lbl_logo = QLabel("⚡ HYBRID SYSTEM CORE")
        lbl_logo.setStyleSheet("font-size: 20px; font-weight: 900; color: #00e5ff; padding-bottom: 10px; letter-spacing: 2px;")
        side_layout.addWidget(lbl_logo)
        
        self.tabs = QTabWidget()
        
        # --- TAB 1: TERMINAL ---
        tab_general = QWidget(); l_general = QVBoxLayout(tab_general)
        lbl_entry = QLabel("❖ INITIALIZATION PROTOCOL"); lbl_entry.setClassName("YellowTitle")
        l_general.addWidget(lbl_entry)
        
        self.inp_sym = QLineEdit("XAUUSDm")
        self.inp_lot = QDoubleSpinBox(); self.inp_lot.setDecimals(2); self.inp_lot.setSingleStep(0.01); self.inp_lot.setValue(0.01)
        
        l_general.addWidget(QLabel("Target Asset (Symbol)")); l_general.addWidget(self.inp_sym)
        l_general.addWidget(QLabel("Base Inject Lot")); l_general.addWidget(self.inp_lot)

        lbl_layers = QLabel("❖ 3-LAYER GRID SETTINGS (Points)"); lbl_layers.setClassName("YellowTitle")
        l_general.addWidget(lbl_layers)

        self.inp_l1_dist = QSpinBox(); self.inp_l1_dist.setMaximum(50000); self.inp_l1_dist.setValue(100)
        self.inp_l2_dist = QSpinBox(); self.inp_l2_dist.setMaximum(50000); self.inp_l2_dist.setValue(200)
        self.inp_l3_dist = QSpinBox(); self.inp_l3_dist.setMaximum(50000); self.inp_l3_dist.setValue(400)
        
        l_general.addWidget(QLabel("Layer 1 (Pos 1-10) Step:")); l_general.addWidget(self.inp_l1_dist)
        l_general.addWidget(QLabel("Layer 2 (Pos 11-15) Step:")); l_general.addWidget(self.inp_l2_dist)
        l_general.addWidget(QLabel("Layer 3 (Pos 16-20) Step:")); l_general.addWidget(self.inp_l3_dist)

        self.btn_update_layers = QPushButton("UPDATE LAYER SETTINGS")
        self.btn_update_layers.setStyleSheet("background-color: transparent; border: 1px solid #ffaa00; color: #ffaa00; padding: 8px; font-weight: bold; border-radius: 4px; margin-top: 5px;")
        self.btn_update_layers.clicked.connect(self.update_layer_settings)
        l_general.addWidget(self.btn_update_layers)

        self.chk_time_filter = QCheckBox("MODULE: Auto-Sleep\n(06:30 PM - 09:30 PM)")
        self.chk_time_filter.setChecked(True) 
        self.chk_time_filter.setStyleSheet("margin-top: 15px;")
        
        self.chk_daily_close = QCheckBox("MODULE: Daily Reset\n(Stop 03:40 | Close 03:50)")
        self.chk_daily_close.setChecked(True)
        self.chk_daily_close.setStyleSheet("color: #ffaa00; margin-top: 5px;")
        
        lbl_eq_protect = QLabel("❖ ACCOUNT SAFEGUARD"); lbl_eq_protect.setClassName("YellowTitle")
        self.inp_equity_protect = QDoubleSpinBox(); self.inp_equity_protect.setRange(0.0, 100.0)
        self.inp_equity_protect.setValue(30.0)
        self.inp_equity_protect.setSuffix(" %")
        
        l_general.addWidget(self.chk_time_filter) 
        l_general.addWidget(self.chk_daily_close)
        l_general.addWidget(lbl_eq_protect)
        l_general.addWidget(QLabel("Max Drawdown Auto-Cut (%)"))
        l_general.addWidget(self.inp_equity_protect)
        
        l_general.addStretch()
        self.tabs.addTab(tab_general, "Terminal")
        
        # --- TAB 2: ENGINE (STRATEGY) ---
        tab_strategy = QWidget(); l_strategy = QVBoxLayout(tab_strategy)
        lbl_anticrash = QLabel("❖ ANTI-CRASH OVERRIDE"); lbl_anticrash.setClassName("YellowTitle")
        l_strategy.addWidget(lbl_anticrash)
        
        self.inp_max_candle = QSpinBox(); self.inp_max_candle.setRange(10, 10000); self.inp_max_candle.setValue(1000)
        l_strategy.addWidget(QLabel("Volatility Threshold (Points to Halt)"))
        l_strategy.addWidget(self.inp_max_candle)
        
        lbl_signal_title = QLabel("❖ SNIPER SENSORS"); lbl_signal_title.setClassName("YellowTitle")
        l_strategy.addWidget(lbl_signal_title)
        
        self.inp_rsi_buy = QDoubleSpinBox(); self.inp_rsi_buy.setRange(10, 90)
        self.inp_rsi_buy.setValue(50.00)
        self.inp_rsi_sell = QDoubleSpinBox(); self.inp_rsi_sell.setRange(10, 90)
        self.inp_rsi_sell.setValue(50.00)
        
        l_strategy.addWidget(QLabel("Deep Drop Trigger (RSI Buy)")); l_strategy.addWidget(self.inp_rsi_buy)
        l_strategy.addWidget(QLabel("Peak Spike Trigger (RSI Sell)")); l_strategy.addWidget(self.inp_rsi_sell)
        
        lbl_grid_title = QLabel("❖ SMART DYNAMIC GRID"); lbl_grid_title.setClassName("YellowTitle")
        l_strategy.addWidget(lbl_grid_title)
        
        self.inp_max_layer = QSpinBox(); self.inp_max_layer.setRange(1, 999); self.inp_max_layer.setValue(100)
        self.inp_expansion_dist = QSpinBox(); self.inp_expansion_dist.setMaximum(50000); self.inp_expansion_dist.setValue(500)
        self.inp_sl_points = QSpinBox(); self.inp_sl_points.setMaximum(100000); self.inp_sl_points.setValue(99999)
        
        l_strategy.addWidget(QLabel("Maximum Depth Array")); l_strategy.addWidget(self.inp_max_layer)
        l_strategy.addWidget(QLabel("Expansion Distance (points)")); l_strategy.addWidget(self.inp_expansion_dist)
        l_strategy.addWidget(QLabel("Emergency Stop Loss (Points)")); l_strategy.addWidget(self.inp_sl_points)
        
        self.inp_trigger_tp = QDoubleSpinBox(); self.inp_trigger_tp.setDecimals(2); self.inp_trigger_tp.setValue(0.30) 
        l_strategy.addWidget(QLabel("Network Take Profit / 0.01 Lot ($)")); l_strategy.addWidget(self.inp_trigger_tp)

        lbl_clean_title = QLabel("❖ SYSTEM PRUNING"); lbl_clean_title.setClassName("YellowTitle")
        l_strategy.addWidget(lbl_clean_title)
        
        self.inp_clean_dist = QSpinBox(); self.inp_clean_dist.setRange(100, 100000)
        self.inp_clean_dist.setValue(99999)
        l_strategy.addWidget(QLabel("Max Distant Node Prune (Points)"))
        l_strategy.addWidget(self.inp_clean_dist)
        
        self.btn_cleanup = QPushButton("AUTO PRUNE ACTIVE")
        self.btn_cleanup.setObjectName("BtnCleanup")
        self.btn_cleanup.setCheckable(True); self.btn_cleanup.setChecked(True) 
        self.btn_cleanup.clicked.connect(self.toggle_cleanup)
        l_strategy.addWidget(self.btn_cleanup)
        self.tabs.addTab(tab_strategy, "Engine")
        
        # --- TAB 3: CLOUD & TELEGRAM ---
        tab_tele = QWidget(); l_tele = QVBoxLayout(tab_tele)
        
        lbl_cloud_title = QLabel("❖ SUPABASE CLOUD SYNC"); lbl_cloud_title.setClassName("YellowTitle")
        l_tele.addWidget(lbl_cloud_title)
        
        self.inp_vps_name = QLineEdit("VPS_1")
        self.inp_supa_url = QLineEdit("")
        self.inp_supa_url.setPlaceholderText("Paste Supabase Project URL here...")
        self.inp_supa_key = QLineEdit("")
        self.inp_supa_key.setPlaceholderText("Paste Supabase API Key here...")
        
        l_tele.addWidget(QLabel("VPS Identity Name")); l_tele.addWidget(self.inp_vps_name)
        l_tele.addWidget(QLabel("Supabase Project URL")); l_tele.addWidget(self.inp_supa_url)
        l_tele.addWidget(QLabel("Supabase API Key")); l_tele.addWidget(self.inp_supa_key)
        
        lbl_tele_title = QLabel("❖ TELEGRAM REMOTE CONTROL"); lbl_tele_title.setClassName("YellowTitle")
        l_tele.addWidget(lbl_tele_title)
        
        self.inp_tel_token = QLineEdit("")
        self.inp_tel_token.setPlaceholderText("Enter HTTP API Token here...")
        self.inp_tel_chat_id = QLineEdit("")
        self.inp_tel_chat_id.setPlaceholderText("Enter Group Chat ID (e.g., -100...)")
        
        l_tele.addWidget(QLabel("Bot API Token")); l_tele.addWidget(self.inp_tel_token)
        l_tele.addWidget(QLabel("Group Chat ID")); l_tele.addWidget(self.inp_tel_chat_id)
        
        self.btn_tel_connect = QPushButton("CONNECT SYSTEMS")
        self.btn_tel_connect.setCheckable(True)
        self.btn_tel_connect.setStyleSheet("background-color: transparent; border: 1px solid #00e5ff; color: #00e5ff; font-weight: bold; padding: 10px; margin-top: 15px;")
        self.btn_tel_connect.clicked.connect(self.toggle_telegram)
        l_tele.addWidget(self.btn_tel_connect)
        
        l_tele.addStretch()
        self.tabs.addTab(tab_tele, "Cloud Link")
        
        # --- TAB 4: ARCHIVE ---
        tab_history = QWidget(); l_history = QVBoxLayout(tab_history)
        lbl_hist_title = QLabel("❖ DATABASE ARCHIVE"); lbl_hist_title.setClassName("YellowTitle")
        l_history.addWidget(lbl_hist_title)
        self.lbl_hist_days = {}
        for i in range(1, 8):
            row_layout = QHBoxLayout()
            lbl_name = QLabel("T-Minus 1 Day:" if i == 1 else f"T-Minus {i} Days:")
            lbl_val = QLabel("0.00 Lot"); lbl_val.setProperty("theme", "value")
            lbl_val.setStyleSheet("color: #3b4f68; font-size: 14px;")
            row_layout.addWidget(lbl_name); row_layout.addWidget(lbl_val, 0, Qt.AlignRight)
            l_history.addLayout(row_layout)
            self.lbl_hist_days[i] = lbl_val 
        l_history.addStretch()
        self.tabs.addTab(tab_history, "Archive")
        
        side_layout.addWidget(self.tabs)
        
        self.btn_start = QPushButton("INITIALIZE SYSTEM")
        self.btn_start.setObjectName("BtnStart")
        self.btn_start.setCheckable(True)
        self.btn_start.clicked.connect(self.toggle_bot)
        side_layout.addWidget(self.btn_start)
        
        lbl_support = QLabel("DEV CONTACT: 0967205522")
        lbl_support.setStyleSheet("color: #00e5ff; font-size: 10px; margin-top: 10px;")
        side_layout.addWidget(lbl_support, alignment=Qt.AlignCenter)

        right_panel = QWidget(); right_layout = QVBoxLayout(right_panel)
        
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""QFrame { background-color: #0b1118; border: 1px solid #00e5ff; border-radius: 8px; padding: 15px; } QLabel { border: none; }""")
        stats_layout = QGridLayout(stats_frame)
        
        self.lbl_bal = QLabel("0.00"); self.lbl_bal.setProperty("theme", "value")
        self.lbl_eq = QLabel("0.00"); self.lbl_eq.setProperty("theme", "value")
        self.lbl_prof = QLabel("$0.00"); self.lbl_prof.setProperty("theme", "value")
        self.lbl_total_pos = QLabel("0"); self.lbl_total_pos.setProperty("theme", "value")
        
        self.lbl_total_lots = QLabel("0.00 Lot"); self.lbl_total_lots.setProperty("theme", "value")
        self.lbl_today_traded_lots = QLabel("0.00 Lot"); self.lbl_today_traded_lots.setProperty("theme", "value")
        
        self.lbl_buy_pos = QLabel("0"); self.lbl_buy_pos.setObjectName("BuyText")
        self.lbl_buy_lots = QLabel("0.00 Lot"); self.lbl_buy_lots.setObjectName("BuyText")
        self.lbl_sell_pos = QLabel("0"); self.lbl_sell_pos.setObjectName("SellText")
        self.lbl_sell_lots = QLabel("0.00 Lot"); self.lbl_sell_lots.setObjectName("SellText")

        self.lbl_time_filter = QLabel("SYSTEM STANDBY")
        self.lbl_time_filter.setStyleSheet("color: #00ffa3; font-weight: 900; font-size: 15px; text-transform: uppercase; letter-spacing: 1px;")

        stats_layout.addWidget(QLabel("NET BALANCE"), 0, 0); stats_layout.addWidget(self.lbl_bal, 0, 1)
        stats_layout.addWidget(QLabel("LIVE EQUITY"), 0, 2); stats_layout.addWidget(self.lbl_eq, 0, 3)
        stats_layout.addWidget(QLabel("FLOAT P/L"), 0, 4); stats_layout.addWidget(self.lbl_prof, 0, 5)
        stats_layout.addWidget(QLabel("ACTIVE NODES"), 0, 6); stats_layout.addWidget(self.lbl_total_pos, 0, 7)
        stats_layout.addWidget(QLabel("NETWORK LOTS"), 0, 8); stats_layout.addWidget(self.lbl_total_lots, 0, 9)
        
        stats_layout.addWidget(QLabel("LONG NODES"), 1, 0); stats_layout.addWidget(self.lbl_buy_pos, 1, 1)
        stats_layout.addWidget(QLabel("LONG LOTS"), 1, 2); stats_layout.addWidget(self.lbl_buy_lots, 1, 3)
        stats_layout.addWidget(QLabel("SHORT NODES"), 1, 4); stats_layout.addWidget(self.lbl_sell_pos, 1, 5)
        stats_layout.addWidget(QLabel("SHORT LOTS"), 1, 6); stats_layout.addWidget(self.lbl_sell_lots, 1, 7)
        
        stats_layout.addWidget(QLabel("CYCLE VOLUME"), 1, 8)
        self.lbl_today_traded_lots.setStyleSheet("color: #ffaa00; font-weight: 900; font-size: 16px;")
        stats_layout.addWidget(self.lbl_today_traded_lots, 1, 9)
        
        lbl_status_title = QLabel("CORE STATUS:"); lbl_status_title.setStyleSheet("color: #5a718c; font-weight: 900; font-size: 12px; letter-spacing: 1px;")
        stats_layout.addWidget(lbl_status_title, 2, 0); stats_layout.addWidget(self.lbl_time_filter, 2, 1, 1, 3) 
        right_layout.addWidget(stats_frame)
        
        self.plot = pg.PlotWidget(); self.plot.setBackground('#060a0f'); self.plot.showGrid(x=True, y=True, alpha=0.15)
        right_layout.addWidget(self.plot); self.candle_item = None
        
        self.logs = QTextEdit(); self.logs.setReadOnly(True); self.logs.setFixedHeight(120)
        self.logs.setStyleSheet("""QTextEdit { background-color: #030508; color: #00e5ff; font-family: 'Consolas', monospace; border: 1px solid #1a2639; border-radius: 6px; padding: 10px; }""")
        right_layout.addWidget(self.logs)
        
        splitter = QSplitter(Qt.Horizontal); splitter.addWidget(sidebar); splitter.addWidget(right_panel); splitter.setSizes([380, 1020])
        main_layout.addWidget(splitter)

    def update_layer_settings(self):
        self.bot.step_l1 = self.inp_l1_dist.value()
        self.bot.step_l2 = self.inp_l2_dist.value()
        self.bot.step_l3 = self.inp_l3_dist.value()
        self.log_msg(f"[SYS] Layers Updated -> L1: {self.bot.step_l1} Pts | L2: {self.bot.step_l2} Pts | L3: {self.bot.step_l3} Pts")

    def toggle_telegram(self):
        if self.btn_tel_connect.isChecked():
            vps_name = self.inp_vps_name.text().strip()
            
            self.bot.supa_url = self.inp_supa_url.text().strip()
            self.bot.supa_key = self.inp_supa_key.text().strip()
            self.bot.vps_name = vps_name
            self.log_msg(f"[SYS] Cloud Sync Module Activated for {vps_name}")

            token = self.inp_tel_token.text().strip()
            chat_id = self.inp_tel_chat_id.text().strip()
            if token and chat_id:
                self.tel_engine = TelegramEngine(token, chat_id, vps_name)
                self.tel_engine.cmd_signal.connect(self.handle_telegram_cmd)
                self.tel_engine.start()
            
            self.btn_tel_connect.setText("SYSTEMS CONNECTED")
            self.btn_tel_connect.setStyleSheet("background-color: rgba(0, 255, 163, 0.1); border: 1px solid #00ffa3; color: #00ffa3; font-weight: bold; padding: 10px; margin-top: 15px;")
        else:
            self.bot.supa_url = ""
            self.bot.supa_key = ""
            if hasattr(self, 'tel_engine'):
                self.tel_engine.is_running = False; self.tel_engine.wait()
            self.btn_tel_connect.setText("CONNECT SYSTEMS")
            self.btn_tel_connect.setStyleSheet("background-color: transparent; border: 1px solid #00e5ff; color: #00e5ff; font-weight: bold; padding: 10px; margin-top: 15px;")
            self.log_msg("[SYS] Cloud & Telegram Links Severed.")

    def handle_telegram_cmd(self, cmd):
        if cmd == "STOP":
            if self.btn_start.isChecked():
                self.btn_start.setChecked(False); self.toggle_bot() 
        elif cmd == "START":
            if not self.btn_start.isChecked():
                self.btn_start.setChecked(True); self.toggle_bot() 
        elif cmd == "STATUS":
            if hasattr(self, 'tel_engine'):
                state = "🟢 RUNNING" if self.bot.is_running else "🔴 STOPPED"
                msg = f"📊 [{self.inp_vps_name.text().upper()}]\nStatus: {state}\nBalance: {self.lbl_bal.text()}\nEquity: {self.lbl_eq.text()}\nProfit: {self.lbl_prof.text()}\nNodes: {self.lbl_total_pos.text()}"
                self.tel_engine.send_msg(msg)
                
    def send_telegram_alert(self, msg):
        if hasattr(self, 'tel_engine') and self.btn_tel_connect.isChecked():
            self.tel_engine.send_msg(f"[{self.inp_vps_name.text().upper()}] {msg}")

    def set_inputs_enabled(self, enabled):
        self.inp_sym.setEnabled(enabled)
        self.inp_lot.setEnabled(enabled)
        self.inp_l1_dist.setEnabled(enabled)
        self.inp_l2_dist.setEnabled(enabled)
        self.inp_l3_dist.setEnabled(enabled)
        self.inp_max_layer.setEnabled(enabled)
        self.inp_expansion_dist.setEnabled(enabled)
        self.inp_sl_points.setEnabled(enabled)
        self.inp_clean_dist.setEnabled(enabled)
        self.inp_rsi_buy.setEnabled(enabled)
        self.inp_rsi_sell.setEnabled(enabled) 
        self.chk_time_filter.setEnabled(enabled)
        self.chk_daily_close.setEnabled(enabled)
        self.inp_equity_protect.setEnabled(enabled)

    def update_dash(self, data):
        self.lbl_bal.setText(f"${data['bal']:,.2f}"); self.lbl_eq.setText(f"${data['eq']:,.2f}")
        self.lbl_prof.setText(f"${data['prof']:,.2f}"); self.lbl_total_pos.setText(f"{data['total_pos']}")
        total_lots = data['buy_lots'] + data['sell_lots']
        self.lbl_total_lots.setText(f"{total_lots:.2f} Lot"); self.lbl_today_traded_lots.setText(f"{data['today_traded_lots']:.2f} Lot")
        self.lbl_buy_pos.setText(f"{data['buy_count']}"); self.lbl_buy_lots.setText(f"{data['buy_lots']:.2f} Lot")
        self.lbl_sell_pos.setText(f"{data['sell_count']}"); self.lbl_sell_lots.setText(f"{data['sell_lots']:.2f} Lot")
        
        if data['prof'] < 0: self.lbl_prof.setStyleSheet("color: #ff3366; font-weight: bold; font-size: 18px;")
        else: self.lbl_prof.setStyleSheet("color: #00ffa3; font-weight: bold; font-size: 18px;")

        if "past_lots" in data:
            for i in range(1, 8):
                lot_val = data["past_lots"].get(i, 0.0)
                self.lbl_hist_days[i].setText(f"{lot_val:.2f} Lot")
                if lot_val > 0: self.lbl_hist_days[i].setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 14px;")
                else: self.lbl_hist_days[i].setStyleSheet("color: #3b4f68; font-weight: bold; font-size: 14px;")
        
        if "time_status" in data:
            self.lbl_time_filter.setText(data["time_status"])
            if "ONLINE" in data["time_status"]: self.lbl_time_filter.setStyleSheet("color: #00ffa3; font-weight: 900; font-size: 15px; letter-spacing: 1px;")
            elif "OFFLINE" in data["time_status"]: self.lbl_time_filter.setStyleSheet("color: #ff3366; font-weight: 900; font-size: 15px; letter-spacing: 1px;")
            elif "STANDBY" in data["time_status"]: self.lbl_time_filter.setStyleSheet("color: #ffaa00; font-weight: 900; font-size: 15px; letter-spacing: 1px;")

    def update_chart(self, data):
        if self.candle_item: self.plot.removeItem(self.candle_item)
        self.candle_item = CandlestickItem(data); self.plot.addItem(self.candle_item)

    def log_msg(self, msg):
        self.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        scrollbar = self.logs.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def toggle_cleanup(self):
        if self.btn_cleanup.isChecked():
            self.bot.auto_cleanup_enabled = True; self.bot.max_cleanup_distance = self.inp_clean_dist.value()
            self.btn_cleanup.setText("AUTO PRUNE ACTIVE")
            self.btn_cleanup.setStyleSheet("background-color: transparent; border: 1px solid #00ffa3; color: #00ffa3; font-weight: bold;")
            self.log_msg(f"[SYS] Auto-Prune Engaged. Distance: {self.bot.max_cleanup_distance} Pts")
        else:
            self.bot.auto_cleanup_enabled = False
            self.btn_cleanup.setText("AUTO PRUNE OFFLINE")
            self.btn_cleanup.setStyleSheet("background-color: transparent; border: 1px solid #ff3366; color: #ff3366; font-weight: bold;")
            self.log_msg("[SYS] Auto-Prune Disengaged.")

    def handle_force_stop(self):
        if self.btn_start.isChecked(): self.btn_start.setChecked(False)
        self.set_inputs_enabled(True)
        self.btn_start.setText("INITIALIZE SYSTEM")
        self.log_msg("[SYS] CRITICAL HALT COMMAND EXECUTED.")

    def toggle_bot(self):
        if self.btn_start.isChecked():
            self.set_inputs_enabled(False) 
            self.bot.symbol = self.inp_sym.text()
            self.bot.lot_size = self.inp_lot.value()
            
            self.bot.step_l1 = self.inp_l1_dist.value() 
            self.bot.step_l2 = self.inp_l2_dist.value() 
            self.bot.step_l3 = self.inp_l3_dist.value() 
            
            self.bot.max_layers = self.inp_max_layer.value()
            self.bot.expansion_dist = self.inp_expansion_dist.value()
            
            self.bot.sl_points = self.inp_sl_points.value()
            self.bot.trigger_tp_per_001 = self.inp_trigger_tp.value()
            self.bot.rsi_buy_level = self.inp_rsi_buy.value()
            self.bot.rsi_sell_level = self.inp_rsi_sell.value()
            self.bot.max_candle_size = self.inp_max_candle.value()
            self.bot.use_time_filter = self.chk_time_filter.isChecked()
            self.bot.use_daily_close = self.chk_daily_close.isChecked()
            self.bot.equity_protection_pct = self.inp_equity_protect.value()
            self.bot.auto_cleanup_enabled = self.btn_cleanup.isChecked()
            self.bot.max_cleanup_distance = self.inp_clean_dist.value()
            
            self.bot.vps_name = self.inp_vps_name.text().strip()
            self.bot.supa_url = self.inp_supa_url.text().strip()
            self.bot.supa_key = self.inp_supa_key.text().strip()
            
            self.bot.is_running = True; self.bot.start()
            self.btn_start.setText("HALT SYSTEM")
        else:
            self.bot.is_running = False; self.bot.wait()
            self.set_inputs_enabled(True)
            self.btn_start.setText("INITIALIZE SYSTEM")

if __name__ == '__main__':
    QLabel.setClassName = lambda self, name: self.setProperty("class", name)
    app = QApplication(sys.argv); window = HybridHunterGUI(); window.show()
    sys.exit(app.exec_())