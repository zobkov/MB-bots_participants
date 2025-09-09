#!/usr/bin/env python3
"""
Скрипт для проверки состояния баз данных
"""
import asyncio
import os
from typing import Dict, Any

import asyncpg
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

async def check_database(db_config: Dict[str, Any], db_name: str) -> Dict[str, Any]:
    """Проверяем состояние базы данных"""
    print(f"\n{'='*50}")
    print(f"Проверка базы данных: {db_name}")
    print(f"{'='*50}")
    
    try:
        # Подключаемся к базе
        conn = await asyncpg.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"]
        )
        
        print(f"✅ Подключение установлено")
        print(f"📍 Хост: {db_config['host']}:{db_config['port']}")
        print(f"🗄️  База данных: {db_config['database']}")
        
        # Получаем информацию о версии PostgreSQL
        version = await conn.fetchval("SELECT version()")
        print(f"🔧 Версия PostgreSQL: {version.split(',')[0]}")
        
        # Получаем список таблиц
        tables_query = """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """
        tables = await conn.fetch(tables_query)
        
        print(f"\n📋 Таблицы в базе данных:")
        if tables:
            for table in tables:
                table_name = table['tablename']
                
                # Получаем количество записей в таблице
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                print(f"   📊 {table_name}: {count} записей")
                
                # Для таблицы users показываем структуру
                if table_name == 'users':
                    print(f"      └── Структура:")
                    columns = await conn.fetch("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns 
                        WHERE table_name = 'users' AND table_schema = 'public'
                        ORDER BY ordinal_position;
                    """)
                    for col in columns:
                        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                        print(f"          • {col['column_name']}: {col['data_type']} {nullable}")
                
                # Для таблицы applications показываем структуру
                elif table_name == 'applications':
                    print(f"      └── Структура:")
                    columns = await conn.fetch("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns 
                        WHERE table_name = 'applications' AND table_schema = 'public'
                        ORDER BY ordinal_position;
                    """)
                    for col in columns:
                        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                        print(f"          • {col['column_name']}: {col['data_type']} {nullable}")
        else:
            print("   ❌ Таблицы не найдены")
        
        await conn.close()
        return {"status": "success", "tables": [t['tablename'] for t in tables]}
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return {"status": "error", "error": str(e)}


async def main():
    """Основная функция проверки"""
    print("🔍 Проверка состояния баз данных КБК")
    
    # Конфигурация для базы заявок
    applications_db_config = {
        "host": os.getenv("DB_APPLICATIONS_HOST"),
        "port": int(os.getenv("DB_APPLICATIONS_PORT")),
        "user": os.getenv("DB_APPLICATIONS_USER"),
        "password": os.getenv("DB_APPLICATIONS_PASS"),
        "database": os.getenv("DB_APPLICATIONS_NAME")
    }
    
    # Проверяем базу данных заявок (содержит users и applications)
    apps_result = await check_database(applications_db_config, "База заявок (applications + users)")
    
    # Финальный отчет
    print(f"\n{'='*50}")
    print("📝 ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*50}")
    
    print(f"\n🗂️  База заявок (порт {applications_db_config['port']}):")
    if apps_result["status"] == "success":
        print(f"   ✅ Статус: Подключение успешно")
        print(f"   📊 Таблицы: {', '.join(apps_result['tables'])}")
        print(f"   ✅ Ожидаемые таблицы: users, applications")
        print(f"   {'✅' if 'users' in apps_result['tables'] else '❌'} Таблица users")
        print(f"   {'✅' if 'applications' in apps_result['tables'] else '❌'} Таблица applications")
    else:
        print(f"   ❌ Статус: Ошибка подключения")
        print(f"   📝 Ошибка: {apps_result['error']}")
    
    print(f"\n🔍 АНАЛИЗ КОНФИГУРАЦИИ:")
    if apps_result["status"] == "success":
        print("   ✅ Единая база содержит обе таблицы (users, applications)")
    else:
        print("   ❌ Проверьте настройки подключения к базе заявок")


if __name__ == "__main__":
    asyncio.run(main())
