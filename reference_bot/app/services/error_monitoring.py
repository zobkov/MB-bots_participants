"""
Модуль для мониторинга и анализа ошибок
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional
import json
import os
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ErrorReport:
    """Структура отчета об ошибке"""
    timestamp: str
    error_type: str
    error_message: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    context: Optional[str] = None
    severity: str = "ERROR"
    component: str = "UNKNOWN"
    resolved: bool = False


class ErrorMonitor:
    """Класс для мониторинга и анализа ошибок"""
    
    def __init__(self, log_file_path: str = "app/logs/error_reports.json"):
        self.log_file_path = log_file_path
        self.ensure_log_file_exists()
    
    def ensure_log_file_exists(self):
        """Создает файл логов если его нет"""
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        if not os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def log_error(
        self, 
        error_type: str,
        error_message: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        context: Optional[str] = None,
        severity: str = "ERROR",
        component: str = "UNKNOWN"
    ):
        """
        Логирует ошибку в файл для последующего анализа
        
        Args:
            error_type: Тип ошибки (GoogleDriveError, DatabaseError, ValidationError и т.д.)
            error_message: Текст ошибки
            user_id: ID пользователя (если применимо)
            username: Имя пользователя (если применимо)
            context: Контекст ошибки (где произошла)
            severity: Уровень серьезности (ERROR, WARNING, CRITICAL)
            component: Компонент системы (GOOGLE_DRIVE, DATABASE, FILE_UPLOAD и т.д.)
        """
        error_report = ErrorReport(
            timestamp=datetime.now().isoformat(),
            error_type=error_type,
            error_message=error_message,
            user_id=user_id,
            username=username,
            context=context,
            severity=severity,
            component=component
        )
        
        try:
            # Читаем существующие ошибки
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                errors = json.load(f)
            
            # Добавляем новую ошибку
            errors.append(asdict(error_report))
            
            # Ограничиваем количество записей (последние 1000)
            if len(errors) > 1000:
                errors = errors[-1000:]
            
            # Сохраняем обратно
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(errors, f, ensure_ascii=False, indent=2)
                
            logger.info(f"📊 Ошибка зафиксирована: {error_type} - {error_message[:100]}...")
            
        except Exception as e:
            logger.error(f"❌ Не удалось записать ошибку в файл мониторинга: {e}")
    
    def get_error_statistics(self, last_hours: int = 24) -> Dict:
        """
        Получает статистику ошибок за указанный период
        
        Args:
            last_hours: Количество часов для анализа
            
        Returns:
            Dict: Статистика ошибок
        """
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                errors = json.load(f)
            
            # Фильтруем ошибки по времени
            cutoff_time = datetime.now().timestamp() - (last_hours * 3600)
            recent_errors = [
                error for error in errors
                if datetime.fromisoformat(error['timestamp']).timestamp() > cutoff_time
            ]
            
            # Собираем статистику
            stats = {
                'total_errors': len(recent_errors),
                'by_component': {},
                'by_type': {},
                'by_severity': {},
                'recent_critical': []
            }
            
            for error in recent_errors:
                # По компонентам
                component = error.get('component', 'UNKNOWN')
                stats['by_component'][component] = stats['by_component'].get(component, 0) + 1
                
                # По типам
                error_type = error.get('error_type', 'UNKNOWN')
                stats['by_type'][error_type] = stats['by_type'].get(error_type, 0) + 1
                
                # По серьезности
                severity = error.get('severity', 'ERROR')
                stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
                
                # Критические ошибки
                if severity == 'CRITICAL':
                    stats['recent_critical'].append(error)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении статистики: {e}")
            return {}
    
    def log_google_drive_error(self, error_message: str, user_id: int, username: str = None, filename: str = None):
        """Специализированный метод для логирования ошибок Google Drive"""
        context = f"file_upload"
        if filename:
            context += f", filename: {filename}"
            
        severity = "CRITICAL" if "Service Accounts do not have storage quota" in error_message else "ERROR"
        
        self.log_error(
            error_type="GoogleDriveError",
            error_message=error_message,
            user_id=user_id,
            username=username,
            context=context,
            severity=severity,
            component="GOOGLE_DRIVE"
        )
    
    def log_database_error(self, error_message: str, operation: str, user_id: int = None):
        """Специализированный метод для логирования ошибок базы данных"""
        self.log_error(
            error_type="DatabaseError",
            error_message=error_message,
            user_id=user_id,
            context=f"operation: {operation}",
            severity="CRITICAL",
            component="DATABASE"
        )
    
    def log_validation_error(self, field: str, value: str, user_id: int, username: str = None):
        """Специализированный метод для логирования ошибок валидации"""
        self.log_error(
            error_type="ValidationError",
            error_message=f"Invalid {field}: {value[:50]}...",
            user_id=user_id,
            username=username,
            context=f"field_validation: {field}",
            severity="WARNING",
            component="VALIDATION"
        )


# Глобальный экземпляр монитора ошибок
error_monitor = ErrorMonitor()
