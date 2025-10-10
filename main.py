import asyncio
import logging
import sys
import os

from app.bot.bot import main
from app.infrastructure.logging import setup_logging, cleanup_old_logs
from config.config import load_config

# Добавим путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    # Загружаем конфигурацию
    config = load_config()
    
    # Настройка логирования с параметрами из конфигурации
    setup_logging(
        log_level=config.logging.level,
        log_dir=config.logging.log_dir,
        console_output=config.logging.console_output,
        file_prefix=config.logging.file_prefix
    )
    
    # Очищаем старые логи
    deleted_logs = cleanup_old_logs(
        log_dir=config.logging.log_dir, 
        keep_days=config.logging.retention_days
    )
    if deleted_logs > 0:
        logging.info(f"Cleaned up {deleted_logs} old log files")
    
    logging.info("Starting Telegram Bot...")
    logging.info(f"Log level: {config.logging.level}")
    logging.info(f"Log directory: {config.logging.log_dir}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.exception(f"Critical error: {e}")
        sys.exit(1)
