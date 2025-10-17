import logging
from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram_dialog.api import exceptions as dialog_exceptions

logger = logging.getLogger(__name__)


GENERIC_ERROR_MESSAGE = "Произошла ошибка. Используй /menu для перезапуска.\n\nТех. поддержка: @zobko"
DIALOG_CONTEXT_EXPIRED_MESSAGE = "Данные устарели. Используй /menu, чтобы продолжить."

DIALOG_CONTEXT_EXCEPTIONS = tuple(
    exc
    for exc in (
        getattr(dialog_exceptions, "ContextNotFound", None),
        getattr(dialog_exceptions, "UnknownIntent", None),
    )
    if exc
)


class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware для обработки ошибок"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as error:
            if self._is_dialog_context_issue(error):
                logger.info(f"Dialog context issue: {error}")
                await self._notify_user(
                    event,
                    data,
                    DIALOG_CONTEXT_EXPIRED_MESSAGE,
                    alert_text=DIALOG_CONTEXT_EXPIRED_MESSAGE
                )
                return None
            logger.exception(f"Error in handler: {error}")
            await self._notify_user(
                event,
                data,
                GENERIC_ERROR_MESSAGE,
                alert_text="Произошла ошибка"
            )
            return None
    
    async def _notify_user(
        self,
        event: TelegramObject,
        data: Dict[str, Any],
        message_text: str,
        *,
        alert_text: Optional[str] = None,
        send_to_chat: bool = True,
    ) -> None:
        """Send error notification back to the user in a safe manner."""
        try:
            if isinstance(event, CallbackQuery):
                if alert_text:
                    await event.answer(alert_text, show_alert=True)
                else:
                    await event.answer()
                if send_to_chat and event.message:
                    await event.message.answer(message_text)
            elif isinstance(event, Message):
                await event.answer(message_text)
            else:
                await self._send_via_bot(data, message_text)
                return
            if send_to_chat and isinstance(event, CallbackQuery) and not event.message:
                await self._send_via_bot(data, message_text)
        except Exception as send_error:
            logger.error(f"Failed to send error message to user: {send_error}")

    @staticmethod
    def _is_dialog_context_issue(error: Exception) -> bool:
        """Return True when error indicates expired or missing dialog context."""
        if DIALOG_CONTEXT_EXCEPTIONS and isinstance(error, DIALOG_CONTEXT_EXCEPTIONS):
            return True
        message = str(error).lower()
        return (
            "context not found" in message
            or "no context" in message
            or "intent is not found" in message
        )

    @staticmethod
    async def _send_via_bot(data: Dict[str, Any], message_text: str) -> None:
        """Fallback sender that posts a message using bot reference from middleware data."""
        bot = data.get("bot")
        if bot is None:
            return
        chat = data.get("event_chat")
        user = data.get("event_from_user")
        target_id = None
        if chat:
            target_id = chat.id
        elif user:
            target_id = user.id
        if target_id is None:
            return
        try:
            await bot.send_message(target_id, message_text)
        except Exception as send_error:
            logger.error(f"Fallback send failed: {send_error}")
