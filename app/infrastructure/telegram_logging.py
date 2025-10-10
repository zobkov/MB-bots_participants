"""
Система отправки логов администраторам.
Отправляет ERROR/CRITICAL немедленно, WARNING - при превышении лимита.
"""

import asyncio
import logging
import time
import contextvars
from collections import deque
from typing import Any, Dict, List

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter


# Контекст логов из middleware
log_ctx: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar("log_ctx", default={})

# Очередь для отправки логов в Telegram
LOG_QUEUE: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()


class ContextFilter(logging.Filter):
    """Фильтр для добавления контекста из middleware в записи логов."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        ctx = log_ctx.get({})
        # Безопасно добавляем поля (будут "-" если нет значений)
        record.user_id = ctx.get("user_id", "-")
        record.chat_id = ctx.get("chat_id", "-")
        record.update_type = ctx.get("update_type", "-")
        record.handler = ctx.get("handler", "-")
        return True


async def log_worker(bot: Bot, admin_ids: List[int]):
    """
    Асинхронный воркер для отправки логов админам.
    Не блокирует основной цикл обработки и защищен от rate-limit.
    """
    logger = logging.getLogger(__name__)
    
    while True:
        try:
            message_data = await LOG_QUEUE.get()
            text = message_data["text"]
            level = message_data["level"]
            
            # Определяем эмодзи для уровня
            emoji = {
                "WARNING": "⚠️",
                "ERROR": "❌", 
                "CRITICAL": "🚨"
            }.get(level, "📝")
            
            # Форматируем сообщение
            formatted_text = f"{emoji} {level}\n{text}"
            
            # Обрезаем до лимита Telegram
            if len(formatted_text) > 4096:
                formatted_text = formatted_text[:4000] + "\n...(обрезано)"
            
            # Отправляем всем админам
            for admin_id in admin_ids:
                try:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=formatted_text,
                        disable_web_page_preview=True,
                        parse_mode=None  # Отключаем парсинг для безопасности
                    )
                except TelegramRetryAfter as e:
                    # Ждем и повторяем при rate-limit
                    await asyncio.sleep(e.retry_after)
                    try:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=formatted_text,
                            disable_web_page_preview=True,
                            parse_mode=None
                        )
                    except Exception as retry_error:
                        logger.error(f"Failed to send log to admin {admin_id} after retry: {retry_error}")
                        
                except TelegramBadRequest as e:
                    # Логируем проблемы с отправкой (например, заблокированный бот)
                    logger.warning(f"Cannot send log to admin {admin_id}: {e}")
                    
                except Exception as e:
                    # Логируем прочие ошибки без рекурсии
                    logger.error(f"Unexpected error sending log to admin {admin_id}: {e}")
                    
        except Exception as e:
            # Критические ошибки в самом воркере
            print(f"[log_worker] Critical error: {e}", flush=True)
            
        finally:
            LOG_QUEUE.task_done()


class TelegramLogHandler(logging.Handler):
    """
    Handler для отправки логов в Telegram.
    - ERROR/CRITICAL отправляются немедленно
    - WARNING отправляются при превышении 5 за минуту
    """
    
    def __init__(self, level=logging.WARNING):
        super().__init__(level)
        self._warn_times = deque()      # WARNING за последние 60 секунд
        self._last_warn_summary = 0.0   # Время последней сводки WARNING
        self._warn_threshold = 5        # Лимит WARNING за минуту
        self._warn_window = 60          # Окно времени в секундах
        
    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Пропускаем логи самого воркера отправки чтобы избежать рекурсии
            if record.name == __name__:
                return
                
            # Форматируем сообщение
            msg = self.format(record)
            now = time.monotonic()
            
            if record.levelno >= logging.ERROR:
                # ERROR/CRITICAL отправляем немедленно
                try:
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(
                        LOG_QUEUE.put_nowait,
                        {
                            "text": msg,
                            "level": record.levelname,
                            "timestamp": now
                        }
                    )
                except RuntimeError:
                    # Если нет running loop (например, в тестах)
                    pass
                    
            elif record.levelno == logging.WARNING:
                # Агрегируем WARNING за окно времени
                self._warn_times.append(now)
                
                # Удаляем старые записи (> 60 секунд)
                while self._warn_times and now - self._warn_times[0] > self._warn_window:
                    self._warn_times.popleft()
                
                # Если превысили лимит и прошло достаточно времени с последней сводки
                if (len(self._warn_times) > self._warn_threshold and 
                    (now - self._last_warn_summary) >= self._warn_window):
                    
                    self._last_warn_summary = now
                    summary_msg = (
                        f"WARNING накопились: {len(self._warn_times)} предупреждений за последнюю минуту.\n"
                        f"Последнее: {msg}\n"
                        f"Проверьте логи для подробностей."
                    )
                    
                    try:
                        loop = asyncio.get_running_loop()
                        loop.call_soon_threadsafe(
                            LOG_QUEUE.put_nowait,
                            {
                                "text": summary_msg,
                                "level": "WARNING",
                                "timestamp": now
                            }
                        )
                    except RuntimeError:
                        pass
                        
        except Exception:
            # Не даем handler'у убить процесс
            pass


async def start_log_worker(bot: Bot, admin_ids: List[int]) -> asyncio.Task:
    """Запуск воркера отправки логов."""
    if not admin_ids:
        logger = logging.getLogger(__name__)
        logger.warning("No admin IDs configured, log notifications disabled")
        return None
        
    task = asyncio.create_task(log_worker(bot, admin_ids))
    logger = logging.getLogger(__name__)
    logger.info(f"Started log worker for {len(admin_ids)} admin(s): {admin_ids}")
    return task


def setup_telegram_logging(admin_ids: List[int]) -> TelegramLogHandler:
    """
    Настройка Telegram handler для логирования.
    Возвращает handler, который нужно добавить к корневому логгеру.
    """
    if not admin_ids:
        return None
        
    # Создаем Telegram handler
    telegram_handler = TelegramLogHandler(level=logging.WARNING)
    
    # Устанавливаем формат сообщений для Telegram
    telegram_formatter = logging.Formatter(
        "%(name)s | %(message)s\n"
        "user=%(user_id)s chat=%(chat_id)s upd=%(update_type)s handler=%(handler)s"
    )
    telegram_handler.setFormatter(telegram_formatter)
    
    # Добавляем фильтр контекста
    telegram_handler.addFilter(ContextFilter())
    
    return telegram_handler


def get_log_context() -> contextvars.ContextVar:
    """Получить переменную контекста логов для использования в middleware."""
    return log_ctx