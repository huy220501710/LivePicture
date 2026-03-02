from app.config import settings
from app.logger import logger
from redis import asyncio as aioredis

redis_connection = None


async def init_redis_revoke_tokens():
    """Initialize Redis connection for storing revoked tokens."""
    global redis_connection
    try:
        redis_connection = await aioredis.from_url(
            settings.REDIS_URL_REVOKE_TOKENS, decode_responses=True
        )
        logger.info("✅ Successfully connected to Redis REVOKE TOKENS")
    except Exception as e:
        logger.error(f"❌ Error connecting to Redis REVOKE TOKENS: {e}")
        redis_connection = None  # To avoid using a broken connection
        raise e
    return redis_connection


async def close_redis_revoke_tokens():
    """Close Redis connection for storing revoked tokens."""
    global redis_connection
    if redis_connection:
        try:
            await redis_connection.close()
            logger.info("🔴 Connection to Redis REVOKE TOKENS closed")
        except Exception as e:
            logger.error(f"Error closing Redis for revoked tokens: {e}")


async def revoke_token(token: str, ex: int) -> None:
    """Adds token to blocklist (revocation)."""
    if not redis_connection:
        logger.error("Attempt to add token to blocklist without initialized Redis.")
        raise Exception("Redis is not initialized. Call init_redis_revoke_tokens() first.")

    try:
        await redis_connection.set(name=token, value="1", ex=ex * 60)
    except Exception as e:
        logger.error(f"Error adding token {token} to blocklist: {e}")


async def is_token_revoked(token: str) -> bool:
    """Check if token is in blocklist."""
    if not redis_connection:
        logger.error("Attempt to verify token without initialized Redis.")
        raise Exception("Redis is not initialized. Call init_redis_revoke_tokens() first.")

    try:
        revoked = await redis_connection.exists(token) > 0
        return revoked
    except Exception as e:
        logger.error(f"Error checking token {token} in blocklist: {e}")
        return False
