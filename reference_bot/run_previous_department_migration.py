#!/usr/bin/env python3
"""
Скрипт для запуска миграции добавления поля previous_department
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database.connect_to_pg import get_pg_pool
from config.config import load_config

async def run_migration():
    """Запускает миграцию для добавления поля previous_department"""
    
    config = load_config()
    
    print("📦 Подключаемся к базе данных...")
    try:
        # Создаем pool соединений для базы данных applications
        db_pool = await get_pg_pool(
            db_name=config.db_applications.database,
            host=config.db_applications.host,
            port=config.db_applications.port,
            user=config.db_applications.user,
            password=config.db_applications.password
        )
        
        print("✅ Подключение к БД установлено")
        
        # Читаем и выполняем SQL миграцию
        migration_path = "migrations/004_add_previous_department.sql"
        
        if not os.path.exists(migration_path):
            print(f"❌ Файл миграции не найден: {migration_path}")
            return
        
        with open(migration_path, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        print("🔄 Выполняем миграцию...")
        
        async with db_pool.connection() as connection:
            await connection.execute(migration_sql)
            
        print("✅ Миграция успешно выполнена!")
        print("🆕 Добавлено поле 'previous_department' в таблицу applications")
        
        # Закрываем pool
        await db_pool.close()
        
    except Exception as e:
        print(f"❌ Ошибка при выполнении миграции: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())
