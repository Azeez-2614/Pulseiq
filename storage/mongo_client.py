from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client["pulseiq"]
articles_collection = db["raw_articles"]


async def save_raw_articles(articles: list[dict]):
    """Asynchronously saves raw articles to MongoDB, avoiding duplicates via title index."""
    if not articles:
        return

    try:
        # Ensure a unique index on 'title' to improve upsert speed
        await articles_collection.create_index("title", unique=True)

        for article in articles:
            title = article.get("title")
            if not title:
                continue

            article_copy = article.copy()
            article_copy["saved_at"] = datetime.utcnow().isoformat()

            # Perform async upsert
            await articles_collection.update_one(
                {"title": title}, {"$set": article_copy}, upsert=True
            )
    except Exception as e:
        print(f"MongoDB save_raw_articles error: {e}")


async def get_recent_articles(limit: int = 50) -> list[dict]:
    """Asynchronously fetches recent raw articles from MongoDB."""
    cursor = articles_collection.find({}, {"_id": 0}).sort("saved_at", -1).limit(limit)
    return await cursor.to_list(length=limit)
