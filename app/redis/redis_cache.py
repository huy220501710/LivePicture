from app.config import settings
from app.logger import logger
from redis import asyncio as aioredis

redis_connection = None


async def init_redis_cache():
    """Initialize Redis cache connection."""
    global redis_connection
    try:
        redis_connection = await aioredis.from_url(settings.REDIS_URL_CACHE)
        logger.info("✅ Successfully connected to Redis CACHE")
    except Exception as e:
        logger.error(f"❌ Error connecting to Redis CACHE: {e}")
        redis_connection = None  # To avoid using a broken connection
        raise e
    return redis_connection


async def close_redis_cache():
    """Закрытие подключения к Redis-кэшу."""
    global redis_connection
    if redis_connection:
        try:
            await redis_connection.close()
            logger.info("🔴 Соединение с Redis CACHE закрыто")
        except Exception as e:
            logger.error(f"Error closing Redis cache: {e}")
