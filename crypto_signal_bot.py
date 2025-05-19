import ccxt
import pandas as pd
import pandas_ta as ta
import csv
import os
import time
import json
from datetime import datetime, timedelta

# Optional: Uncomment if you want colored console output
# from colorama import Fore, Style, init
# init(autoreset=True)

# Initialize Binance
exchange = ccxt.binance()

# Load markets and filter for active USDT pairs
markets = exchange.load_markets()
symbols = [symbol for symbol, data in markets.items() if "/USDT" in symbol and data['active']]

# Define which symbols you'd want QUTEX signals for (from Binance USDT pairs)
qutex_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]

# Log files
log_file = "signals_log.csv"
text_log_file = "signals_log.txt"
tp_hit_log_file = "tp_hit_log.txt"
qutex_log_file = "qutex_signals_log.txt"
last_signal_file = "last_signals.json"

# Load last signals history or initialize empty
if os.path.exists(last_signal_file):
    with open(last_signal_file, "r") as f:
        last_signals = json.load(f)
else:
    last_signals = {}

# Function to save updated last signal times
def save_last_signals():
    with open(last_signal_file, "w") as f:
        json.dump(last_signals, f)

# Function to log signals to text file
def log_signal(message):
    with open(text_log_file, "a", encoding="utf-8") as f:
        f.write(f"{message}\n")

# Function to log signals to CSV file
def log_to_csv(symbol, price, atr, buy_price, take_profit, stop_loss):
    file_exists = os.path.isfile(log_file)
    with open(log_file, mode="a", newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Time", "Symbol", "Price", "ATR", "Buy Price", "Take Profit", "Stop Loss"])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([now, symbol, price, atr, buy_price, take_profit, stop_loss])

# Function to log QUTEX signals separately
def log_qutex_signal(message):
    with open(qutex_log_file, "a", encoding="utf-8") as f:
        f.write(f"{message}\n")

# Function to log QUTEX signals to both text and CSV file
def log_qutex_signal(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Log to text file
    with open(qutex_log_file, "a", encoding="utf-8") as f:
        f.write(f"{message}\n")
    
    # Log to CSV file
    csv_file = "quotex_signals_log.csv"
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, mode="a", newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Time", "Signal"])
        writer.writerow([now, message])


# Function to log Take Profit hits
def log_tp_hit(message):
    with open(tp_hit_log_file, "a", encoding="utf-8") as f:
        f.write(f"{message}\n")

# Function to fetch OHLCV and calculate signals
def analyze_market(symbol, timeframe):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

        df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        latest = df.iloc[-1]

        close_price = latest["close"]
        atr = latest["ATR"]

        if pd.isna(atr):
            print(f"⏭️ {symbol} {timeframe} - ATR not available yet.")
            return

        buy_price = close_price - (atr * 0.5)
        take_profit = close_price + (atr * 1.0)
        stop_loss = close_price - (atr * 1.0)

        profit_percent = ((take_profit - buy_price) / buy_price) * 100

        avg_volume = df["volume"].rolling(20).mean().iloc[-1]
        current_volume = latest["volume"]

        key = f"{symbol}_{timeframe}"
        last_signal_time = last_signals.get(key)

        now = datetime.now()

        # Log ticker info (can colorize if using colorama)
        print(f"{symbol} {timeframe} | Volume: {current_volume:.2f} vs Avg: {avg_volume:.2f} | Profit: {profit_percent:.2f}%")

        # Signal conditions
        if current_volume > avg_volume * 1 and profit_percent >= 0.5:
            if not last_signal_time or (now - datetime.fromisoformat(last_signal_time)) > timedelta(hours=24):
                message = (
                    f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] ⚡ {symbol} [{timeframe}] ALERT\n"
                    f"Current Price: {close_price:.4f}\n"
                    f"ATR: {atr:.4f}\n"
                    f"✅ Buy Price: {buy_price:.4f}\n"
                    f"🎯 Take Profit: {take_profit:.4f}\n"
                    f"🛑 Stop Loss: {stop_loss:.4f}\n"
                    f"Expected Profit: {profit_percent:.2f}%\n"
                    f"---"
                )
                print(message)
                log_signal(message)
                log_to_csv(symbol, close_price, atr, buy_price, take_profit, stop_loss)

                if symbol in qutex_symbols:
                    log_qutex_signal(message)

                last_signals[key] = now.isoformat()
                save_last_signals()
            else:
                print(f"⏸️ {symbol} {timeframe} - Signal sent at {last_signal_time}. Waiting 24hr cooldown.")
        else:
            print(f"❌ No signal for {symbol} {timeframe} - Conditions not met.")

        # Monitor if Take Profit hit (in real usage, you'd track this separately — simplified here)
        if close_price >= take_profit:
            tp_message = (
                f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 🎉 {symbol} [{timeframe}] HIT Take Profit at {close_price:.4f} 🎯"
            )
            print(tp_message)
            log_tp_hit(tp_message)

    except Exception as e:
        print(f"❌ Error fetching {symbol} {timeframe}: {e}")

# Toggle infinite loop ON/OFF
INFINITE_LOOP = True

try:
    while INFINITE_LOOP:
        for symbol in symbols[:50]:  # Limit to avoid API ban
            for tf in ["15m", "1h", "4h"]:
                analyze_market(symbol, tf)
                time.sleep(0.5)  # API rate limit respect
        print("\n✅ Cycle complete. Waiting 60 seconds...\n")
        time.sleep(60)

except KeyboardInterrupt:
    print("\n🚨 Bot stopped by user.")
