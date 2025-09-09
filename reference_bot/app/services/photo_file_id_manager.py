import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Set, Optional

from aiogram import Bot
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)


class PhotoFileIdManager:
    """Менеджер для работы с file_id фотографий"""
    
    def __init__(self, bot: Bot, images_dir: str, file_id_storage_path: str, target_chat_id: int):
        self.bot = bot
        self.images_dir = Path(images_dir)
        self.file_id_storage_path = Path(file_id_storage_path)
        self.target_chat_id = target_chat_id
        
    def _get_all_image_files(self) -> Set[str]:
        """Получить все файлы изображений из папки images (относительные пути)"""
        image_extensions = {'.png', '.jpg', '.jpeg'}
        image_files = set()
        
        for file_path in self.images_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                # Получаем относительный путь от папки images
                relative_path = file_path.relative_to(self.images_dir)
                image_files.add(str(relative_path))
                
        return image_files
    
    def _load_existing_file_ids(self) -> Dict[str, str]:
        """Загрузить существующие file_id из JSON файла"""
        if self.file_id_storage_path.exists():
            try:
                with open(self.file_id_storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Не удалось загрузить file_id из {self.file_id_storage_path}: {e}")
        return {}
    
    def _save_file_ids(self, file_ids: Dict[str, str]) -> None:
        """Сохранить file_id в JSON файл"""
        # Создаем директорию если её нет
        self.file_id_storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.file_id_storage_path, 'w', encoding='utf-8') as f:
            json.dump(file_ids, f, ensure_ascii=False, indent=2)
        logger.info(f"Сохранено {len(file_ids)} file_id в {self.file_id_storage_path}")
    
    async def _send_photo_and_get_file_id(self, image_path: Path) -> Optional[str]:
        """Отправить фото и получить file_id"""
        try:
            photo = FSInputFile(image_path)
            message = await self.bot.send_photo(
                chat_id=self.target_chat_id,
                photo=photo,
                caption=f"📸 {image_path.name}"
            )
            
            if message.photo:
                file_id = message.photo[-1].file_id  # Берем самое большое разрешение
                logger.info(f"✅ Отправлено {image_path.name}, file_id: {file_id}")
                return file_id
            else:
                logger.error(f"❌ Не удалось получить file_id для {image_path.name}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке {image_path.name}: {e}")
            return None
    
    async def check_and_upload_new_photos(self) -> Dict[str, str]:
        """
        Проверить наличие новых фотографий и загрузить их file_id.
        Возвращает обновленный словарь file_id.
        """
        logger.info("🔍 Проверка наличия новых фотографий...")
        
        # Получаем все файлы изображений
        all_images = self._get_all_image_files()
        
        # Загружаем существующие file_id
        existing_file_ids = self._load_existing_file_ids()
        
        # Находим новые файлы
        existing_files = set(existing_file_ids.keys())
        new_files = all_images - existing_files
        
        if not new_files:
            logger.info("✅ Новых фотографий не найдено")
            return existing_file_ids
        
        logger.info(f"🆕 Найдено {len(new_files)} новых фотографий")
        
        # Отправляем новые файлы и получаем file_id
        updated_file_ids = existing_file_ids.copy()
        
        for relative_path in new_files:
            full_path = self.images_dir / relative_path
            file_id = await self._send_photo_and_get_file_id(full_path)
            
            if file_id:
                updated_file_ids[relative_path] = file_id
                # Небольшая задержка между отправками
                await asyncio.sleep(0.5)
        
        # Сохраняем обновленные file_id
        self._save_file_ids(updated_file_ids)
        
        logger.info(f"✅ Обработано {len(new_files)} новых фотографий")
        return updated_file_ids
    
    async def regenerate_all_file_ids(self) -> Dict[str, str]:
        """
        Полностью пересоздать словарь file_id для всех фотографий.
        Используется для принудительного обновления всех file_id.
        """
        logger.info("🔄 Полная регенерация file_id для всех фотографий...")
        
        # Получаем все файлы изображений
        all_images = self._get_all_image_files()
        
        if not all_images:
            logger.warning("❌ Фотографии не найдены в папке images")
            return {}
        
        logger.info(f"📸 Найдено {len(all_images)} фотографий для обработки")
        
        file_ids = {}
        
        for i, relative_path in enumerate(all_images, 1):
            full_path = self.images_dir / relative_path
            logger.info(f"📤 Отправка {i}/{len(all_images)}: {relative_path}")
            
            file_id = await self._send_photo_and_get_file_id(full_path)
            
            if file_id:
                file_ids[relative_path] = file_id
                
            # Задержка между отправками
            await asyncio.sleep(0.5)
        
        # Сохраняем все file_id
        self._save_file_ids(file_ids)
        
        logger.info(f"✅ Регенерация завершена. Обработано {len(file_ids)} фотографий")
        return file_ids
    
    def get_file_id(self, relative_path: str) -> Optional[str]:
        """Получить file_id для конкретного файла"""
        file_ids = self._load_existing_file_ids()
        return file_ids.get(relative_path)
    
    def get_all_file_ids(self) -> Dict[str, str]:
        """Получить все file_id"""
        return self._load_existing_file_ids()


async def startup_photo_check(bot: Bot, images_dir: str = "app/bot/assets/images", 
                             target_chat_id: int = 257026813, 
                             file_id_storage_path: str = "config/photo_file_ids.json") -> Dict[str, str]:
    """
    Функция для проверки новых фотографий при старте бота.
    
    Args:
        bot: Экземпляр бота
        images_dir: Путь к папке с изображениями
        target_chat_id: ID чата для отправки фотографий
        file_id_storage_path: Путь к файлу с file_id
        
    Returns:
        Словарь с file_id всех фотографий
    """
    manager = PhotoFileIdManager(bot, images_dir, file_id_storage_path, target_chat_id)
    return await manager.check_and_upload_new_photos()
