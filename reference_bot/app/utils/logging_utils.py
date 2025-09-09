"""
Утилиты для расширенного логирования
"""
import logging
import functools
from datetime import datetime
from typing import Callable, Any
import json

logger = logging.getLogger(__name__)


def log_user_action(action_name: str, log_level: int = logging.INFO):
    """
    Декоратор для логирования действий пользователя
    
    Args:
        action_name: Название действия для логирования
        log_level: Уровень логирования
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Извлекаем информацию о пользователе из аргументов
            user_id = None
            username = None
            
            for arg in args:
                if hasattr(arg, 'from_user'):
                    user_id = arg.from_user.id
                    username = arg.from_user.username
                    break
                elif hasattr(arg, 'event') and hasattr(arg.event, 'from_user'):
                    user_id = arg.event.from_user.id
                    username = arg.event.from_user.username
                    break
            
            start_time = datetime.now()
            
            # Логируем начало действия
            logger.log(log_level, f"🎯 {action_name} | Пользователь: {user_id} (@{username}) | Начало")
            
            try:
                result = await func(*args, **kwargs)
                
                # Логируем успешное завершение
                duration = (datetime.now() - start_time).total_seconds()
                logger.log(log_level, f"✅ {action_name} | Пользователь: {user_id} | Завершено за {duration:.2f}с")
                
                return result
                
            except Exception as e:
                # Логируем ошибку
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(f"❌ {action_name} | Пользователь: {user_id} | Ошибка за {duration:.2f}с: {e}")
                raise
                
        return wrapper
    return decorator


def log_data_operation(operation_name: str, sensitive_fields: list = None):
    """
    Декоратор для логирования операций с данными
    
    Args:
        operation_name: Название операции
        sensitive_fields: Список полей, которые нужно скрыть в логах
    """
    if sensitive_fields is None:
        sensitive_fields = ['password', 'token', 'secret', 'credentials']
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            # Маскируем чувствительные данные
            safe_kwargs = {}
            for key, value in kwargs.items():
                if any(sensitive in key.lower() for sensitive in sensitive_fields):
                    safe_kwargs[key] = "***MASKED***"
                else:
                    safe_kwargs[key] = str(value)[:100]  # Ограничиваем длину для читаемости
            
            logger.info(f"📊 {operation_name} | Начало | Параметры: {safe_kwargs}")
            
            try:
                result = await func(*args, **kwargs)
                
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ {operation_name} | Успешно завершено за {duration:.2f}с")
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(f"❌ {operation_name} | Ошибка за {duration:.2f}с: {e}")
                raise
                
        return wrapper
    return decorator


def log_api_call(service_name: str, endpoint: str = None):
    """
    Декоратор для логирования API вызовов
    
    Args:
        service_name: Название сервиса (Google Drive, Google Sheets, etc.)
        endpoint: Конечная точка API
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            
            endpoint_info = f" | Endpoint: {endpoint}" if endpoint else ""
            logger.info(f"🌐 API Call | {service_name}{endpoint_info} | Начало")
            
            try:
                result = await func(*args, **kwargs)
                
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ API Call | {service_name} | Успешно за {duration:.2f}с")
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                error_type = type(e).__name__
                
                # Специальная обработка API ошибок
                if "403" in str(e):
                    logger.warning(f"🚫 API Call | {service_name} | Доступ запрещен (403) за {duration:.2f}с")
                elif "401" in str(e):
                    logger.warning(f"🔐 API Call | {service_name} | Неавторизован (401) за {duration:.2f}с")
                elif "404" in str(e):
                    logger.warning(f"🔍 API Call | {service_name} | Не найдено (404) за {duration:.2f}с")
                elif "quotaExceeded" in str(e) or "storageQuotaExceeded" in str(e):
                    logger.warning(f"📊 API Call | {service_name} | Превышена квота за {duration:.2f}с")
                else:
                    logger.error(f"❌ API Call | {service_name} | {error_type} за {duration:.2f}с: {e}")
                
                raise
                
        return wrapper
    return decorator


class ProcessLogger:
    """Класс для подробного логирования процессов"""
    
    def __init__(self, process_name: str, user_id: int = None):
        self.process_name = process_name
        self.user_id = user_id
        self.start_time = datetime.now()
        self.steps = []
        
    def step(self, step_name: str, details: str = None):
        """Логирует шаг процесса"""
        timestamp = datetime.now()
        duration = (timestamp - self.start_time).total_seconds()
        
        step_info = f"📋 {self.process_name} | Шаг: {step_name}"
        if self.user_id:
            step_info += f" | Пользователь: {self.user_id}"
        step_info += f" | +{duration:.2f}с"
        
        if details:
            step_info += f" | {details}"
            
        logger.info(step_info)
        
        self.steps.append({
            'step': step_name,
            'timestamp': timestamp.isoformat(),
            'duration': duration,
            'details': details
        })
    
    def complete(self, success: bool = True, final_message: str = None):
        """Завершает процесс"""
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        status = "✅ Успешно" if success else "❌ С ошибкой"
        completion_info = f"🏁 {self.process_name} | {status} | Общее время: {total_duration:.2f}с"
        
        if self.user_id:
            completion_info += f" | Пользователь: {self.user_id}"
            
        if final_message:
            completion_info += f" | {final_message}"
            
        logger.info(completion_info)
        
        # Логируем сводку по шагам
        if self.steps:
            logger.debug(f"📊 {self.process_name} | Сводка по шагам: {len(self.steps)} шагов")
            for i, step in enumerate(self.steps, 1):
                logger.debug(f"   {i}. {step['step']} ({step['duration']:.2f}с)")


def create_process_logger(process_name: str, user_id: int = None) -> ProcessLogger:
    """Создает новый логгер процесса"""
    return ProcessLogger(process_name, user_id)


# Готовые декораторы для частых операций
database_operation = log_data_operation
google_api_call = log_api_call
user_action = log_user_action

# Примеры использования:
# @user_action("Загрузка резюме")
# async def upload_resume(...)

# @google_api_call("Google Drive", "files.create")  
# async def upload_to_drive(...)

# @database_operation("Сохранение заявки")
# async def save_application(...)
