import asyncio
import aio_pika

from app.config import settings
from app.logger import logger

rabbitmq_connection = None
rabbitmq_channel = None


async def init_rabbitmq():
    """Initialize RabbitMQ connection with retry logic."""
    global rabbitmq_connection, rabbitmq_channel
    max_retries = 5
    retry_delay = 2  # секунды
    
    for attempt in range(max_retries):
        try:
            rabbitmq_connection = await asyncio.wait_for(
                aio_pika.connect_robust(settings.RABBITMQ_URL_BROKER),
                timeout=10.0
            )
            rabbitmq_channel = await rabbitmq_connection.channel()  # Создаем канал
            logger.info("✅ Successfully connected to RabbitMQ")
            return rabbitmq_connection, rabbitmq_channel
        except Exception as e:
            rabbitmq_connection = None
            rabbitmq_channel = None
            if attempt < max_retries - 1:
                logger.warning(f"⚠️ Попытка подключения к RabbitMQ {attempt + 1}/{max_retries} не удалась: {e}. Повтор через {retry_delay}с...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"❌ Error connecting to RabbitMQ after {max_retries} attempts: {e}")
                # Не raise - позволяем приложению запуститься без RabbitMQ
                return None, None


async def close_rabbitmq():
    """Закрытие подключения к RabbitMQ."""
    global rabbitmq_connection, rabbitmq_channel
    if rabbitmq_channel:
        try:
            await rabbitmq_channel.close()
            logger.info("🔴 Канал RabbitMQ закрыт")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ channel: {e}")

    if rabbitmq_connection:
        try:
            await rabbitmq_connection.close()
            logger.info("🔴 Соединение с RabbitMQ закрыто")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")


async def get_rabbitmq_connection_and_channel():
    """Получить текущее соединение и канал RabbitMQ."""
    global rabbitmq_connection, rabbitmq_channel
    if rabbitmq_connection is None or rabbitmq_channel is None:
        raise Exception("RabbitMQ не подключен. Пожалуйста, инициализируйте соединение.")
    return rabbitmq_connection, rabbitmq_channel
