# =============================================
# HYBRID QUANTA ULTIMATE v2026 - Render Ready
# Developer: MUHAMMAD MUHARRAM
# =============================================

import os
import logging
from flask import Flask, jsonify
from datetime import datetime
import feedparser
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np
import requests
import pytz

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

PORT = int(os.getenv('PORT', 10000))
SYMBOL = os.getenv('SYMBOL', 'bitcoin')  # CoinGecko ID

vader = SentimentIntensityAnalyzer()

qtt_lexicon = {
    "growth": 0.92, "rally": 0.88, "bullish": 0.90, "uptrend": 0.85,
    "surge": 0.87, "etf": 0.82, "accumulation": 0.88, "institutional": 0.90,
    "whale": 0.88, "breakout": 0.89, "adoption": 0.84,
    "crash": 0.15, "drop": 0.30, "bearish": 0.25, "sell-off": 0.28,
    "ارتفاع": 0.88, "تجميع": 0.87, "اختراق": 0.90,
    "هبوط": 0.30, "تصحيح": 0.38, "ضعف": 0.35
}

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptopotato.com/feed/",
    "https://cointelegraph.com/rss"
]

def get_price():
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={SYMBOL}&vs_currencies=usd"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return round(data[SYMBOL]['usd'], 2)
    except Exception as e:
        logger.error(f"Price fetch error: {e}")
        return None

def cycle_completion(price: float) -> int:
    s = str(price).replace('.', '').replace('-', '').lstrip('0')
    if not s:
        return 0
    total = sum(int(d) for d in s)
    return 1 + (total - 1) % 9 if total != 0 else 0

def analyze_news():
    titles = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:3]:
                titles.append(e.title + " " + (e.summary or ""))
        except:
            pass
    text = " | ".join(titles) or "No news available"
    score = vader.polarity_scores(text)['compound']
    q_scores = [qtt_lexicon.get(w, 0.5) for w in text.lower().split() if w in qtt_lexicon]
    q = np.mean(q_scores) if q_scores else 0.5
    final = np.clip((score + 1)/2 * 0.6 + q * 0.4, 0, 1)
    return {"score": round(final, 2), "text_preview": text[:200]}

def run_analysis():
    price = get_price()
    if not price:
        return {"error": "Unable to fetch price - check network or CoinGecko API"}
    
    cycle = cycle_completion(price)
    news = analyze_news()
    
    return {
        "timestamp": datetime.now(pytz.timezone('Africa/Cairo')).isoformat(),
        "symbol": SYMBOL.upper(),
        "price_usd": price,
        "cycle_completion": cycle,
        "sentiment": news
    }

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hybrid Quanta Bot</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f4f8; }
            h1 { color: #4a90e2; }
            button { padding: 15px 40px; font-size: 1.2em; background: #4a90e2; color: white; border: none; border-radius: 8px; cursor: pointer; }
            button:hover { background: #357abd; }
            #result { margin-top: 30px; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); white-space: pre-wrap; text-align: left; max-width: 800px; margin: 30px auto; }
            #loader { border: 5px solid #f3f3f3; border-top: 5px solid #4a90e2; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 20px auto; display: none; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <h1>🚀 Hybrid Quanta Bot</h1>
        <p>Cloud Edition | Developer: MUHAMMAD MUHARRAM</p>
        
        <button onclick="getAnalysis()">Analyze Market Now</button>
        <div id="loader"></div>
        <div id="result"></div>
        
        <script>
            async function getAnalysis() {
                document.getElementById('loader').style.display = 'block';
                document.getElementById('result').style.display = 'none';
                
                try {
                    const response = await fetch('/api/run');
                    const data = await response.json();
                    document.getElementById('result').innerHTML = '<h3>Analysis Result:</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    document.getElementById('result').style.display = 'block';
                } catch (error) {
                    document.getElementById('result').innerHTML = '<h3>Error:</h3><pre>' + error + '</pre>';
                    document.getElementById('result').style.display = 'block';
                }
                document.getElementById('loader').style.display = 'none';
            }
        </script>
    </body>
    </html>
    """

@app.route('/api/run')
def api():
    result = run_analysis()
    return jsonify(result)

if __name__ == '__main__':
    logger.info("Hybrid Quanta started on Render")
    app.run(host='0.0.0.0', port=PORT, debug=False)