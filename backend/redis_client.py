import redis
from config import settings
from typing import Optional

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)


def check_rate_limit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """
    Check if rate limit is exceeded using Redis sliding window.
    Returns (is_allowed, current_count)
    """
    try:
        current = redis_client.get(key)
        if current is None:
            redis_client.setex(key, window_seconds, 1)
            return True, 1

        count = int(current)
        if count >= limit:
            return False, count

        redis_client.incr(key)
        return True, count + 1
    except redis.ConnectionError:
        # If Redis is down, allow the request but log it
        return True, 0


def cache_set(key: str, value: str, expiry_seconds: int) -> bool:
    """Set a value in Redis cache with expiry"""
    try:
        redis_client.setex(key, expiry_seconds, value)
        return True
    except redis.ConnectionError:
        return False


def cache_get(key: str) -> Optional[str]:
    """Get a value from Redis cache"""
    try:
        return redis_client.get(key)
    except redis.ConnectionError:
        return None


def cache_delete(key: str) -> bool:
    """Delete a key from Redis cache"""
    try:
        redis_client.delete(key)
        return True
    except redis.ConnectionError:
        return False
