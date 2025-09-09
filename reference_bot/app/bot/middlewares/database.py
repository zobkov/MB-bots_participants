from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
import logging

from app.infrastructure.database.database.db import DB

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для работы с базой данных"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработчик middleware
        
        Args:
            handler: Следующий обработчик в цепочке
            event: Событие Telegram
            data: Данные для передачи обработчику
            
        Returns:
            Результат выполнения обработчика
        """
        # Получаем пулы соединений с БД из диспетчера
        dispatcher = data.get("_dispatcher") or data.get("dispatcher") or data.get("dp")
        
        # Попробуем получить из различных источников
        db_pool = None
        db_applications_pool = None
        bot = None
        config = None
        
        if dispatcher:
            db_pool = dispatcher.get("db")
            db_applications_pool = dispatcher.get("db_applications")
            bot = dispatcher.get("bot")
            config = dispatcher.get("config")
        
        # Если не нашли в диспетчере, попробуем в самих данных
        if not db_pool:
            db_pool = data.get("_db_pool")
            
        if not db_applications_pool:
            db_applications_pool = data.get("_db_applications_pool")
        
        if not bot:
            bot = data.get("bot")
            
        if not config:
            config = data.get("config")
        
        if not db_applications_pool:
            logger.warning("Пул соединений с БД заявок не найден в middleware")
            return await handler(event, data)
        
        # Получаем пользователя из события
        user: User = data.get("event_from_user")
        
        if user:
            logger.debug(f"🔍 DatabaseMiddleware: обрабатываем пользователя {user.id} (@{user.username})")
            try:
                # Создаем соединения с БД
                async with db_applications_pool.connection() as applications_connection:
                    
                    logger.debug(f"💾 Соединения с БД установлены")
                    database = DB(applications_connection, applications_connection)
                    
                    # Проверяем существование пользователя
                    logger.debug(f"🔍 Проверяем существование пользователя {user.id}")
                    user_record = await database.users.get_user_record(user_id=user.id)
                    
                    if not user_record:
                        # Создаем нового пользователя
                        logger.info(f"👤 Создаем нового пользователя: {user.id} (@{user.username})")
                        await database.users.add(
                            user_id=user.id,
                            language=user.language_code or "ru",
                        )
                        logger.info(f"✅ Новый пользователь создан: {user.id}")
                    else:
                        # Обновляем статус активности
                        logger.debug(f"🔄 Обновляем статус активности пользователя {user.id}")
                        await database.users.update_alive_status(
                            user_id=user.id, 
                            is_alive=True
                        )
                    
                    # Добавляем объект БД в данные для использования в обработчиках
                    data["db"] = database
                    
                    # Добавляем дополнительные данные в middleware_data для доступа в диалогах
                    if bot:
                        data["bot"] = bot
                    if config:
                        data["config"] = config
                    
                    logger.debug(f"🎯 Вызываем обработчик для пользователя {user.id}")
                    
                    # Вызываем обработчик в контексте соединений
                    result = await handler(event, data)
                    
                    # Коммитим изменения в обеих БД
                    logger.debug(f"💾 Коммитим изменения в БД для пользователя {user.id}")
                    await applications_connection.commit()
                    
                    logger.debug(f"✅ DatabaseMiddleware: обработка пользователя {user.id} завершена")
                    return result
                    
            except Exception as e:
                logger.error(f"❌ Критическая ошибка в DatabaseMiddleware для пользователя {user.id}: {e}")
                logger.error(f"📋 Тип события: {type(event).__name__}")
                logger.error(f"📋 Данные события: {data}")
                # Возвращаем результат по умолчанию если что-то пошло не так
                return await handler(event, data)
        else:
            # Если пользователь не авторизован, просто передаем дальше
            logger.debug("⚠️ Пользователь не найден в событии, пропускаем DatabaseMiddleware")
            return await handler(event, data)
