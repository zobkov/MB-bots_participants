"""
Утилиты для работы с file_id фотографий в боте.
Обеспечивает быструю отправку фотографий через file_id вместо загрузки файлов.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict

from aiogram import Bot
from aiogram.types import InputMediaPhoto, Message

logger = logging.getLogger(__name__)


class PhotoSender:
    """Класс для оптимизированной отправки фотографий через file_id"""
    
    def __init__(self, file_id_storage_path: str = "config/photo_file_ids.json"):
        self.file_id_storage_path = Path(file_id_storage_path)
        self._file_ids_cache: Optional[Dict[str, str]] = None
    
    def _load_file_ids(self) -> Dict[str, str]:
        """Загрузить file_id из файла с кешированием"""
        if self._file_ids_cache is None:
            if self.file_id_storage_path.exists():
                try:
                    with open(self.file_id_storage_path, 'r', encoding='utf-8') as f:
                        self._file_ids_cache = json.load(f)
                        logger.debug(f"Загружено {len(self._file_ids_cache)} file_id из кеша")
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    logger.warning(f"Не удалось загрузить file_id: {e}")
                    self._file_ids_cache = {}
            else:
                logger.warning(f"Файл {self.file_id_storage_path} не найден")
                self._file_ids_cache = {}
        
        return self._file_ids_cache
    
    def reload_cache(self) -> None:
        """Принудительно обновить кеш file_id"""
        self._file_ids_cache = None
        self._load_file_ids()
        logger.info("Кеш file_id обновлен")
    
    def get_file_id(self, relative_path: str) -> Optional[str]:
        """
        Получить file_id для фотографии по относительному пути.
        
        Args:
            relative_path: Путь относительно папки images (например, "start/1.png")
            
        Returns:
            file_id или None если не найден
        """
        file_ids = self._load_file_ids()
        return file_ids.get(relative_path)
    
    async def send_photo_by_path(self, bot: Bot, chat_id: int, relative_path: str, 
                                caption: Optional[str] = None, **kwargs) -> Optional[Message]:
        """
        Отправить фотографию по относительному пути.
        Сначала пытается использовать file_id, при неудаче отправляет файл.
        
        Args:
            bot: Экземпляр бота
            chat_id: ID чата
            relative_path: Путь к фото относительно папки images
            caption: Подпись к фото
            **kwargs: Дополнительные параметры для send_photo
            
        Returns:
            Отправленное сообщение или None при ошибке
        """
        file_id = self.get_file_id(relative_path)
        
        if file_id:
            try:
                # Пытаемся отправить через file_id
                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=caption,
                    **kwargs
                )
                logger.debug(f"✅ Фото {relative_path} отправлено через file_id")
                return message
                
            except Exception as e:
                logger.warning(f"⚠️ Не удалось отправить {relative_path} через file_id: {e}")
        
        # Fallback: отправляем как файл
        try:
            from aiogram.types import FSInputFile
            
            full_path = Path("app/bot/assets/images") / relative_path
            if full_path.exists():
                photo = FSInputFile(full_path)
                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=caption,
                    **kwargs
                )
                logger.warning(f"📁 Фото {relative_path} отправлено как файл (fallback)")
                return message
            else:
                logger.error(f"❌ Файл {full_path} не найден")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке {relative_path}: {e}")
            return None
    
    async def send_photo_group_by_paths(self, bot: Bot, chat_id: int, 
                                       relative_paths: list[str], 
                                       captions: Optional[list[str]] = None,
                                       **kwargs) -> Optional[list[Message]]:
        """
        Отправить группу фотографий как медиа-группу.
        
        Args:
            bot: Экземпляр бота
            chat_id: ID чата
            relative_paths: Список путей к фото относительно папки images
            captions: Список подписей (опционально)
            **kwargs: Дополнительные параметры для send_media_group
            
        Returns:
            Список отправленных сообщений или None при ошибке
        """
        if not relative_paths:
            return None
        
        media_group = []
        
        for i, relative_path in enumerate(relative_paths):
            file_id = self.get_file_id(relative_path)
            caption = captions[i] if captions and i < len(captions) else None
            
            if file_id:
                media_group.append(InputMediaPhoto(media=file_id, caption=caption))
            else:
                # Fallback: используем файл
                from aiogram.types import FSInputFile
                
                full_path = Path("app/bot/assets/images") / relative_path
                if full_path.exists():
                    photo = FSInputFile(full_path)
                    media_group.append(InputMediaPhoto(media=photo, caption=caption))
                else:
                    logger.error(f"❌ Файл {full_path} не найден")
                    continue
        
        if not media_group:
            logger.error("❌ Нет доступных фотографий для отправки")
            return None
        
        try:
            messages = await bot.send_media_group(
                chat_id=chat_id,
                media=media_group,
                **kwargs
            )
            logger.debug(f"✅ Отправлена медиа-группа из {len(messages)} фотографий")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке медиа-группы: {e}")
            return None
    
    def has_file_id(self, relative_path: str) -> bool:
        """Проверить, есть ли file_id для указанного файла"""
        return self.get_file_id(relative_path) is not None
    
    def get_stats(self) -> Dict[str, int]:
        """Получить статистику по file_id"""
        file_ids = self._load_file_ids()
        return {
            "total_photos": len(file_ids),
            "cache_loaded": self._file_ids_cache is not None
        }


# Глобальный экземпляр для использования в боте
photo_sender = PhotoSender()


def get_photo_sender() -> PhotoSender:
    """Получить глобальный экземпляр PhotoSender"""
    return photo_sender
