#!/usr/bin/env python3
"""
Утилита для тестирования команды синхронизации с Google Sheets
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import load_config
from app.infrastructure.database import DatabaseManager
from app.infrastructure.google_sheets import GoogleSheetsManager


async def test_sync_command():
    """Тестирование команды /sync_debates_google"""
    
    print("🔄 Тестирование команды /sync_debates_google")
    print("=" * 50)
    
    try:
        # Загружаем конфигурацию
        config = load_config()
        print(f"✅ Конфигурация загружена")
        
        # Инициализируем менеджеры
        db_manager = DatabaseManager(config.db)
        await db_manager.init()
        
        google_sheets_manager = GoogleSheetsManager(
            config.google_sheets.credentials_path,
            config.google_sheets.spreadsheet_id
        )
        
        print(f"✅ Менеджеры инициализированы")
        
        # Имитируем выполнение команды
        print("\n🔄 Начинаю синхронизацию с Google Таблицами...")
        
        # Получаем данные пользователей
        users_data = await db_manager.get_all_users_for_export()
        db_counts = await db_manager.get_debate_registrations_count()
        
        print(f"📊 Получено пользователей: {len(users_data)}")
        print(f"📊 Статистика регистрации: {db_counts}")
        
        # Синхронизируем с Google Sheets
        success = await google_sheets_manager.sync_debate_data(users_data, db_counts)
        
        if success:
            print("\n✅ Синхронизация завершена успешно!")
            print(f"📊 Экспортировано пользователей: {len(users_data)}")
            print("📝 Лист MAIN обновлен")
            print("� Таблица содержит только данные о регистрации пользователей")
            
            print("\n🎉 Команда /sync_debates_google работает корректно!")
            
        else:
            print("❌ Ошибка синхронизации")
            return False
        
        # Закрываем подключения
        await db_manager.close()
        
        return True
        
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
        logging.exception("Error during sync command testing")
        return False


async def main():
    """Главная функция"""
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    success = await test_sync_command()
    
    if success:
        print("\n✅ Команда /sync_debates_google готова к использованию")
        exit(0)
    else:
        print("\n❌ Проблемы с командой синхронизации")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())