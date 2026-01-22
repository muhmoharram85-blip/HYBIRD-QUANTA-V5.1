# =============================================
# HYBRID QUANTA v5.1 – Institutional Grade Market Intelligence
# Developer: Mohamed Moharram
# Date: January 2026
# =============================================

import pandas as pd
import numpy as np
import requests
import yfinance as yf
from datetime import datetime
import pytz
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

qtt_lexicon = {
    "growth": 0.92, "rally": 0.88, "bullish": 0.90, "uptrend": 0.85,
    "surge": 0.87, "accumulation": 0.88, "institutional": 0.90, "whale": 0.88,
    "crash": 0.15, "drop": 0.30, "bearish": 0.25, "sell-off": 0.28,
    "ارتفاع": 0.88, "تجميع": 0.87, "اختراق": 0.90,
    "هبوط": 0.30, "تصحيح": 0.38, "ضعف": 0.35
}

vader = SentimentIntensityAnalyzer()

def get_binance_ohlcv(symbol="BTCUSDT", interval="15m", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        data = requests.get(url, timeout=10).json()
        if not data or len(data) < 10: return None
        df = pd.DataFrame(data, columns=['open_time','open','high','low','close','volume','close_time','qav','trades','taker_base','taker_quote','ignore'])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)
        return df
    except:
        return None

def get_yahoo_ohlcv(symbol="^IXIC", interval="15m", period="5d"):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist.empty or len(hist) < 10: return None
        hist.reset_index(inplace=True)
        return hist[['Open', 'High', 'Low', 'Close', 'Volume']].rename(columns={'Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'})
    except:
        return None

def digital_root(price):    s = str(price).replace('.', '').replace('-', '').lstrip('0')
    if not s: return 0
    total = sum(int(d) for d in s)
    return 1 + (total - 1) % 9 if total != 0 else 0

def macd_trend(df):
    if len(df) < 30: return "NO_DATA"
    exp1 = df['close'].ewm(span=12).mean()
    exp2 = df['close'].ewm(span=26).mean()
    macd_line = exp1 - exp2
    signal = macd_line.ewm(span=9).mean()
    hist = macd_line - signal
    last = hist.iloc[-1]
    return "BULLISH" if last > 0 else "BEARISH" if last < 0 else "NEUTRAL"

def detect_fvg(df):
    if len(df) < 5: return "NEUTRAL", 0.0
    for i in range(len(df) - 3, 1, -1):
        if df['low'].iloc[i] > df['high'].iloc[i + 2]:
            gap = (df['low'].iloc[i] + df['high'].iloc[i + 2]) / 2
            return "BULLISH_FVG", gap
        if df['high'].iloc[i] < df['low'].iloc[i + 2]:
            gap = (df['high'].iloc[i] + df['low'].iloc[i + 2]) / 2
            return "BEARISH_FVG", gap
    return "NEUTRAL", 0.0

def market_reaction(df):
    if len(df) < 15: return "NO_DATA"
    recent = df['volume'].iloc[-5:].mean()
    past = df['volume'].iloc[-15:-5].mean()
    if past == 0: return "WEAK"
    return "STRONG" if recent / past > 1.4 else "WEAK"

def analyze_sentiment(text):
    clean = re.sub(r'<[^>]+>', '', text)
    words = clean.lower().split()
    v_score = vader.polarity_scores(clean)['compound']
    v_norm = (v_score + 1) / 2
    q_scores = [qtt_lexicon.get(w, 0.5) for w in words if w in qtt_lexicon]
    q_score = np.mean(q_scores) if q_scores else 0.5
    return np.clip(v_norm * 0.6 + q_score * 0.4, 0, 1)

