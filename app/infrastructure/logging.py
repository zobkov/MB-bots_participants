"""
Модуль настройки логирования для бота.
Обеспечивает логирование в файлы с разделением по датам.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


class DateRotatingFileHandler(logging.handlers.BaseRotatingHandler):
    """
    Кастомный обработчик для ротации логов по датам.
    Создает новый файл каждый день в формате YYYY-MM-DD.log
    """
    
    def __init__(self, log_dir: str, prefix: str = "bot", encoding: str = "utf-8"):
        self.log_dir = Path(log_dir)
        self.prefix = prefix
        self.encoding = encoding
        
        # Создаем директорию если её нет
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Формируем имя файла на текущую дату
        filename = self._get_current_filename()
        super().__init__(filename, mode='a', encoding=encoding)
        
        self.current_date = datetime.now().date()
    
    def _get_current_filename(self) -> str:
        """Получить имя файла для текущей даты"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        return str(self.log_dir / f"{self.prefix}-{current_date}.log")
    
    def shouldRollover(self, record) -> bool:
        """Проверить, нужно ли создать новый файл"""
        return datetime.now().date() != self.current_date
    
    def doRollover(self):
        """Создать новый файл для новой даты"""
        if self.stream:
            self.stream.close()
            self.stream = None
        
        # Обновляем дату и имя файла
        self.current_date = datetime.now().date()
        self.baseFilename = self._get_current_filename()
        
        # Открываем новый файл
        if not self.delay:
            self.stream = self._open()


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    console_output: bool = True,
    file_prefix: str = "bot",
    admin_ids: list = None
) -> None:
    """
    Настройка логирования для бота.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Директория для сохранения логов
        console_output: Выводить ли логи в консоль
        file_prefix: Префикс для имен файлов логов
        admin_ids: Список ID администраторов для уведомлений
    """
    
    # Конвертируем строку в уровень логирования
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Создаем форматтер для файлов и консоли
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Форматтер с контекстом для консоли
    context_formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s | %(message)s | user=%(user_id)s chat=%(chat_id)s upd=%(update_type)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Создаем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Очищаем существующие обработчики
    root_logger.handlers.clear()
    
    # Настраиваем файловый обработчик с ротацией по датам
    file_handler = DateRotatingFileHandler(
        log_dir=log_dir, 
        prefix=file_prefix,
        encoding="utf-8"
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Настраиваем консольный обработчик (если нужен)
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(context_formatter)
        
        # Добавляем фильтр контекста для консоли
        from app.infrastructure.telegram_logging import ContextFilter
        console_handler.addFilter(ContextFilter())
        
        root_logger.addHandler(console_handler)
    
    # Настраиваем Telegram handler если есть админы
    if admin_ids:
        from app.infrastructure.telegram_logging import setup_telegram_logging
        telegram_handler = setup_telegram_logging(admin_ids)
        if telegram_handler:
            root_logger.addHandler(telegram_handler)
            logging.info(f"Telegram notifications enabled for {len(admin_ids)} admin(s)")
    
    # Устанавливаем уровни для популярных библиотек
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiogram_dialog").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured - Level: {log_level}, Dir: {log_dir}, Admins: {len(admin_ids or [])}")


def get_log_files_info(log_dir: str = "logs") -> list:
    """
    Получить информацию о существующих файлах логов.
    
    Args:
        log_dir: Директория с логами
        
    Returns:
        Список словарей с информацией о файлах логов
    """
    log_path = Path(log_dir)
    
    if not log_path.exists():
        return []
    
    log_files = []
    for log_file in log_path.glob("*.log"):
        stat = log_file.stat()
        log_files.append({
            "name": log_file.name,
            "path": str(log_file),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "created": datetime.fromtimestamp(stat.st_ctime)
        })
    
    return sorted(log_files, key=lambda x: x["modified"], reverse=True)


def cleanup_old_logs(log_dir: str = "logs", keep_days: int = 30) -> int:
    """
    Удалить старые файлы логов.
    
    Args:
        log_dir: Директория с логами
        keep_days: Количество дней для хранения логов
        
    Returns:
        Количество удаленных файлов
    """
    log_path = Path(log_dir)
    
    if not log_path.exists():
        return 0
    
    cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
    deleted_count = 0
    
    for log_file in log_path.glob("*.log"):
        if log_file.stat().st_mtime < cutoff_date:
            try:
                log_file.unlink()
                deleted_count += 1
                logging.info(f"Deleted old log file: {log_file.name}")
            except Exception as e:
                logging.error(f"Failed to delete log file {log_file.name}: {e}")
    
    return deleted_count