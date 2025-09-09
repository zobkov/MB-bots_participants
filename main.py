import asyncio
import logging
import logging.config
import sys
import os

from app.bot.bot import main

# Добавим путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "default",
            "filename": "bot.log",
            "encoding": "utf-8",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
}

if __name__ == "__main__":
    logging.config.dictConfig(logging_config)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.exception(f"Critical error: {e}")
        sys.exit(1)
