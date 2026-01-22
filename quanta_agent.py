# =============================================
# HYBRID QUANTA ULTIMATE v2026 - CLOUD READY
# المطور: محمد محرم
# Optimized for Render.com & GitHub
# =============================================

import os
import pandas as pd
import numpy as np
import feedparser
from datetime import datetime
import pytz
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
import logging
from typing import Tuple, Optional, Dict
from flask import Flask, jsonify, render_template_string
import ccxt  # Alternative to MT5 for cloud deployment
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

# --- Configuration from Environment Variables ---
SYMBOL = os.getenv('SYMBOL', 'BTC/USDT')
EXCHANGE_NAME = os.getenv('EXCHANGE', 'binance')
API_KEY = os.getenv('EXCHANGE_API_KEY', '')
API_SECRET = os.getenv('EXCHANGE_API_SECRET', '')
PORT = int(os.getenv('PORT', 10000))

# Timeframes
TIMEFRAMES = {
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "1w": "1w"
}

# Initialize sentiment analyzer
vader = SentimentIntensityAnalyzer()

# Quantum Trading Theory Lexicon
qtt_lexicon = {
    "growth": 0.92, "rally": 0.88, "bullish": 0.90, "uptrend": 0.85,
    "surge": 0.87, "etf": 0.82, "accumulation": 0.88, "institutional": 0.90,
    "whale": 0.88, "breakout": 0.89, "moon": 0.85, "adoption": 0.84,
    "crash": 0.15, "drop": 0.30, "bearish": 0.25, "sell-off": 0.28,
    "dump": 0.20, "fear": 0.32, "regulation": 0.40, "ban": 0.18,
    "ارتفاع": 0.88, "تجميع": 0.87, "اختراق": 0.90,
    "هبوط": 0.30, "تصحيح": 0.38, "ضعف": 0.35
}

# RSS Feed sources
RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptopotato.com/feed/",
    "https://cointelegraph.com/rss"
]

