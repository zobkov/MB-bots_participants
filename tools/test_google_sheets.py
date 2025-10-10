#!/usr/bin/env python3
"""
Утилита для тестирования интеграции с Google Sheets
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


async def test_google_sheets():
    """Тестирование подключения и синхронизации с Google Sheets"""
    
    print("🔧 Тестирование интеграции с Google Sheets")
    print("=" * 50)
    
    try:
        # Загружаем конфигурацию
        config = load_config()
        print(f"✅ Конфигурация загружена")
        
        # Проверяем наличие файла credentials
        if not os.path.exists(config.google_sheets.credentials_path):
            print(f"❌ Файл credentials не найден: {config.google_sheets.credentials_path}")
            print("💡 Создайте файл google_credentials.json по инструкции в docs/GOOGLE_SHEETS.md")
            return False
        
        print(f"✅ Файл credentials найден: {config.google_sheets.credentials_path}")
        
        # Инициализируем Google Sheets Manager
        print("\n🔗 Тестирование подключения к Google Sheets...")
        google_sheets = GoogleSheetsManager(
            config.google_sheets.credentials_path,
            config.google_sheets.spreadsheet_id
        )
        
        # Тестируем подключение
        success = await google_sheets.test_connection()
        if not success:
            print("❌ Не удалось подключиться к Google Sheets")
            print("💡 Проверьте:")
            print("   - Правильность ID таблицы в .env")
            print("   - Права доступа Service Account к таблице")
            print("   - Активацию Google Sheets API")
            return False
        
        print("✅ Подключение к Google Sheets успешно")
        
        # Инициализируем базу данных
        print("\n📊 Получение данных из базы...")
        db_manager = DatabaseManager(config.db)
        await db_manager.init()
        
        # Получаем данные для синхронизации
        users_data = await db_manager.get_all_users_for_export()
        db_counts = await db_manager.get_debate_registrations_count()
        
        print(f"✅ Получено пользователей: {len(users_data)}")
        print(f"✅ Статистика регистрации: {db_counts}")
        
        # Тестируем синхронизацию
        print("\n📝 Тестирование синхронизации данных...")
        sync_success = await google_sheets.sync_debate_data(users_data, db_counts)
        
        if sync_success:
            print("✅ Синхронизация данных прошла успешно!")
            print(f"📊 Экспортировано пользователей: {len(users_data)}")
            print("💡 Проверьте лист MAIN в вашей Google Таблице")
        else:
            print("❌ Ошибка при синхронизации данных")
            return False
        
        # Закрываем подключения
        await db_manager.close()
        
        print("\n🎉 Все тесты прошли успешно!")
        print("💡 Теперь команда /sync_debates_google готова к использованию")
        return True
        
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        logging.exception("Error during Google Sheets testing")
        return False


async def main():
    """Главная функция"""
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    success = await test_google_sheets()
    
    if success:
        print("\n✅ Интеграция с Google Sheets настроена корректно")
        exit(0)
    else:
        print("\n❌ Проблемы с интеграцией Google Sheets")
        print("📖 Изучите документацию: docs/GOOGLE_SHEETS.md")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())