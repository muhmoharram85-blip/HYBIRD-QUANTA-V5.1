import yfinance as yf
import pandas as pd
import numpy as np
import feedparser
from datetime import datetime
import pytz
import requests
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- بيانات تلجرام الخاصة بك ---
# التوكن من صورتك (مؤمن)
TELEGRAM_TOKEN = "7543883447:AAH0p1_u0A23YvL8_h7p66FkX5o2WvV9Z_Y" 
# ضع هنا رقم الآيدي الذي حصلت عليه من IDBot
CHAT_ID = "ضع_الرقم_هنا" 

SYMBOL = "BTC-USD"
vader = SentimentIntensityAnalyzer()

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except: return False

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

def build_report(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(interval="15m", period="2d")
        if df.empty: return "❌ فشل جلب البيانات من ياهو"

        current_price = df['Close'].iloc[-1]
        root = digital_root(current_price)
        _, _, hist = macd(df['Close'])
        trend = "صعودي 🟢" if hist.iloc[-1] > 0 else "هبوطي 🔴"
        
        report = f"""
🚀 <b>[كوانتا v5.1 - تلجرام]</b>
---------------------------------
<b>الأصل:</b> {symbol}
<b>السعر:</b> {current_price:.2f}
<b>الجذر الرقمي:</b> {root}
<b>الاتجاه:</b> {trend}
<b>التوقيت:</b> {datetime.now(pytz.timezone('Africa/Cairo')).strftime('%I:%M %p')}
---------------------------------
#كوانتا_فينتيك
"""
        return report
    except Exception as e:
        return f"❌ خطأ تقني: {str(e)}"

if __name__ == "__main__":
    final_report = build_report(SYMBOL)
    success = send_to_telegram(final_report)
    if success:
        print("✅ تم إرسال التقرير لتلجرام بنجاح!")
    else:
        print("❌ فشل الإرسال، تأكد من Chat ID")
