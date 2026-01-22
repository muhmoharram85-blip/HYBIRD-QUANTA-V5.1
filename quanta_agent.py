# =============================================
# HYBRID QUANTA ULTIMATE v2026 - FINAL CLOUD VERSION
# المطور: محمد محرم
# الوصف: نسخة متوافقة مع Render/Linux باستخدام Yahoo Finance
# =============================================

import yfinance as yf
import pandas as pd
import numpy as np
import feedparser
from datetime import datetime
import pytz
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re

# --- الإعدادات الفنية ---
SYMBOL = "BTC-USD" 

vader = SentimentIntensityAnalyzer()

# قاموس المشاعر المطور
qtt_lexicon = {
    "growth": 0.92, "rally": 0.88, "bullish": 0.90, "uptrend": 0.85,
    "surge": 0.87, "etf": 0.82, "accumulation": 0.88, "institutional": 0.90,
    "whale": 0.88, "crash": 0.15, "drop": 0.30, "bearish": 0.25,
    "sell-off": 0.28, "ارتفاع": 0.88, "تجميع": 0.87, "اختراق": 0.90,
    "هبوط": 0.30, "تصحيح": 0.38, "ضعف": 0.35
}

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptopotato.com/feed/"
]

# --- دالة MACD (تم إصلاح فصل الأسطر) ---
def macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

# --- دالة الجذر الرقمي ---
def digital_root(price):
    try:
        s = str(int(price)).replace('.', '').replace('-', '').lstrip('0')
        if not s: return 0
        total = sum(int(d) for d in s)
        return 1 + (total - 1) % 9 if total != 0 else 0
    except:
        return 0

# --- اكتشاف فجوات القيمة العادلة FVG ---
def detect_fvg(df):
    if df is None or len(df) < 5:
        return "NEUTRAL", 0.0
    # فحص آخر الشموع المكتملة
    for i in range(len(df) - 4, 1, -1):
        # Bullish FVG
        if df['Low'].iloc[i] > df['High'].iloc[i + 2]:
            gap_price = (df['Low'].iloc[i] + df['High'].iloc[i + 2]) / 2
            return "BULLISH_FVG", gap_price
        # Bearish FVG
        if df['High'].iloc[i] < df['Low'].iloc[i + 2]:
            gap_price = (df['High'].iloc[i] + df['Low'].iloc[i + 2]) / 2
            return "BEARISH_FVG", gap_price
    return "NEUTRAL", 0.0

# --- جلب وتحليل الأخبار ---
def fetch_news():
    titles = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                titles.append(entry.title + " " + entry.get('summary', ""))
        except: continue
    return " | ".join(titles[:5])

def analyze_sentiment(text):
    if not text: return 0.5
    clean_text = re.sub(r'<[^>]+>', '', text)
    v_score = (vader.polarity_scores(clean_text)['compound'] + 1) / 2
    words = clean_text.lower().split()
    q_scores = [qtt_lexicon.get(w, 0.5) for w in words if w in qtt_lexicon]
    q_score = np.mean(q_scores) if q_scores else 0.5
    return np.clip(v_score * 0.6 + q_score * 0.4, 0.0, 1.0)

# --- بناء التقرير النهائي ---
def build_report(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(interval="15m", period="2d")
        
        if df.empty:
            return "❌ خطأ: لم يتم العثور على بيانات للرمز."

        current_price = df['Close'].iloc[-1]
        root = digital_root(current_price)
        fvg_status, fvg_price = detect_fvg(df)
        
        _, _, hist = macd(df['Close'])
        macd_val = hist.iloc[-1]
        trend = "BULLISH 🟢" if macd_val > 0 else "BEARISH 🔴"
        
        news_text = fetch_news()
        score = analyze_sentiment(news_text)
        sentiment_label = "إيجابي" if score > 0.6 else "سلبي" if score < 0.4 else "محايد"

        report = f"""
🚀 [تقرير ذكاء كوانتا الهجين v2026]
---------------------------------
الأصل: {symbol}
السعر الحالي: {current_price:.2f}
التوقيت: {datetime.now(pytz.timezone('Africa/Cairo')).strftime('%Y-%m-%d %I:%M %p')}

✅ التحليل الرقمي:
- الجذر الرقمي: {root} ({'دورة قوية' if root in [1,9] else 'دورة عادية'})

📊 التحليل الفني:
- اتجاه MACD (15m): {trend}
- حالة الفجوة (FVG): {fvg_status}
- سعر الفجوة المستهدف: {fvg_price:.2f}

📰 تحليل المشاعر (AI):
- الدرجة: {score:.2f}
- التصنيف: {sentiment_label}

---------------------------------
#كوانتا_فينتيك #تداول_ذكي #محمد_محرم
"""
        return report
    except Exception as e:
        return f"❌ خطأ تقني في النظام: {str(e)}"

if __name__ == "__main__":
    print(build_report(SYMBOL))
