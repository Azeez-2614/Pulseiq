from celery_app import celery_app
from ingestion.news_fetcher import fetch_headlines
from ingestion.stock_fetcher import fetch_current_prices
from ingestion.reddit_fetcher import fetch_reddit_posts
from processing.sentiment import score_batch
from processing.normalizer import normalize_articles
from storage.postgres_client import save_scores
from storage.redis_client import cache_score, publish_update
from storage.mongo_client import save_raw_articles
import pandas as pd
import logging
import asyncio

logger = logging.getLogger(__name__)

async def run_pipeline_async(self):
    """Underlying asynchronous pipeline execution loop."""
    logger.info(f"Pipeline async execution started — attempt {self.request.retries + 1}")

    try:
        # Step 1: Ingest from all sources
        try:
            news = fetch_headlines()
            logger.info(f"Fetched {len(news)} news articles")
        except Exception as e:
            logger.warning(f"News fetch failed: {e}")
            news = []

        try:
            reddit = fetch_reddit_posts()
            logger.info(f"Fetched {len(reddit)} Reddit posts")
        except Exception as e:
            logger.warning(f"Reddit fetch failed: {e}")
            reddit = []

        try:
            prices = fetch_current_prices()
            logger.info(f"Fetched prices for {len(prices)} symbols")
        except Exception as e:
            logger.warning(f"Price fetch failed: {e}")
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

        logger.info(f"Pipeline complete — {len(scored)} articles processed")
        return {"status": "success", "articles_processed": len(scored)}
        
    except Exception as e:
        logger.error(f"Internal error during async pipeline run: {e}")
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
