from sqlalchemy import text

from app.logger import logger

from .database import get_db


async def connect():
    try:
        async for db in get_db():
            await db.execute(text("SELECT VERSION();"))
            logger.info("✅ Successfully connected to MySQL")
    except Exception as e:
        logger.error(f"❌ Error connecting to MySQL: {e}")
        raise e
