#!/usr/bin/env python3
"""
Скрипт для применения миграций к базе данных заявок
"""
import asyncio
import psycopg
import logging
from config.config import load_config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='#%(levelname)-8s [%(asctime)s] - %(filename)s:%(lineno)d - %(name)s:%(funcName)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_applications_migrations():
    """Применяет миграции для заявок"""
    logger.info("Загрузка конфигурации")
    config = load_config()
    
    # Подключение к базе данных заявок
    connection_string = f"postgresql://{config.db_applications.user}:{config.db_applications.password}@{config.db_applications.host}:{config.db_applications.port}/{config.db_applications.database}"
    
    logger.info("Подключение к базе данных заявок")
    async with await psycopg.AsyncConnection.connect(connection_string) as conn:
        async with conn.cursor() as cur:
            # Создаем таблицу миграций если не существует
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.commit()
            
            # Получаем список примененных миграций
            await cur.execute("SELECT filename FROM migrations")
            applied_migrations = {row[0] for row in await cur.fetchall()}
            logger.info(f"Уже применены миграции: {applied_migrations}")
            
            # Читаем и применяем все миграции для заявок
            import os
            migrations_dir = "migrations"
            
            # Список миграций для заявок (в порядке применения)
            application_migrations = [
                "002_create_applications_table.sql",
                "003_update_applications_table.sql",
                "005_add_priority_system.sql",
                "006_create_users_in_app_db.sql",
                "007_update_applications_fk_and_drop_status.sql",
            ]
            
            for migration_file in application_migrations:
                migration_path = os.path.join(migrations_dir, migration_file)
                
                if os.path.exists(migration_path):
                    if migration_file not in applied_migrations:
                        logger.info(f"Применяем миграцию: {migration_file}")
                        
                        with open(migration_path, 'r', encoding='utf-8') as f:
                            migration_sql = f.read()
                        
                        try:
                            await cur.execute(migration_sql)
                            # Записываем что миграция применена
                            await cur.execute(
                                "INSERT INTO migrations (filename) VALUES (%s)",
                                (migration_file,)
                            )
                            await conn.commit()
                            logger.info(f"Миграция {migration_file} успешно применена")
                        except Exception as e:
                            await conn.rollback()
                            logger.error(f"Ошибка при применении миграции {migration_file}: {e}")
                            raise
                    else:
                        logger.info(f"Миграция {migration_file} уже применена")
                else:
                    logger.warning(f"Файл миграции {migration_path} не найден")
    
    logger.info("Миграции для заявок применены")

if __name__ == "__main__":
    asyncio.run(run_applications_migrations())