def quanta_analyze(symbol: str, asset_type: str = "auto"):
    if asset_type == "auto":
        asset_type = "crypto" if symbol.endswith(("USDT", "BTC", "ETH")) else "stock"

    if asset_type == "crypto":
        df_m15 = get_binance_ohlcv(symbol, "15m")
        df_h1 = get_binance_ohlcv(symbol, "1h")
        df_h4 = get_binance_ohlcv(symbol, "4h")        df_d1 = get_binance_ohlcv(symbol, "1d")
        df_w1 = get_binance_ohlcv(symbol, "1w")
    else:
        df_m15 = get_yahoo_ohlcv(symbol, "15m", "5d")
        df_h1 = get_yahoo_ohlcv(symbol, "1h", "1mo")
        df_h4 = get_yahoo_ohlcv(symbol, "1h", "2mo")
        df_d1 = get_yahoo_ohlcv(symbol, "1d", "6mo")
        df_w1 = get_yahoo_ohlcv(symbol, "1wk", "2y")

    if df_m15 is None or df_m15.empty:
        return f"❌ لا يمكن جلب بيانات لـ {symbol}"

    price = df_m15['close'].iloc[-1]
    root = digital_root(price)
    fvg_status, fvg_price = detect_fvg(df_m15)
    reaction = market_reaction(df_m15)

    macd_trends = {}
    for tf_name, df in [("M15", df_m15), ("H1", df_h1), ("H4", df_h4), ("D1", df_d1), ("W1", df_w1)]:
        macd_trends[tf_name] = macd_trend(df) if df is not None else "NO_DATA"

    sentiment_score = 0.65
    sentiment_label = "Bullish" if sentiment_score > 0.6 else "Bearish" if sentiment_score < 0.4 else "Neutral"

    high_confidence = (root in [1, 9]) and (reaction == "STRONG")
    verdict = "High Conviction" if high_confidence else "Monitoring"

    action = "N/A"
    sl, tp = 0.0, 0.0
    if verdict == "High Conviction":
        if fvg_status == "BULLISH_FVG":
            action = "BUY"
            sl = fvg_price if fvg_price > 0 else price * 0.98
            tp = price * 1.04
        elif fvg_status == "BEARISH_FVG":
            action = "SELL"
            sl = fvg_price if fvg_price > 0 else price * 1.02
            tp = price * 0.96

    report = f"""
[تقرير HYBRID QUANTA v5.1]
المطور: محمد محرم
الأصل: {symbol} | السعر: {price:.2f}
الوقت: {datetime.now(pytz.timezone('Africa/Cairo')).strftime('%d %b %Y | %I:%M %p (EET)')}

الجذر الرقمي: {root} ({'دورة نشطة' if root in [1,9] else 'مستقر'})
حالة FVG: {fvg_status} | سعر الفجوة: {fvg_price:.2f}
رد فعل السوق: {reaction}

اتجاه MACD عبر الأطر الزمنية:"""
    for tf, tr in macd_trends.items():
        report += f"- {tf}: {tr}\n"

    report += f"""
تحليل المشاعر (تقديري): {sentiment_label} ({sentiment_score:.2f})
الحكم: {verdict}
الإجراء المقترح: {action}
وقف الخسارة: {sl:.2f} | أخذ الربح: {tp:.2f}
---------------------------------
© HYBRID QUANTA v5.1 – QUATNA ECON | لا يُعد نصيحة مالية
"""
    return report

if __name__ == "__main__":
    import os
    from flask import Flask, request

    app = Flask(__name__)

    @app.route('/report')
    def report():
        symbol = request.args.get('symbol', '^IXIC')
        asset_type = request.args.get('type', 'auto')
        result = quanta_analyze(symbol, asset_type)
        return f"<pre dir='rtl'>{result}</pre>"

    @app.route('/')
    def home():
        return """
        <h2>HYBRID QUANTA v5.1</h2>
        <p>من تطوير: محمد محرم</p>
        <p>مثال: <a href='/report?symbol=BTCUSDT'>تحليل البيتكوين</a></p>
        <p>مثال: <a href='/report?symbol=^IXIC'>تحليل ناسداك</a></p>
        """

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
