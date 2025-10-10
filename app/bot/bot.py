import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram_dialog import setup_dialogs
from redis.asyncio import Redis

from config.config import load_config
from app.bot.handlers.commands import router as commands_router
from app.bot.middlewares.error_handler import ErrorHandlerMiddleware
from app.bot.middlewares.config import ConfigMiddleware

# Импорт всех диалогов
from app.bot.dialogs.start import start_dialog
from app.bot.dialogs.main_menu import main_menu_dialog
from app.bot.dialogs.timetable import timetable_dialog
from app.bot.dialogs.navigation import navigation_dialog
from app.bot.dialogs.faq import faq_dialog
from app.bot.dialogs.registration import registration_dialog

logger = logging.getLogger(__name__)


async def setup_redis_storage(config) -> RedisStorage:
    """Настройка Redis storage для FSM"""
    if config.redis.password:
        redis_url = f"redis://:{config.redis.password}@{config.redis.host}:{config.redis.port}/0"
    else:
        redis_url = f"redis://{config.redis.host}:{config.redis.port}/0"
    
    redis_client = Redis.from_url(redis_url, decode_responses=False)
    
    # Проверяем подключение
    await redis_client.ping()
    logger.info("Successfully connected to Redis")
    
    storage = RedisStorage(
        redis=redis_client,
        key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
        state_ttl=86400,  # 1 день
        data_ttl=86400
    )
    
    return storage


async def main():
    """Основная функция запуска бота"""
    logger.info("Loading configuration...")
    config = load_config()
    
    logger.info("Starting bot...")
    
    # Создание бота
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Настройка Redis storage
    storage = await setup_redis_storage(config)
    
    # Создание диспетчера
    dp = Dispatcher(storage=storage)
    
    # Добавление данных в диспетчер
    dp["config"] = config
    dp["bot"] = bot
    
    # Подключение middleware
    dp.update.middleware(ConfigMiddleware(config))
    dp.update.middleware(ErrorHandlerMiddleware())
    
    # Подключение роутеров
    dp.include_router(commands_router)
    
    # Подключение диалогов
    dp.include_routers(
        start_dialog,
        main_menu_dialog,
        timetable_dialog,
        navigation_dialog,
        faq_dialog,
        registration_dialog
    )
    
    # Настройка диалогов
    setup_dialogs(dp)
    
    logger.info("Bot started successfully!")
    
    try:
        # Запуск polling
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Error during polling: {e}")
    finally:
        # Закрытие соединений
        logger.info("Shutting down...")
        await bot.session.close()
        if storage.redis:
            await storage.redis.aclose()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    asyncio.run(main())