# Initialize Exchange
def init_exchange():
    """Initialize CCXT exchange (cloud-compatible)"""
    try:
        exchange_class = getattr(ccxt, EXCHANGE_NAME)
        exchange = exchange_class({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        logger.info(f"✅ Connected to {EXCHANGE_NAME}")
        return exchange
    except Exception as e:
        logger.error(f"❌ Exchange initialization failed: {e}")
        return None

exchange = init_exchange()


# ==========================
# MACD Indicator
# ==========================
def macd(series: pd.Series, fast: int = 12, slow: int = 26, 
         signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD indicator"""
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def macd_trend(df: pd.DataFrame) -> str:
    """Determine trend based on MACD"""
    try:
        _, _, hist = macd(df['close'])
        last = hist.iloc[-1]
        prev = hist.iloc[-2]
        
        if last > 0 and last > prev:
            return "STRONG_BULLISH"
        elif last > 0:
            return "BULLISH"
        elif last < 0 and last < prev:
            return "STRONG_BEARISH"
        elif last < 0:
            return "BEARISH"
        return "NEUTRAL"
    except Exception as e:
        logger.error(f"MACD error: {e}")
        return "NEUTRAL"


# ==========================
# RSI Indicator
# ==========================
def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def rsi_signal(df: pd.DataFrame, period: int = 14) -> str:
    """Get RSI signal"""
    try:
        rsi = calculate_rsi(df['close'], period)
        current_rsi = rsi.iloc[-1]
        
        if current_rsi > 70:
            return "OVERBOUGHT"
        elif current_rsi < 30:
            return "OVERSOLD"
        elif current_rsi > 50:
            return "BULLISH"
        else:
            return "BEARISH"
    except Exception as e:
        logger.error(f"RSI error: {e}")
        return "NEUTRAL"


# ==========================
# Digital Root
# ==========================
def digital_root(price: float) -> int:
    """Calculate digital root"""
    s = str(price).replace('.', '').replace('-', '').lstrip('0')
    if not s:
        return 0
    total = sum(int(d) for d in s)
    return 1 + (total - 1) % 9 if total != 0 else 0


def interpret_digital_root(root: int) -> str:
    """Interpret digital root"""
    interpretations = {
        1: "New beginnings", 2: "Balance", 3: "Growth",
        4: "Stability", 5: "Change", 6: "Harmony",
        7: "Analysis", 8: "Power", 9: "Completion"
    }
    return interpretations.get(root, "Unknown")


# ==========================
# Fair Value Gap Detection
# ==========================
def detect_fvg(df: pd.DataFrame) -> Tuple[str, float]:
    """Detect Fair Value Gaps"""
    try:
        if len(df) < 10:
            return "NO_DATA", 0.0
        
        for i in range(len(df) - 3, 1, -1):
            if df['low'].iloc[i] > df['high'].iloc[i + 2]:
                gap_price = (df['low'].iloc[i] + df['high'].iloc[i + 2]) / 2
                return "BULLISH_FVG", gap_price
            
            if df['high'].iloc[i] < df['low'].iloc[i + 2]:
                gap_price = (df['high'].iloc[i] + df['low'].iloc[i + 2]) / 2
                return "BEARISH_FVG", gap_price
        
        return "NEUTRAL", 0.0
    except Exception as e:
        logger.error(f"FVG error: {e}")
        return "ERROR", 0.0


# ==========================
# Market Volume Reaction
# ==========================
def market_reaction(df: pd.DataFrame) -> str:
    """Analyze volume reaction"""
    try:
        if 'volume' not in df or len(df) < 15:
            return "NO_DATA"
        
        recent_vol = df['volume'].iloc[-5:].mean()
        past_vol = df['volume'].iloc[-15:-5].mean()
        
        if past_vol == 0:
            return "WEAK"
        
        ratio = recent_vol / past_vol
        
        if ratio > 1.8:
            return "VERY_STRONG"
        elif ratio > 1.4:
            return "STRONG"
        elif ratio > 1.0:
            return "MODERATE"
        else:
            return "WEAK"
    except Exception as e:
        logger.error(f"Volume reaction error: {e}")
        return "ERROR"


# ==========================
# News & Sentiment
# ==========================
def fetch_news(max_articles: int = 5) -> str:
    """Fetch crypto news"""
    titles = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                titles.append(f"{title} {summary}")
        except Exception as e:
            logger.warning(f"News fetch error from {url}: {e}")
            continue
    
    return " | ".join(titles[:max_articles]) if titles else "No news available"


def analyze_sentiment(text: str) -> float:
    """Analyze sentiment"""
    if not text or text == "No news available":
        return 0.5
    
    clean_text = re.sub(r'<[^>]+>', '', text)
    v_score = (vader.polarity_scores(clean_text)['compound'] + 1) / 2
    
    words = clean_text.lower().split()
    q_scores = [qtt_lexicon.get(w, 0.5) for w in words if w in qtt_lexicon]
    q_score = np.mean(q_scores) if q_scores else 0.5
    
    return np.clip(v_score * 0.6 + q_score * 0.4, 0.0, 1.0)


def sentiment_label(score: float) -> str:
    """Convert sentiment to label"""
    if score >= 0.7:
        return "VERY_BULLISH"
    elif score >= 0.6:
        return "BULLISH"
    elif score >= 0.4:
        return "NEUTRAL"
    elif score >= 0.3:
        return "BEARISH"
    else:
        return "VERY_BEARISH"


# ==========================
# Get Market Data (CCXT)
# ==========================
def get_ohlcv(symbol: str, timeframe: str, limit: int = 100) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data from exchange"""
    try:
        if exchange is None:
            return None
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"OHLCV fetch error: {e}")
        return None


def get_current_price(symbol: str) -> Optional[float]:
    """Get current price"""
    try:
        if exchange is None:
            return None
        ticker = exchange.fetch_ticker(symbol)
        return ticker['last']
    except Exception as e:
        logger.error(f"Price fetch error: {e}")
        return None


# ==========================
# Analysis Report
# ==========================
def build_analysis(symbol: str = SYMBOL, timeframe: str = "15m") -> Dict:
    """Build analysis report"""
    try:
        # Get current price
        price = get_current_price(symbol)
        if price is None:
            return {"error": "Unable to fetch price"}
        
        # Get OHLCV data
        df = get_ohlcv(symbol, timeframe)
        if df is None:
            return {"error": "Unable to fetch market data"}
        
        # Technical analysis
        root = digital_root(price)
        root_meaning = interpret_digital_root(root)
        
        macd_signal = macd_trend(df)
        rsi_status = rsi_signal(df)
        fvg_status, fvg_price = detect_fvg(df)
        reaction = market_reaction(df)
        
        # Multi-timeframe
        mtf_trends = {}
        for tf_name in ["15m", "1h", "4h", "1d"]:
            tf_df = get_ohlcv(symbol, tf_name, limit=50)
            if tf_df is not None:
                mtf_trends[tf_name] = macd_trend(tf_df)
        
        # Sentiment
        news_text = fetch_news()
        sentiment_score = analyze_sentiment(news_text)
        sentiment = sentiment_label(sentiment_score)
        
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "digital_root": {
                "value": root,
                "meaning": root_meaning
            },
            "technical": {
                "macd": macd_signal,
                "rsi": rsi_status,
                "fvg": fvg_status,
                "fvg_price": round(fvg_price, 2) if fvg_price > 0 else None,
                "volume_reaction": reaction
            },
            "multi_timeframe": mtf_trends,
            "sentiment": {
                "score": round(sentiment_score, 2),
                "label": sentiment,
                "news_preview": news_text[:300]
            }
        }
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return {"error": str(e)}


# ==========================
# Flask Routes
# ==========================
@app.route('/')
def home():
    """Home page with HTML interface"""
    html = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hybrid Quanta Bot</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 40px;
            }
            h1 {
                text-align: center;
                color: #667eea;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            .subtitle {
                text-align: center;
                color: #666;
                margin-bottom: 30px;
            }
            .status {
                background: #f0f0f0;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            }
            .btn {
                background: #667eea;
                color: white;
                border: none;
                padding: 15px 40px;
                border-radius: 10px;
                font-size: 1.1em;
                cursor: pointer;
                display: block;
                margin: 20px auto;
                transition: all 0.3s;
            }
            .btn:hover {
                background: #764ba2;
                transform: scale(1.05);
            }
            .result {
                background: #f9f9f9;
                padding: 20px;
                border-radius: 10px;
                margin-top: 20px;
                display: none;
            }
            .result pre {
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .loader {
                border: 5px solid #f3f3f3;
                border-top: 5px solid #667eea;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
                display: none;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Hybrid Quanta Bot</h1>
            <p class="subtitle">المطور: محمد محرم | Cloud Edition</p>
            
            <div class="status">
                <strong>الحالة:</strong> <span id="status">جاهز للعمل</span>
            </div>
            
            <button class="btn" onclick="getAnalysis()">
                📊 تحليل السوق الآن
            </button>
            
            <div class="loader" id="loader"></div>
            
            <div class="result" id="result">
                <h3>نتيجة التحليل:</h3>
                <pre id="output"></pre>
            </div>
        </div>
        
        <script>
            async function getAnalysis() {
                document.getElementById('loader').style.display = 'block';
                document.getElementById('result').style.display = 'none';
                document.getElementById('status').textContent = 'جاري التحليل...';
                
                try {
                    const response = await fetch('/api/analysis');
                    const data = await response.json();
                    
                    document.getElementById('output').textContent = 
                        JSON.stringify(data, null, 2);
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('status').textContent = 'تم التحليل بنجاح ✅';
                } catch (error) {
                    document.getElementById('output').textContent = 
                        'خطأ: ' + error.message;
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('status').textContent = 'فشل التحليل ❌';
                }
                
                document.getElementById('loader').style.display = 'none';
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route('/api/analysis')
def api_analysis():
    """API endpoint for analysis"""
    symbol = SYMBOL
    timeframe = "15m"
    result = build_analysis(symbol, timeframe)
    return jsonify(result)


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(pytz.UTC).isoformat(),
        "exchange": EXCHANGE_NAME,
        "symbol": SYMBOL
    })


# ==========================
# Main
# ==========================
if __name__ == "__main__":
    logger.info("🚀 Starting Hybrid Quanta Bot...")
    logger.info(f"📊 Trading: {SYMBOL} on {EXCHANGE_NAME}")
    logger.info(f"🌐 Server running on port {PORT}")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)