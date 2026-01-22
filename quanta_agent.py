# =============================================
# HYBRID QUANTA ULTIMATE v2026 - REVISED
# المطور: محمد محرم
# التعديلات: إصلاح FVG + تحسين الجذر الرقمي + دعم عربي/إنجليزي في المشاعر
# =============================================

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import feedparser
from datetime import datetime
import pytz
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re

# --- الإعدادات الفنية ---
SYMBOL = "BTCUSD"
TIMEFRAMES = {
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1
}

vader = SentimentIntensityAnalyzer()

# --- قاموس QTT المطور (يدعم كلمات عربية وإنجليزية) ---
qtt_lexicon = {
    # إنجليزي
    "growth": 0.92, "rally": 0.88, "bullish": 0.90, "uptrend": 0.85,
    "surge": 0.87, "etf": 0.82, "accumulation": 0.88, "institutional": 0.90,
    "whale": 0.88, "crash": 0.15, "drop": 0.30, "bearish": 0.25,
    "sell-off": 0.28,
    # عربي
    "ارتفاع": 0.88, "تجميع": 0.87, "اختراق": 0.90,
    "هبوط": 0.30, "تصحيح": 0.38, "ضعف": 0.35
}

# --- RSS Sources ---
RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptopotato.com/feed/"
]

# ==========================
# MACD (تم إصلاح تداخل الأسطر هنا)
# ==========================
def macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def macd_trend(df):
    _, _, hist = macd(df['close'])
    last = hist.iloc[-1]
    return "BULLISH" if last > 0 else "BEARISH" if last < 0 else "NEUTRAL"

# ==========================
# Digital Root (مُحسّن)
# ==========================
def digital_root(price):
    s = str(price).replace('.', '').replace('-', '')
    s = s.lstrip('0')
    if not s:
        return 0
    total = sum(int(d) for d in s)
    return 1 + (total - 1) % 9 if total != 0 else 0

# ==========================
# FVG Detection (مُصلَح)
# ==========================
def detect_fvg(symbol, tf):
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 100)
    if rates is None or len(rates) < 10:
        return "NO_DATA", 0.0

    df = pd.DataFrame(rates)
    for i in range(len(df) - 3, 1, -1):
        if df['low'].iloc[i] > df['high'].iloc[i + 2]:
            gap_price = (df['low'].iloc[i] + df['high'].iloc[i + 2]) / 2
            return "BULLISH_FVG", gap_price
        if df['high'].iloc[i] < df['low'].iloc[i + 2]:
            gap_price = (df['high'].iloc[i] + df['low'].iloc[i + 2]) / 2
            return "BEARISH_FVG", gap_price
    return "NEUTRAL", 0.0

# ==========================
# Market Reaction (Volume) (تم إصلاح تداخل الأسطر هنا)
# ==========================
def market_reaction(symbol, tf):
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, 30)
    if rates is None or len(rates) < 10:
        return "NO_DATA"
    df = pd.DataFrame(rates)
    recent_vol = df['tick_volume'].iloc[-5:].mean()
    past_vol = df['tick_volume'].iloc[-15:-5].mean()
    if past_vol == 0:
        return "WEAK"
    vol_change = recent_vol / past_vol
    return "STRONG" if vol_change > 1.4 else "WEAK"

# ==========================
# News Sentiment
# ==========================
def fetch_news():
    titles = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                text = entry.title + " " + (entry.summary if 'summary' in entry else "")
                titles.append(text)
        except Exception as e:
            print(f"[تحذير] فشل تحميل الأخبار من {url}: {e}")
            continue
    return " | ".join(titles[:5])

def analyze_sentiment(text):
    clean_text = re.sub(r'<[^>]+>', '', text)
    words = clean_text.lower().split()
    
    v_score = vader.polarity_scores(clean_text)['compound']
    v_norm = (v_score + 1) / 2

    q_scores = [qtt_lexicon.get(w, 0.5) for w in words if w in qtt_lexicon]
    q_score = np.mean(q_scores) if q_scores else 0.5

    final = v_norm * 0.6 + q_score * 0.4
    return np.clip(final, 0.0, 1.0)

# ==========================
# Report Builder
# ==========================
def build_report(symbol, base_tf_name="M15"):
    if not mt5.initialize():
        return "❌ خطأ: فشل تهيئة MT5"
    if not mt5.symbol_select(symbol, True):
        mt5.shutdown()
        return f"❌ الرمز {symbol} غير متاح في MT5"

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        mt5.shutdown()
        return "❌ لا يمكن جلب سعر حي"

    price = tick.bid
    root = digital_root(price)

    fvg_status, fvg_price = detect_fvg(symbol, TIMEFRAMES[base_tf_name])
    reaction = market_reaction(symbol, TIMEFRAMES[base_tf_name])

    macd_trends = {}
    for tf_name, tf in TIMEFRAMES.items():
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, 200)
        if rates is None or len(rates) < 50:
            macd_trends[tf_name] = "NO_DATA"
            continue
        df = pd.DataFrame(rates)
        macd_trends[tf_name] = macd_trend(df)

    news_text = fetch_news()
    sentiment_score = analyze_sentiment(news_text)
    sentiment_label = "Bullish" if sentiment_score > 0.6 else "Bearish" if sentiment_score < 0.4 else "Neutral"

    high_confidence = (root in [1, 9]) and (reaction == "STRONG")
    verdict = "High Conviction" if high_confidence else "Monitoring"

    action = "N/A"
    sl, tp = 0.0, 0.0
    if verdict == "High Conviction":
        if fvg_status == "BULLISH_FVG" and sentiment_score > 0.55:
            action = "BUY"
            sl = fvg_price if fvg_price > 0 else price * 0.98
            tp = price * 1.04
        elif fvg_status == "BEARISH_FVG" and sentiment_score < 0.45:
            action = "SELL"
            sl = fvg_price if fvg_price > 0 else price * 1.02
            tp = price * 0.96

    report = f"""
[تقرير ذكاء كوانتا الهجين]
الأصل: {symbol} | السعر: {price:.1f}
الوقت: {datetime.now(pytz.timezone('Africa/Cairo')).strftime('%d %b %Y | %I:%M %p (EET)')}

الجذر الرقمي: {root} ({'دورة نشطة' if root in [1,9] else 'مستقر'})
حالة FVG: {fvg_status} | سعر الفجوة: {fvg_price:.1f}
رد فعل السوق: {reaction}

اتجاه MACD عبر الأطر الزمنية:
"""
    for tf, tr in macd_trends.items():
        report += f"- {tf}: {tr}\n"

    report += f"""
تحليل المشاعر:
- الدرجة: {sentiment_score:.2f}
- التصنيف: {sentiment_label}

الحكم: {verdict}
الإجراء المقترح: {action}
وقف الخسارة: {sl:.1f} | أخذ الربح: {tp:.1f}
---------------------------------
#كوانتا_فينتيك #تداول_ذكي #FVG #MACD #تحليل_مشاعر
"""
    mt5.shutdown()
    return report

# ==========================
# Main
# ==========================
if __name__ == "__main__":
    print(build_report(SYMBOL, "M15"))
