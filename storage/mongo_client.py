import pymongo
import sys
import os

# Add parent directory to path so config can be imported when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

_mongo_client = None

def get_mongo_db():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = pymongo.MongoClient(config.MONGO_URL, serverSelectionTimeoutMS=2000)
    return _mongo_client["pulseiq"]

def save_raw_articles(articles: list[dict]):
    """
    Saves a list of raw articles to MongoDB as backup.
    Uses upsert based on title to avoid inserting duplicates.
    """
    if not articles:
        return
        
    try:
        db = get_mongo_db()
        collection = db["raw_articles"]
        
        # Ensure a unique index on 'title' to improve upsert speed
        collection.create_index("title", unique=True)
        
        for article in articles:
            title = article.get("title")
            if not title:
                continue
                
            # Perform upsert
            collection.update_one(
                {"title": title},
                {"$set": article},
                upsert=True
            )
            
    except Exception as e:
        print(f"MongoDB save_raw_articles error: {e}")

if __name__ == "__main__":
    print("Testing MongoDB client connection...")
    try:
        db = get_mongo_db()
        # Trigger connection check
        db.list_collection_names()
        print("Connected to MongoDB successfully.")
        
        # Insert a sample raw article
        sample = {
            "title": "Raw article test title",
            "description": "Raw article body details.",
            "source": "Reddit",
            "url": "https://reddit.com/r/test",
            "published_at": "2026-06-26T00:00:00Z"
        }
        save_raw_articles([sample])
        print("Saved raw article successfully.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
