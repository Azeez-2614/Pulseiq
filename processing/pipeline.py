from ingestion.news_fetcher import fetch_headlines
from ingestion.stock_fetcher import fetch_current_prices
from ingestion.reddit_fetcher import fetch_reddit_posts
from processing.sentiment import score_batch
from processing.normalizer import normalize_articles
from storage.postgres_client import save_scores, init_db
from storage.redis_client import cache_score, publish_update
from storage.mongo_client import save_raw_articles
import pandas as pd
import logging
import time
import config
import redis as redis_lib
import pymongo

def wait_for_databases():
    """Attempts to initialize DB services, retrying if they aren't ready yet."""
    logging.info("Checking database readiness...")
    
    # Initialize Postgres tables
    postgres_ready = False
    for attempt in range(5):
        if init_db():
            postgres_ready = True
            break
        logging.warning(f"PostgreSQL not ready. Retrying in 3 seconds... ({attempt+1}/5)")
        time.sleep(3)
        
    if not postgres_ready:
        logging.error("Failed to initialize PostgreSQL. Continuing but database errors may occur.")

    # Redis check
    for attempt in range(5):
        try:
            r = redis_lib.Redis.from_url(config.REDIS_URL)
            r.ping()
            logging.info("Redis is ready.")
            break
        except Exception:
            logging.warning(f"Redis not ready. Retrying... ({attempt+1}/5)")
            time.sleep(3)

    # MongoDB check
    for attempt in range(5):
        try:
            client = pymongo.MongoClient(config.MONGO_URL, serverSelectionTimeoutMS=3000)
            client.server_info()
            logging.info("MongoDB is ready.")
            break
        except Exception:
            logging.warning(f"MongoDB not ready. Retrying... ({attempt+1}/5)")
            time.sleep(3)

def pipeline_job():
    logging.info("Starting pipeline execution...")
    
    try:
        # Step 1: Ingest from all sources
        logging.info("Fetching articles and prices...")
        try:
            news = fetch_headlines()
            logging.info(f"Fetched {len(news)} news headlines")
        except Exception as e:
            logging.warning(f"News fetch failed: {e}")
            news = []

        try:
            reddit = fetch_reddit_posts()
            logging.info(f"Fetched {len(reddit)} Reddit posts")
        except Exception as e:
            logging.warning(f"Reddit fetch failed: {e}")
            reddit = []

        try:
            prices = fetch_current_prices()
            logging.info(f"Fetched prices for {len(prices)} symbols")
        except Exception as e:
            logging.warning(f"Price fetch failed: {e}")
            prices = []

        # Step 2: Score articles and back up raw data
        all_articles = news + reddit
        if not all_articles:
            logging.warning("No articles fetched in this run. Skipping processing.")
            return

        logging.info("Scoring sentiment on fetched content...")
        scored = score_batch(all_articles)
        
        # Save raw articles to MongoDB
        logging.info("Backing up raw articles to MongoDB...")
        save_raw_articles(all_articles)

        # Normalize articles into structured schema using Pandas
        logging.info("Normalizing and cleaning article records...")
        df = normalize_articles(scored)
        
        # Save structured scores to PostgreSQL
        logging.info("Saving scores to PostgreSQL...")
        save_scores(df.to_dict("records"))

        # Step 3: Compute averages per ticker and cache/publish to Redis
        logging.info("Updating Redis cache and publishing live feed...")
        price_df = pd.DataFrame(prices)
        
        for symbol in config.WATCHLIST:
            # Filter articles mentioning this ticker
            sym_df = df[df["mentioned_tickers"].apply(lambda t: symbol in t if isinstance(t, list) else False)]
            
            # Default sentiment is 0 (neutral) if no articles mention it in the current run
            avg_score = 0.0
            if not sym_df.empty:
                avg_score = round(sym_df["sentiment"].apply(
                    lambda x: x["compound"] if isinstance(x, dict) else 0.0
                ).mean(), 4)
                
            # Get price info
            symbol_price_data = price_df[price_df["symbol"] == symbol]
            price_info = symbol_price_data.to_dict("records")[0] if not symbol_price_data.empty else {}

            # Cache average sentiment and price data in Redis
            cache_score(symbol, avg_score, price_data=price_info)
            
            # Prepare update payload
            update_payload = {
                "symbol": symbol,
                "sentiment_score": avg_score,
                "price": price_info.get("price", 0.0),
                "change_pct": price_info.get("change_pct", 0.0),
                "volume": price_info.get("volume", 0),
                "timestamp": price_info.get("timestamp", "")
            }
            
            # Publish to Redis channel
            publish_update(update_payload)
            
        logging.info("Pipeline execution completed successfully.")
        
    except Exception as e:
        logging.exception(f"Error in pipeline job: {e}")
