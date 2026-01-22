import yfinance as yf
import pandas as pd
import numpy as np
import feedparser
from datetime import datetime
import pytz
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
import requests

# --- إعدادات تلجرام (ضع بياناتك هنا) ---
# انسخ التوكن من الصورة التي أرفقتها وضعه بين القوسين
TELEGRAM_TOKEN = "7543883447:AAH..." 
# ضع الآيدي الخاص بك هنا (الذي حصلت عليه من IDBot)
CHAT_ID = "ضع_هنا_الرقم" 

SYMBOL = "BTC-USD"
vader = SentimentIntensityAnalyzer()

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error: {e}")

def macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def digital_root(price):
    try:
        s = str(int(price)).replace('.', '').replace('-', '').lstrip('0')
        total = sum(int(d) for d in s)
        return 1 + (total - 1) % 9 if total != 0 else 0
    except: return 0

def fetch_news():
    titles = []
    feed = feedparser.parse("https://www.coindesk.com/arc/outboundfeeds/rss/")
    for entry in feed.entries[:3]:
        titles.append(entry.title)
    return " | ".join(titles)

def build_report(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(interval="15m", period="2d")
        if df.empty: return "❌ لا توجد بيانات"

        current_price = df['Close'].iloc[-1]
        root = digital_root(current_price)
        _, _, hist = macd(df['Close'])
        trend = "صعودي 🟢" if hist.iloc[-1] > 0 else "هبوطي 🔴"
        
        report = f"""
<b>🚀 [تقرير كوانتا المباشر]</b>
---------------------------------
<b>الأصل:</b> {symbol}
<b>السعر:</b> {current_price:.2f}
<b>الجذر الرقمي:</b> {root}
<b>الاتجاه الحالي:</b> {trend}
<b>التوقيت:</b> {datetime.now(pytz.timezone('Africa/Cairo')).strftime('%Y-%m-%d %I:%M %p')}
---------------------------------
#كوانتا_فينتيك
"""
        return report
    except Exception as e:
        return f"❌ خطأ: {str(e)}"

if __name__ == "__main__":
    final_report = build_report(SYMBOL)
    send_to_telegram(final_report)
    print("✅ تم إرسال التقرير إلى تلجرام")
