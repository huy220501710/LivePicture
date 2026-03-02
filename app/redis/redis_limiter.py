from app.config import settings
from app.logger import logger
from redis import asyncio as aioredis

redis_connection = None


async def init_redis_limiter():
    """Initialize Redis-Limiter connection."""
    global redis_connection
    try:
        redis_connection = await aioredis.from_url(settings.REDIS_URL_LIMITER)
        logger.info("✅ Successfully connected to Redis Limiter")
    except Exception as e:
        logger.error(f"❌ Error connecting to Redis Limiter: {e}")
        redis_connection = None  # To avoid using a broken connection
        raise e
    return redis_connection


async def close_redis_limiter():
    """Close Redis-Limiter connection."""
    global redis_connection
    if redis_connection:
        try:
            await redis_connection.close()
            logger.info("🔴 Connection to Redis Limiter closed")
        except Exception as e:
            logger.error(f"Error closing Redis-Limiter: {e}")
