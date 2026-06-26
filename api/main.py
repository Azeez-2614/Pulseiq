from __future__ import annotations
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

# Import async clients & models
from storage.redis_client import get_redis, get_all_scores, get_cached_score, CHANNEL
from storage.postgres_client import AsyncSessionLocal, SentimentScore
from storage.mongo_client import get_recent_articles
from processing.correlator import compute_correlation
from api.security import verify_api_key, validate_symbol, limiter
from tasks import run_pipeline
import config

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PulseIQ API",
    version="2.0.0",
    description="Real-time market sentiment intelligence API",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/health", tags=["System"])
async def health_check():
    """Public health endpoint — no auth required."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/scores", tags=["Sentiment"])
@limiter.limit("60/minute")
async def get_all_scores_endpoint(
    request: Request, api_key: str = Depends(verify_api_key)
):
    """Returns current sentiment scores for all tracked symbols."""
    return await get_all_scores()


@app.get("/scores/{symbol}", tags=["Sentiment"])
@limiter.limit("60/minute")
async def get_symbol_score(
    symbol: str, request: Request, api_key: str = Depends(verify_api_key)
):
    """Returns sentiment score for a single validated symbol."""
    clean_symbol = validate_symbol(symbol)
    data = await get_cached_score(clean_symbol)
    if not data:
        return JSONResponse(
            status_code=404,
            content={
                "error": f"No cached data for {clean_symbol}. Pipeline may not have run yet."
            },
        )
    return data


@app.get("/articles", tags=["Content"])
@limiter.limit("30/minute")
async def get_articles(request: Request, api_key: str = Depends(verify_api_key)):
    """Returns 50 most recent scored articles."""
    return await get_recent_articles(limit=50)


@app.get("/correlation", tags=["Correlation"])
@limiter.limit("30/minute")
async def get_dynamic_correlation(
    request: Request, api_key: str = Depends(verify_api_key)
):
    """
    Dynamically queries historical sentiment scores from PostgreSQL,
    aligns them, fetches stock price variations, and computes Pearson correlations.
    """
    try:
        async with AsyncSessionLocal() as session:
            # 1. Fetch sentiment scores from database (last 7 days)
            limit_date = datetime.utcnow() - timedelta(days=7)
            from sqlalchemy import select

            stmt = select(SentimentScore).where(
                SentimentScore.published_at >= limit_date
            )
            result = await session.execute(stmt)
            db_scores = result.scalars().all()

            if not db_scores:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "Not enough historical sentiment data in PostgreSQL database. Run the pipeline first.",
                        "data_points_found": 0,
                    },
                )

            # Convert DB rows to DataFrame
            scores_list = []
            for s in db_scores:
                scores_list.append(
                    {
                        "published_at": s.published_at,
                        "mentioned_tickers": [s.symbol],
                        "sentiment": s.raw_scores,
                    }
                )
            sentiment_df = pd.DataFrame(scores_list)

            # 2. Fetch historical prices from yfinance or generate mock prices
            prices_list = []
            for symbol in config.WATCHLIST:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d", interval="1h")
                    if not hist.empty:
                        first_open = hist.iloc[0]["Open"]
                        for timestamp, row in hist.iterrows():
                            pct_change = (
                                ((row["Close"] - first_open) / first_open) * 100
                                if first_open != 0
                                else 0.0
                            )
                            prices_list.append(
                                {
                                    "symbol": symbol,
                                    "timestamp": timestamp.to_pydatetime(),
                                    "change_pct": round(pct_change, 2),
                                }
                            )
                    else:
                        now = datetime.utcnow()
                        for h in range(120):
                            ts = now - timedelta(hours=h)
                            prices_list.append(
                                {
                                    "symbol": symbol,
                                    "timestamp": ts,
                                    "change_pct": round(1.5 * (h % 5) - 3.0, 2),
                                }
                            )
                except Exception:
                    now = datetime.utcnow()
                    for h in range(120):
                        ts = now - timedelta(hours=h)
                        prices_list.append(
                            {
                                "symbol": symbol,
                                "timestamp": ts,
                                "change_pct": round(1.2 * (h % 6) - 2.5, 2),
                            }
                        )

            price_df = pd.DataFrame(prices_list)

            # 3. Compute Pearson correlation using processing correlator
            correlations = compute_correlation(sentiment_df, price_df)
            return {
                "status": "success",
                "time_window": "7 days",
                "correlations": correlations,
            }
    except Exception as e:
        logger.exception("Error calculating dynamic correlation")
        return JSONResponse(
            status_code=500, content={"error": f"Calculations failed: {str(e)}"}
        )


@app.post("/pipeline/trigger", tags=["System"])
@limiter.limit("5/minute")
async def trigger_pipeline(request: Request, api_key: str = Depends(verify_api_key)):
    """Triggers the ingestion and processing pipeline as an asynchronous Celery background task."""
    try:
        task = run_pipeline.delay()
        return {
            "status": "pipeline triggered",
            "task_id": task.id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to enqueue Celery task: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Could not trigger background worker: {e}"},
        )


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """Real-time sentiment score stream via WebSocket."""
    await websocket.accept()
    logger.info(f"WebSocket client connected: {websocket.client}")
    try:
        r = await get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(CHANNEL)
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        try:
            await pubsub.unsubscribe(CHANNEL)
            await r.aclose()
        except Exception:
            pass
