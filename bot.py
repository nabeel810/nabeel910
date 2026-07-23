Enterimport time
import requests
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
import sqlite3

TOKEN = "8469297826:AAH6onC_4Pdmqej7ZoSNV-1cPjhr-VeVjpE"
CHAT_ID = "6557169034"

ASSETS = {
    "XAUUSD": {"name": "الذهب", "ticker": "GC=F", "htf": "1h", "ltf": "15m", "type": "fast"},
    "GBPUSD": {"name": "الباوند / دولار", "ticker": "GBPUSD=X", "htf": "1h", "ltf": "15m", "type": "fast"},
    "NZDUSD": {"name": "النيوزيلندي / دولار", "ticker": "NZDUSD=X", "htf": "1h", "ltf": "15m", "type": "fast"},
    "EURUSD": {"name": "اليورو / دولار", "ticker": "EURUSD=X", "htf": "1h", "ltf": "5m", "type": "slow"},
    "AUDUSD": {"name": "الدولار الأسترالي", "ticker": "AUDUSD=X", "htf": "1h", "ltf": "5m", "type": "slow"},
    "USDJPY": {"name": "الدولار / الين", "ticker": "USDJPY=X", "htf": "1h", "ltf": "5m", "type": "slow"},
}

def init_db():
    conn = sqlite3.connect("trading_signals.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_signals (
            symbol TEXT PRIMARY KEY,
            signal_type TEXT,
            entry REAL,
            sl REAL,
            tp1 REAL,
            tp2 REAL,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"خطأ: {e}")

def check_session_filter():
    now_utc = datetime.now(timezone.utc)
    current_hour = now_utc.hour
    is_london = 7 <= current_hour <= 10
    is_newyork = 13 <= current_hour <= 16
    if is_london:
        return True, "جلسة لندن"
    elif is_newyork:
        return True, "جلسة نيويورك"
    else:
        return False, "خارج الجلسات"

def calculate_indicators(df):
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    high_diff = df['High'].diff()
    low_diff = -df['Low'].diff()
    
    pos_dm = pd.Series([h if h > l and h > 0 else 0 for h, l in zip(high_diff, low_diff)], index=df.index)
    neg_dm = pd.Series([l if l > h and l > 0 else 0 for h, l in zip(high_diff, low_diff)], index=df.index)
    
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift()).abs()
    tr3 = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(14).mean()
    plus_di = 100 * (pos_dm.rolling(14).mean() / atr)
    minus_di = 100 * (neg_dm.rolling(14).mean() / atr)
    
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).abs() * 100
    df['ADX'] = dx.rolling(14).mean().fillna(25)
    return df

