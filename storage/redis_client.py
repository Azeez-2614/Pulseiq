from __future__ import annotations
import redis.asyncio as aioredis
import json
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHANNEL = "pulseiq:live"


async def get_redis():
    return aioredis.from_url(REDIS_URL, decode_responses=True)


async def cache_score(
    symbol: str, score: float, price_data: dict = None, ttl_seconds: int = 300
):
    """Caches average sentiment score and optional stock price details in Redis."""
    r = await get_redis()
    payload = {"score": score, "symbol": symbol.upper()}
    if price_data:
        payload.update(price_data)
    await r.setex(f"pulseiq:score:{symbol.upper()}", ttl_seconds, json.dumps(payload))
    await r.aclose()


async def get_cached_score(symbol: str) -> dict | None:
    """Retrieves cached score for a symbol."""
    r = await get_redis()
    val = await r.get(f"pulseiq:score:{symbol.upper()}")
    await r.aclose()
    return json.loads(val) if val else None


async def publish_update(data: dict):
    """Publishes a live update dictionary to the Redis pub/sub channel."""
    r = await get_redis()
    await r.publish(CHANNEL, json.dumps(data))
    await r.aclose()


async def get_all_scores() -> dict:
    """Retrieves all cached scores from Redis."""
    r = await get_redis()
    keys = await r.keys("pulseiq:score:*")
    result = {}
    for key in keys:
        symbol = key.split(":")[-1]
        val = await r.get(key)
        if val:
            result[symbol] = json.loads(val)
    await r.aclose()
    return result
