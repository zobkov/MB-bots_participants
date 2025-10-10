"""
Middleware для добавления контекста в логи и логирования необработанных исключений.
"""

import logging
from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery

from app.infrastructure.telegram_logging import get_log_context


class LoggingContextMiddleware(BaseMiddleware):
    """
    Middleware для:
    1. Добавления контекста апдейта в логи (user_id, chat_id, тип апдейта)
    2. Логирования необработанных исключений
    """
    
    def __init__(self):
        self.logger = logging.getLogger("bot.middleware")
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        
        # Извлекаем контекст из события
        context = self._extract_context(event, handler)
        
        # Устанавливаем контекст для логов
        log_ctx = get_log_context()
        token = log_ctx.set(context)
        
        try:
            # Логируем начало обработки для отладки
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(
                    f"Processing {context['update_type']} from user {context['user_id']} "
                    f"in chat {context['chat_id']}"
                )
            
            # Вызываем обработчик
            result = await handler(event, data)
            
            return result
            
        except Exception as e:
            # Логируем необработанное исключение с полным контекстом
            self.logger.exception(
                f"Unhandled exception in {context['handler']}: {e}"
            )
            # Пробрасываем исключение дальше, чтобы aiogram мог его обработать
            raise
            
        finally:
            # Сбрасываем контекст
            log_ctx.reset(token)
    
    def _extract_context(self, event: TelegramObject, handler: Callable) -> Dict[str, Any]:
        """Извлекает контекст из события Telegram."""
        
        # Базовые значения
        context = {
            "user_id": None,
            "chat_id": None,
            "update_type": type(event).__name__,
            "handler": getattr(handler, "__name__", str(handler))
        }
        
        # Извлекаем user_id
        if hasattr(event, "from_user") and event.from_user:
            context["user_id"] = event.from_user.id
        elif hasattr(event, "message") and event.message and event.message.from_user:
            context["user_id"] = event.message.from_user.id
        
        # Извлекаем chat_id
        if hasattr(event, "chat") and event.chat:
            context["chat_id"] = event.chat.id
        elif hasattr(event, "message") and event.message and event.message.chat:
            context["chat_id"] = event.message.chat.id
        
        # Для Update объектов копаем глубже
        if isinstance(event, Update):
            if event.message:
                if event.message.from_user:
                    context["user_id"] = event.message.from_user.id
                if event.message.chat:
                    context["chat_id"] = event.message.chat.id
            elif event.callback_query:
                if event.callback_query.from_user:
                    context["user_id"] = event.callback_query.from_user.id
                if event.callback_query.message and event.callback_query.message.chat:
                    context["chat_id"] = event.callback_query.message.chat.id
        
        return context