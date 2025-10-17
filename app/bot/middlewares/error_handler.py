import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)


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
        except Exception as e:
            logger.exception(f"Error in handler: {e}")
            
            # Отправляем пользователю сообщение об ошибке
            error_message = "Произошла ошибка. Используй /menu для перезапуска.\n\nТех. поддержка: @zobko"
            
            try:
                if isinstance(event, CallbackQuery):
                    # Для callback query отправляем alert и сообщение в чат
                    await event.answer("Произошла ошибка", show_alert=True)
                    if event.message:
                        await event.message.answer(error_message)
                elif isinstance(event, Message):
                    # Для обычного сообщения отвечаем напрямую
                    await event.answer(error_message)
                elif hasattr(event, 'answer'):
                    # Для других типов событий
                    await event.answer(error_message)
            except Exception as send_error:
                logger.error(f"Failed to send error message to user: {send_error}")
            
            return None
