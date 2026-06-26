import redis
import json
import sys
import os

# Add parent directory to path so config can be imported when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

CHANNEL = "pulseiq:live"

# Lazily initialized redis client
_r = None

def get_redis_client():
    global _r
    if _r is None:
        _r = redis.Redis.from_url(config.REDIS_URL)
    return _r

def cache_score(symbol: str, score: float, price_data: dict = None, ttl_seconds: int = 3600):
    """Caches average sentiment score and optional stock price details in Redis."""
    try:
        r = get_redis_client()
        key = f"pulseiq:score:{symbol.upper()}"
        payload = {"score": score, "symbol": symbol.upper()}
        if price_data:
            payload.update(price_data)
        r.setex(key, ttl_seconds, json.dumps(payload))
    except Exception as e:
        print(f"Redis cache_score error: {e}")

def get_cached_score(symbol: str):
    """Retrieves cached score for a symbol."""
    try:
        r = get_redis_client()
        val = r.get(f"pulseiq:score:{symbol.upper()}")
        return json.loads(val) if val else None
    except Exception as e:
        print(f"Redis get_cached_score error: {e}")
        return None

def publish_update(data: dict):
    """Publishes a live update dictionary to the Redis pub/sub channel."""
    try:
        r = get_redis_client()
        r.publish(CHANNEL, json.dumps(data))
    except Exception as e:
        print(f"Redis publish_update error: {e}")

def get_all_scores() -> dict:
    """Retrieves all cached scores from Redis."""
    try:
        r = get_redis_client()
        keys = r.keys("pulseiq:score:*")
        result = {}
        for key in keys:
            symbol = key.decode().split(":")[-1]
            val = r.get(key)
            if val:
                result[symbol] = json.loads(val)
        return result
    except Exception as e:
        print(f"Redis get_all_scores error: {e}")
        return {}

if __name__ == "__main__":
    print("Testing Redis client connection...")
    try:
        r = get_redis_client()
        r.ping()
        print("Connected to Redis successfully.")
        
        # Test caching
        cache_score("AAPL", 0.75, ttl_seconds=10)
        print("Cached AAPL score. Reading it back:")
        print(get_cached_score("AAPL"))
        
        # Test get_all_scores
        print("All cached scores:")
        print(get_all_scores())
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
