"""
Хелперы для работы с file_id в aiogram-dialog.
Позволяют получать file_id для использования в стандартных виджетах.
"""

from typing import Optional
from pathlib import Path

from app.utils.photo_utils import get_photo_sender


def get_file_id_for_path(relative_path: str) -> Optional[str]:
    """
    Получает file_id для относительного пути к изображению.
    
    Args:
        relative_path: Путь к изображению относительно папки images (например, "main_menu/main_menu.png")
        
    Returns:
        file_id если найден, иначе None
        
    Example:
        file_id = get_file_id_for_path("main_menu/main_menu.jpg")
        if file_id:
            # Используем в StaticMedia через file_id
            StaticMedia(file_id=file_id)
        else:
            # Fallback на файл
            StaticMedia(path="app/bot/assets/images/main_menu/main_menu.jpg")
    """
    photo_sender = get_photo_sender()
    file_id = photo_sender.get_file_id(relative_path)
    
    if file_id:
        # Очищаем file_id от возможных пробелов и переносов строк
        file_id = file_id.strip().replace('\n', '').replace('\r', '')
        return file_id if file_id else None
    
    return None
