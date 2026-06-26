from __future__ import annotations
from celery_app import celery_app
from ingestion.news_fetcher import fetch_headlines
from ingestion.stock_fetcher import fetch_current_prices
from ingestion.reddit_fetcher import fetch_reddit_posts
from processing.sentiment import score_batch
from processing.normalizer import normalize_articles
from storage.postgres_client import save_scores, AsyncSessionLocal
from storage.redis_client import get_redis, cache_score, publish_update
from storage.mongo_client import save_raw_articles
import pandas as pd
import logging
import asyncio
import requests
import config

logger = logging.getLogger(__name__)

async def wait_for_databases_async() -> bool:
    """
    Checks readiness of PostgreSQL, Redis, and MongoDB asynchronously with retries.
    Returns True if all databases are ready, False otherwise.
    """
    # Check PostgreSQL
    postgres_ready = False
    for attempt in range(config.DB_RETRY_ATTEMPTS):
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
            logger.info("PostgreSQL is ready.")
            postgres_ready = True
            break
        except Exception as e:
            logger.warning(f"PostgreSQL not ready ({attempt+1}/{config.DB_RETRY_ATTEMPTS}): {e}")
            await asyncio.sleep(config.DB_RETRY_DELAY_SECONDS)
            
    # Check Redis
    redis_ready = False
    for attempt in range(config.DB_RETRY_ATTEMPTS):
        try:
            r = await get_redis()
            await r.ping()
            await r.aclose()
            logger.info("Redis is ready.")
            redis_ready = True
            break
        except Exception as e:
            logger.warning(f"Redis not ready ({attempt+1}/{config.DB_RETRY_ATTEMPTS}): {e}")
            await asyncio.sleep(config.DB_RETRY_DELAY_SECONDS)
            
    # Check MongoDB
    mongo_ready = False
    for attempt in range(config.DB_RETRY_ATTEMPTS):
        try:
            from storage.mongo_client import client as mongo_client
            await mongo_client.admin.command('ping')
            logger.info("MongoDB is ready.")
            mongo_ready = True
            break
        except Exception as e:
            logger.warning(f"MongoDB not ready ({attempt+1}/{config.DB_RETRY_ATTEMPTS}): {e}")
            await asyncio.sleep(config.DB_RETRY_DELAY_SECONDS)
            
    return postgres_ready and redis_ready and mongo_ready

async def run_pipeline_async(self) -> dict[str, str | int]:
    """Underlying asynchronous pipeline execution loop."""
    logger.info(f"Pipeline async execution started — attempt {self.request.retries + 1}")
    
    # Ensure databases are active
    databases_ok = await wait_for_databases_async()
    if not databases_ok:
        raise RuntimeError("Database connectivity check failed on pipeline startup.")

    try:
        # Step 1: Ingest from all sources with robust error capture
        try:
            news = fetch_headlines()
            logger.info(f"Fetched {len(news)} news articles")
        except requests.exceptions.Timeout:
            logger.warning("News API timed out — skipping this source")
            news = []
        except requests.exceptions.ConnectionError:
            logger.warning("News API connection failed — skipping this source")
            news = []
        except Exception as e:
            logger.error(f"Unexpected news fetch error: {type(e).__name__}: {e}")
            news = []

        try:
            reddit = fetch_reddit_posts()
            logger.info(f"Fetched {len(reddit)} Reddit posts")
        except requests.exceptions.Timeout:
            logger.warning("Reddit API timed out — skipping this source")
            reddit = []
        except requests.exceptions.ConnectionError:
            logger.warning("Reddit API connection failed — skipping this source")
            reddit = []
        except Exception as e:
            logger.error(f"Unexpected Reddit fetch error: {type(e).__name__}: {e}")
            reddit = []

        try:
            prices = fetch_current_prices()
            logger.info(f"Fetched prices for {len(prices)} symbols")
        except Exception as e:
            logger.error(f"Unexpected price fetch error: {type(e).__name__}: {e}")
            prices = []

        all_articles = news + reddit
        if not all_articles:
            logger.warning("No articles fetched — skipping pipeline run")
            return {"status": "skipped", "reason": "no articles"}

        # Step 2: Score articles and backup
        scored = score_batch(all_articles)
        await save_raw_articles(all_articles)

        # Step 3: Normalize and save structured scores to PostgreSQL
        df = normalize_articles(scored)
        await save_scores(df.to_dict("records"))

        # Step 4: Compute averages per symbol and publish updates to Redis
        price_df = pd.DataFrame(prices)
        if not price_df.empty:
            for symbol in price_df["symbol"].unique():
                sym_df = df[df["mentioned_tickers"].apply(lambda t: symbol in t if isinstance(t, list) else False)]
                if sym_df.empty:
                    continue
                
                avg_score = round(
                    sym_df["sentiment"].apply(
                        lambda x: x["compound"] if isinstance(x, dict) else 0
                    ).mean(), 4
                )
                
                # Fetch price info for this symbol
                symbol_price_data = price_df[price_df["symbol"] == symbol]
                price_info = symbol_price_data.to_dict("records")[0] if not symbol_price_data.empty else {}
                
                # Prepare payload matching frontend schema
                update_payload = {
                    "symbol": symbol,
                    "sentiment_score": avg_score,
                    "price": price_info.get("price", 0.0),
                    "change_pct": price_info.get("change_pct", 0.0),
                    "volume": price_info.get("volume", 0),
                    "timestamp": price_info.get("timestamp", "")
                }
                
                # Async cache & publish
                await cache_score(symbol, avg_score, price_data=price_info)
                await publish_update(update_payload)

        # Reset consecutive failures on success
        r = await get_redis()
        await r.set("pulseiq:pipeline:consecutive_failures", 0)
        await r.aclose()

        logger.info(f"Pipeline complete — {len(scored)} articles processed")
        return {"status": "success", "articles_processed": len(scored)}
        
    except Exception as e:
        # Increment consecutive failure count
        try:
            r = await get_redis()
            fail_count_bytes = await r.get("pulseiq:pipeline:consecutive_failures")
            fail_count = int(fail_count_bytes) if fail_count_bytes else 0
            fail_count += 1
            await r.set("pulseiq:pipeline:consecutive_failures", fail_count)
            await r.aclose()
        except Exception as redis_err:
            logger.error(f"Failed to record failures in Redis: {redis_err}")
            fail_count = 1

        logger.error(f"Pipeline failed (consecutive failures: {fail_count}): {e}")
        if fail_count >= 3:
            logger.critical(
                f"ALERT: Pipeline has failed {fail_count} times in a row. "
                f"Manual intervention may be required."
            )
        raise e

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="tasks.run_pipeline"
)
def run_pipeline(self):
    """Synchronous entrypoint Celery task spawning the asyncio event loop."""
    try:
        # Run async pipeline using asyncio loop
        return asyncio.run(run_pipeline_async(self))
    except Exception as exc:
        logger.error(f"Pipeline task failed: {exc}")
        raise self.retry(exc=exc)
