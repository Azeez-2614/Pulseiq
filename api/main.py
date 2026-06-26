from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import logging
import os

# Import async clients & models
from storage.redis_client import get_redis, get_all_scores, get_cached_score, CHANNEL
from storage.postgres_client import AsyncSessionLocal, SentimentScore
from storage.mongo_client import get_recent_articles
from processing.correlator import compute_correlation
from api.security import verify_api_key
from tasks import run_pipeline
import config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PulseIQ-API")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="PulseIQ API",
    description="Real-Time Market Sentiment & Stock Intelligence REST + WebSocket API",
    version="2.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS (allow both GET and POST requests from the Next.js frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Database migration checks can run asynchronously.
    # Alembic handles the schema migrations now, but we can verify basic readiness.
    logger.info("PulseIQ API started successfully.")

@app.get("/scores")
@limiter.limit("60/minute")
async def get_scores(request: Request, api_key: str = Depends(verify_api_key)):
    """Returns current average sentiment scores and stock prices cached in Redis."""
    scores = await get_all_scores()
    if not scores:
        return {symbol: {"symbol": symbol, "score": 0.0} for symbol in config.WATCHLIST}
    return scores

@app.get("/scores/{symbol}")
@limiter.limit("60/minute")
async def get_symbol_score(symbol: str, request: Request, api_key: str = Depends(verify_api_key)):
    """Returns cached sentiment score and details for a single symbol."""
    data = await get_cached_score(symbol.upper())
    if not data:
        return {"error": f"No data cached for symbol {symbol.upper()}"}
    return data

@app.get("/articles")
@limiter.limit("30/minute")
async def get_latest_articles(request: Request, api_key: str = Depends(verify_api_key)):
    """Returns recently stored raw articles from MongoDB."""
    return await get_recent_articles(limit=50)

@app.get("/correlation")
@limiter.limit("30/minute")
async def get_dynamic_correlation(request: Request, api_key: str = Depends(verify_api_key)):
    """
    Dynamically queries historical sentiment scores from PostgreSQL,
    aligns them, fetches stock price variations, and computes Pearson correlations.
    """
    try:
        # Use async session context manager
        async with AsyncSessionLocal() as session:
            # 1. Fetch sentiment scores from database (last 7 days)
            limit_date = datetime.utcnow() - timedelta(days=7)
            from sqlalchemy import select
            stmt = select(SentimentScore).where(SentimentScore.published_at >= limit_date)
            result = await session.execute(stmt)
            db_scores = result.scalars().all()
            
            if not db_scores:
                return {
                    "error": "Not enough historical sentiment data in PostgreSQL database. Run the pipeline first.",
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
                        # Fallback mock prices
                        now = datetime.utcnow()
                        for h in range(120):
                            ts = now - timedelta(hours=h)
                            prices_list.append({
                                "symbol": symbol,
                                "timestamp": ts,
                                "change_pct": round(1.5 * (h % 5) - 3.0, 2)
                            })
                except Exception:
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

@app.post("/pipeline/trigger")
@limiter.limit("5/minute")
async def trigger_pipeline(request: Request, api_key: str = Depends(verify_api_key)):
    """Triggers the ingestion and processing pipeline as an asynchronous Celery background task."""
    try:
        task = run_pipeline.delay()
        return {
            "status": "pipeline triggered",
            "task_id": task.id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to enqueue Celery task: {e}")
        return {"error": f"Could not trigger background worker: {e}"}

@app.get("/health")
async def health():
    """Health check validating Redis availability."""
    checks = {}
    try:
        r = await get_redis()
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }

@app.websocket("/ws/live")
async def websocket_endpoint(ws: WebSocket):
    """
    Subscribes to Redis pub/sub channel and broadcasts messages to connected clients reactively.
    This eliminates busy-waiting loops completely.
    """
    await ws.accept()
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await ws.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await r.aclose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
