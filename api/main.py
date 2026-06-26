from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import asyncio
import json
import logging
import sys

# Import local layers
from storage.redis_client import get_redis_client, get_all_scores, get_cached_score, CHANNEL
from storage.postgres_client import get_session, SentimentScore
from processing.correlator import compute_correlation
import config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PulseIQ-API")

app = FastAPI(
    title="PulseIQ API",
    description="Real-Time Market Sentiment & Stock Intelligence REST + WebSocket API",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST Endpoints

@app.get("/health")
def health():
    """Service health check."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/scores")
def get_scores():
    """Returns current sentiment scores for all tracked symbols cached in Redis."""
    scores = get_all_scores()
    # If cache is empty, return initial empty scores dictionary
    if not scores:
        return {symbol: {"symbol": symbol, "score": 0.0} for symbol in config.WATCHLIST}
    return scores

@app.get("/scores/{symbol}")
def get_symbol_score(symbol: str):
    """Returns cached sentiment score for a single symbol."""
    data = get_cached_score(symbol.upper())
    if not data:
        return {"error": f"No data cached for symbol {symbol.upper()}"}
    return data

@app.get("/correlation")
def get_dynamic_correlation():
    """
    Dynamically queries historical sentiment scores from PostgreSQL and 
    historical stock price changes from yfinance, aligns them, and computes
    their Pearson correlation.
    """
    try:
        session = get_session()
    except Exception as e:
        return {"error": f"Could not connect to PostgreSQL database: {str(e)}"}

    try:
        # 1. Fetch sentiment scores from database (last 7 days)
        limit_date = datetime.utcnow() - timedelta(days=7)
        db_scores = session.query(SentimentScore).filter(
            SentimentScore.published_at >= limit_date
        ).all()
        
        if not db_scores:
            return {
                "error": "Not enough historical sentiment data in PostgreSQL database. Run the scheduler pipeline first.",
                "data_points_found": 0
            }
            
        # Convert DB rows to DataFrame
        scores_list = []
        for s in db_scores:
            scores_list.append({
                "published_at": s.published_at,
                "mentioned_tickers": [s.symbol],
                "sentiment": s.raw_scores
            })
        sentiment_df = pd.DataFrame(scores_list)

        # 2. Fetch historical prices from yfinance or generate mock prices
        prices_list = []
        for symbol in config.WATCHLIST:
            try:
                # Fetch hourly stock data for the last 5 days
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d", interval="1h")
                if not hist.empty:
                    # Calculate pct change relative to the first open in hist
                    first_open = hist.iloc[0]["Open"]
                    for timestamp, row in hist.iterrows():
                        pct_change = ((row["Close"] - first_open) / first_open) * 100 if first_open != 0 else 0.0
                        prices_list.append({
                            "symbol": symbol,
                            "timestamp": timestamp.to_pydatetime(),
                            "change_pct": round(pct_change, 2)
                        })
                else:
                    # If yfinance yields empty (closed markets/rate limit), add mock prices to correlate
                    now = datetime.utcnow()
                    for h in range(120):  # 5 days hourly
                        ts = now - timedelta(hours=h)
                        prices_list.append({
                            "symbol": symbol,
                            "timestamp": ts,
                            "change_pct": round(1.5 * (h % 5) - 3.0, 2) # pseudo-random deterministic delta
                        })
            except Exception:
                # Fallback to mock prices on yfinance exception
                now = datetime.utcnow()
                for h in range(120):
                    ts = now - timedelta(hours=h)
                    prices_list.append({
                        "symbol": symbol,
                        "timestamp": ts,
                        "change_pct": round(1.2 * (h % 6) - 2.5, 2)
                    })

        price_df = pd.DataFrame(prices_list)

        # 3. Compute Pearson correlation using processing correlator
        correlations = compute_correlation(sentiment_df, price_df)
        return {
            "status": "success",
            "time_window": "7 days",
            "correlations": correlations
        }

    except Exception as e:
        logger.exception("Error calculating dynamic correlation")
        return {"error": f"Calculations failed: {str(e)}"}
    finally:
        session.close()

@app.get("/articles")
def get_latest_articles(limit: int = 10):
    """
    Returns the latest scored articles from PostgreSQL.
    If PostgreSQL has no articles or fails to connect, it falls back to generating mock articles on-the-fly.
    """
    try:
        session = get_session()
        db_scores = session.query(SentimentScore).order_by(
            SentimentScore.published_at.desc()
        ).limit(limit).all()
        
        if db_scores:
            articles = []
            for s in db_scores:
                articles.append({
                    "title": s.headline,
                    "source": s.source,
                    "published_at": s.published_at.isoformat() if s.published_at else "",
                    "symbol": s.symbol,
                    "sentiment": s.raw_scores or {"compound": 0.0, "label": "neutral"}
                })
            return articles
    except Exception as e:
        logger.error(f"PostgreSQL query in /articles failed: {e}")
        # Fallback to mock generation if DB fails

    # Return mock articles as fallback
    try:
        from ingestion.news_fetcher import generate_mock_headlines
        from processing.sentiment import score_batch
        from processing.normalizer import find_mentioned_tickers
        
        raw_mocks = generate_mock_headlines()
        scored_mocks = score_batch(raw_mocks)
        
        articles = []
        for a in scored_mocks[:limit]:
            mentioned = find_mentioned_tickers(a["title"])
            sym = mentioned[0] if mentioned else "GENERAL"
            articles.append({
                "title": a["title"],
                "source": a["source"],
                "published_at": a["published_at"],
                "symbol": sym,
                "sentiment": a["sentiment"]
            })
        return articles
    except Exception as mock_err:
        logger.error(f"Mock generation failed in /articles: {mock_err}")
        return []

# WebSocket Broadcast Layer

class WebSocketBroadcaster:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active: {len(self.active_connections)}")

    async def broadcast_from_redis(self):
        """Listens to Redis pub/sub channel and broadcasts messages to all connected WebSockets."""
        try:
            r = get_redis_client()
            pubsub = r.pubsub()
            pubsub.subscribe(CHANNEL)
            logger.info(f"Subscribed to Redis pub/sub channel '{CHANNEL}' for WebSocket broadcasting.")
        except Exception as e:
            logger.error(f"Failed to subscribe to Redis for WebSockets: {e}")
            return

        while True:
            try:
                # Non-blocking check for messages (timeout of 0.5s to allow yielding control)
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                if message and self.active_connections:
                    data_str = message["data"].decode("utf-8")
                    # Broadcast to all active clients
                    # Make a copy of connections to avoid modification errors during loop
                    clients = list(self.active_connections)
                    for client in clients:
                        try:
                            await client.send_text(data_str)
                        except Exception:
                            # Disconnected or failed to send, remove client
                            self.disconnect(client)
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Error in WebSocket broadcast loop: {e}")
                await asyncio.sleep(2)

broadcaster = WebSocketBroadcaster()

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        # Keep connection open until client disconnects
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        broadcaster.disconnect(websocket)

# Start background pubsub broadcaster when FastAPI starts up
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcaster.broadcast_from_redis())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