def fetch_market_data(ticker, interval, period="5d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = calculate_indicators(df)
        return df
    except Exception as e:
        print(f"خطأ بيانات {ticker}: {e}")
        return None

def calculate_smart_sl_tp(df_ltf, current_price, trend):
    recent_low = df_ltf['Low'].tail(20).min()
    recent_high = df_ltf['High'].tail(20).max()
    buffer = (current_price * 0.0005)

    if "Bullish" in trend:
        sl = recent_low - buffer
        risk = current_price - sl
        tp1 = current_price + (risk * 1.5)
        tp2 = current_price + (risk * 3.0)
    else:
        sl = recent_high + buffer
        risk = sl - current_price
        tp1 = current_price - (risk * 1.5)
        tp2 = current_price - (risk * 3.0)

    return round(float(sl), 4), round(float(tp1), 4), round(float(tp2), 4)

def manage_active_signals():
    conn = sqlite3.connect("trading_signals.db")
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, signal_type, entry, sl, tp1, tp2, status FROM active_signals")
    rows = cursor.fetchall()

    for row in rows:
        symbol, sig_type, entry, sl, tp1, tp2, status = row
        config = ASSETS.get(symbol)
        if not config:
            continue

        df_live = fetch_market_data(config["ticker"], "1m", period="1d")
        if df_live is None or df_live.empty:
            continue
        current_price = float(df_live.iloc[-1]['Close'])

        if "شراء" in sig_type:
            if status == "OPEN" and current_price >= tp1:
                send_telegram_message(f"🎯 *تحديث Break-Even*\nالأصل: {config['name']} (`{symbol}`)\nتم تحقيق الهدف الأول (TP1). انقل الوقف لنقطة الدخول (`{entry}`).")
                cursor.execute("UPDATE active_signals SET status = 'BE_SET' WHERE symbol = ?", (symbol,))
                conn.commit()
            elif current_price >= tp2:
                send_telegram_message(f"🏆 *هدف ثاني محقق!* الأصل {config['name']} (`{symbol}`) ضرب TP2. تم إغلاق التتبع.")
                cursor.execute("DELETE FROM active_signals WHERE symbol = ?", (symbol,))
                conn.commit()
            elif current_price <= sl:
                send_telegram_message(f"❌ *وقف خسارة:* الأصل {config['name']} (`{symbol}`) ضرب الوقف.")
                cursor.execute("DELETE FROM active_signals WHERE symbol = ?", (symbol,))
                conn.commit()
        else:
            if status == "OPEN" and current_price <= tp1:
                send_telegram_message(f"🎯 *تحديث Break-Even*\nالأصل: {config['name']} (`{symbol}`)\nتم تحقيق الهدف الأول (TP1). انقل الوقف لنقطة الدخول (`{entry}`).")
                cursor.execute("UPDATE active_signals SET status = 'BE_SET' WHERE symbol = ?", (symbol,))
                conn.commit()
            elif current_price <= tp2:
                send_telegram_message(f"🏆 *هدف ثاني محقق!* الأصل {config['name']} (`{symbol}`) ضرب TP2. تم إغلاق التتبع.")
                cursor.execute("DELETE FROM active_signals WHERE symbol = ?", (symbol,))
                conn.commit()
            elif current_price >= sl:
                send_telegram_message(f"❌ *وقف خسارة:* الأصل {config['name']} (`{symbol}`) ضرب الوقف.")
                cursor.execute("DELETE FROM active_signals WHERE symbol = ?", (symbol,))
                conn.commit()
    conn.close()

def analyze_asset(symbol, config):
    conn = sqlite3.connect("trading_signals.db")
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM active_signals WHERE symbol = ?", (symbol,))
    existing = cursor.fetchone()
    conn.close()
    if existing:
        return None

    session_active, session_name = check_session_filter()
    if not session_active:
        return None

    df_htf = fetch_market_data(config["ticker"], config["htf"])
    if df_htf is None or len(df_htf) < 200:
        return None
        
    last_htf = df_htf.iloc[-1]
    current_price = float(last_htf['Close'])
    ema_200 = float(last_htf['EMA_200'])
    adx_val = float(last_htf['ADX'])

    if adx_val <= 20:
        return None

    trend_direction = "Bullish (صاعد)" if current_price > ema_200 else "Bearish (هابط)" if current_price < ema_200 else ""
    if not trend_direction:
        return None

    df_ltf = fetch_market_data(config["ticker"], config["ltf"], period="2d")
    if df_ltf is None or len(df_ltf) < 5:
        return None
        
    prev_candle = df_ltf.iloc[-2]
    curr_candle = df_ltf.iloc[-1]
    is_bos_confirmed = curr_candle['Close'] > prev_candle['High'] if "Bullish" in trend_direction else curr_candle['Close'] < prev_candle['Low']
    if not is_bos_confirmed:
        return None

    sl, tp1, tp2 = calculate_smart_sl_tp(df_ltf, current_price, trend_direction)
    signal_type = "شراء (BUY / LONG)" if "Bullish" in trend_direction else "بيع (SELL / SHORT)"

    conn = sqlite3.connect("trading_signals.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO active_signals VALUES (?, ?, ?, ?, ?, ?, 'OPEN')",
                   (symbol, signal_type, current_price, sl, tp1, tp2))
    conn.commit()
    conn.close()

    return {
        "symbol": symbol, "name": config["name"], "type": signal_type,
        "trend": trend_direction, "adx": round(adx_val, 2), "session": session_name,
        "interval": config["ltf"], "entry": round(current_price, 4),
        "sl": sl, "tp1": tp1, "tp2": tp2
    }

def main():
    print("🚀 بدء فحص السوق...")
    for symbol, config in ASSETS.items():
        signal = analyze_asset(symbol, config)
        if signal:
            msg = (
                f"🚨 *إشارة تداول جديدة (ICT/SMC)*\n"
                f"------------------------------------\n"
                f"📌 الأصل: {signal['name']} (`{signal['symbol']}`)\n"
                f"📊 الصفقة: *{signal['type']}*\n"
                f"⏱️ الفريم: `{signal['interval']}`\n\n"
                f"🎯 المستويات:\n"
                f"• الدخول: `{signal['entry']}`\n"
                f"• الوقف (SL): `{signal['sl']}`\n"
                f"• الهدف 1 (TP1): `{signal['tp1']}`\n"
                f"• الهدف 2 (TP2): `{signal['tp2']}`\n"
                f"------------------------------------"
            )
            send_telegram_message(msg)
        time.sleep(2)
        
    manage_active_signals()

if __name__ == "__main__":
    main()
