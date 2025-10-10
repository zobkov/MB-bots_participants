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
from app.bot.middlewares.logging_context import LoggingContextMiddleware
from app.infrastructure.database import DatabaseManager, RedisManager
from app.infrastructure.google_sheets import GoogleSheetsManager

# Импорт всех диалогов
from app.bot.dialogs.start import start_dialog
from app.bot.dialogs.main_menu import main_menu_dialog
from app.bot.dialogs.timetable import timetable_dialog
from app.bot.dialogs.navigation import navigation_dialog
from app.bot.dialogs.faq import faq_dialog
from app.bot.dialogs.registration import registration_dialog

# Импорт системы уведомлений
from app.infrastructure.telegram_logging import start_log_worker

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


async def setup_database_and_redis(config) -> tuple[DatabaseManager, RedisManager, GoogleSheetsManager]:
    """Настройка базы данных, Redis для кеширования и Google Sheets"""
    # Инициализация DatabaseManager
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    # Инициализация RedisManager 
    redis_manager = RedisManager(config.redis)
    await redis_manager.init()
    
    # Инициализация GoogleSheetsManager
    google_sheets_manager = GoogleSheetsManager(
        config.google_sheets.credentials_path,
        config.google_sheets.spreadsheet_id
    )
    
    # Проверяем подключение к Google Sheets (опционально)
    try:
        await google_sheets_manager.init()
        logger.info("Google Sheets manager initialized successfully")
    except Exception as e:
        logger.warning(f"Google Sheets initialization failed (will retry on sync): {e}")
    
    # Синхронизация Redis с базой данных
    db_counts = await db_manager.get_debate_registrations_count()
    await redis_manager.sync_with_database(db_counts)
    
    logger.info("Database and Redis initialized and synced")
    return db_manager, redis_manager, google_sheets_manager


class DatabaseMiddleware:
    """Middleware для добавления менеджеров базы данных, Redis и Google Sheets в контекст"""
    
    def __init__(self, db_manager: DatabaseManager, redis_manager: RedisManager, google_sheets_manager: GoogleSheetsManager):
        self.db_manager = db_manager
        self.redis_manager = redis_manager
        self.google_sheets_manager = google_sheets_manager
    
    async def __call__(self, handler, event, data):
        data["db_manager"] = self.db_manager
        data["redis_manager"] = self.redis_manager
        data["google_sheets_manager"] = self.google_sheets_manager
        return await handler(event, data)


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
    
    # Настройка базы данных, Redis и Google Sheets
    db_manager, redis_manager, google_sheets_manager = await setup_database_and_redis(config)
    
    # Создание диспетчера
    dp = Dispatcher(storage=storage)
    
    # Добавление данных в диспетчер
    dp["config"] = config
    dp["bot"] = bot
    
    # Подключение middleware
    dp.update.middleware(LoggingContextMiddleware())  # Добавляем первым для контекста логов
    dp.update.middleware(ConfigMiddleware(config))
    dp.update.middleware(DatabaseMiddleware(db_manager, redis_manager, google_sheets_manager))  # Добавляем DB middleware
    dp.update.middleware(ErrorHandlerMiddleware())
    
    # Запуск воркера уведомлений для админов
    log_worker_task = None
    if config.logging.admin_ids:
        log_worker_task = await start_log_worker(bot, config.logging.admin_ids)
    
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
        
        # Останавливаем воркер уведомлений
        if log_worker_task and not log_worker_task.done():
            log_worker_task.cancel()
            try:
                await log_worker_task
            except asyncio.CancelledError:
                pass
        
        # Закрываем подключения к базе данных и Redis
        await db_manager.close()
        await redis_manager.close()
        
        await bot.session.close()
        if storage.redis:
            await storage.redis.aclose()


if __name__ == "__main__":
    # Эта часть выполняется только если файл запускается напрямую
    # В обычном случае бот запускается через main.py с настроенным логированием
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    asyncio.run(main())
