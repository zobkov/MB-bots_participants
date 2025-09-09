#!/usr/bin/env python3
"""
Скрипт для принудительной регенерации всех file_id фотографий.
Отправляет все фото из папки images в указанный чат и сохраняет file_id.

Использование:
    python regenerate_photo_file_ids.py
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Добавляем корневую папку проекта в путь
sys.path.append(str(Path(__file__).parent))

from config.config import load_config
from app.services.photo_file_id_manager import PhotoFileIdManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('photo_file_id_regeneration.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Константы
TARGET_CHAT_ID = 257026813  # Чат с вами
IMAGES_DIR = "app/bot/assets/images"
FILE_ID_STORAGE_PATH = "config/photo_file_ids.json"


async def main():
    """Главная функция для регенерации file_id"""
    try:
        logger.info("🚀 Запуск скрипта регенерации file_id...")
        
        # Загружаем конфигурацию
        config = load_config()
        
        # Создаем бота
        bot = Bot(
            token=config.tg_bot.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        
        # Создаем менеджер file_id
        manager = PhotoFileIdManager(
            bot=bot,
            images_dir=IMAGES_DIR,
            file_id_storage_path=FILE_ID_STORAGE_PATH,
            target_chat_id=TARGET_CHAT_ID
        )
        
        # Отправляем сообщение о начале процесса
        await bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text="🔄 <b>Начинаю регенерацию file_id для всех фотографий бота</b>\n\n"
                 "Это может занять некоторое время..."
        )
        
        # Запускаем полную регенерацию
        file_ids = await manager.regenerate_all_file_ids()
        
        # Отправляем отчет
        report = (
            f"✅ <b>Регенерация file_id завершена!</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Обработано фотографий: <code>{len(file_ids)}</code>\n"
            f"• Файл сохранен: <code>{FILE_ID_STORAGE_PATH}</code>\n\n"
            f"🤖 Теперь бот может использовать оптимизированную отправку фото!"
        )
        
        await bot.send_message(chat_id=TARGET_CHAT_ID, text=report)
        
        logger.info(f"✅ Регенерация завершена успешно. Обработано {len(file_ids)} фотографий")
        
        # Закрываем сессию бота
        await bot.session.close()
        
    except Exception as e:
        logger.exception(f"❌ Ошибка при регенерации file_id: {e}")
        
        # Пытаемся отправить сообщение об ошибке
        try:
            if 'bot' in locals():
                await bot.send_message(
                    chat_id=TARGET_CHAT_ID,
                    text=f"❌ <b>Ошибка при регенерации file_id</b>\n\n"
                         f"<code>{str(e)}</code>\n\n"
                         f"Проверьте логи для подробностей."
                )
                await bot.session.close()
        except Exception:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    print("🔄 Запуск регенерации file_id для фотографий...")
    print(f"📁 Папка с изображениями: {IMAGES_DIR}")
    print(f"💾 Файл для сохранения: {FILE_ID_STORAGE_PATH}")
    print(f"💬 Целевой чат: {TARGET_CHAT_ID}")
    print()
    
    # Подтверждение запуска
    try:
        confirm = input("Продолжить? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes', 'да']:
            print("❌ Отменено пользователем")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n❌ Отменено пользователем")
        sys.exit(0)
    
    asyncio.run(main())
