import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from aiogram_dialog.api.exceptions import UnknownIntent, UnknownState
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter, TelegramServerError

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Middleware для обработки ошибок и отправки понятных сообщений пользователям
    """

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except (UnknownIntent, UnknownState) as e:
            logger.error(f"Dialog context error for user {self._get_user_id(event)}: {e}")
            await self._send_context_error_message(event, data)
            # Не пробрасываем исключение дальше, чтобы бот не упал
            return None
        except (TelegramBadRequest, TelegramRetryAfter, TelegramServerError) as e:
            logger.error(f"Telegram API error for user {self._get_user_id(event)}: {e}")
            await self._send_generic_error_message(event, data)
            # Не пробрасываем исключение дальше, чтобы бот не упал
            return None
        except Exception as e:
            logger.exception(f"Unexpected error for user {self._get_user_id(event)}: {e}")
            await self._send_generic_error_message(event, data)
            # Не пробрасываем исключение дальше, чтобы бот не упал
            return None

    def _get_user_id(self, event: Update) -> int:
        """Получить ID пользователя из события"""
        if event.message:
            return event.message.from_user.id
        elif event.callback_query:
            return event.callback_query.from_user.id
        elif event.inline_query:
            return event.inline_query.from_user.id
        else:
            return 0

    def _get_chat_id(self, event: Update) -> int:
        """Получить ID чата из события"""
        if event.message:
            return event.message.chat.id
        elif event.callback_query and event.callback_query.message:
            return event.callback_query.message.chat.id
        else:
            return 0

    async def _send_context_error_message(self, event: Update, data: Dict[str, Any]):
        """Отправить сообщение о потере контекста диалога"""
        bot = data.get("bot")
        chat_id = self._get_chat_id(event)
        
        if bot and chat_id:
            message = (
                "🚫 Упс! Что-то пошло не так, и данные не сохранились.\n\n"
                "Воспользуйся /menu, чтобы починить бота."
            )
            try:
                await bot.send_message(chat_id=chat_id, text=message)
                logger.info(f"Context error message sent to user {self._get_user_id(event)}")
            except Exception as send_error:
                logger.error(f"Failed to send context error message to {chat_id}: {send_error}")

    async def _send_generic_error_message(self, event: Update, data: Dict[str, Any]):
        """Отправить общее сообщение об ошибке"""
        bot = data.get("bot")
        chat_id = self._get_chat_id(event)
        
        if bot and chat_id:
            message = (
                "⚠️ Упс! Что-то пошло не так.\n\n"
                "Используй /menu для сброса."
            )
            try:
                await bot.send_message(chat_id=chat_id, text=message)
                logger.info(f"Generic error message sent to user {self._get_user_id(event)}")
            except Exception as send_error:
                logger.error(f"Failed to send generic error message to {chat_id}: {send_error}")
