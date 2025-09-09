#!/usr/bin/env python3
"""
Скрипт для применения миграций к базе данных приложений
"""
import asyncio
import psycopg
import logging
import os
from config.config import load_config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='#%(levelname)-8s [%(asctime)s] - %(filename)s:%(lineno)d - %(name)s:%(funcName)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_migrations():
    """Применяет все миграции к базе данных приложений"""
    logger.info("Загрузка конфигурации")
    config = load_config()
    
    # Подключение к базе данных приложений (не пользователей!)
    connection_string = f"postgresql://{config.db_applications.user}:{config.db_applications.password}@{config.db_applications.host}:{config.db_applications.port}/{config.db_applications.database}"
    
    logger.info("Подключение к базе данных приложений")
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
            
            # Читаем и применяем миграции
            migrations_dir = "migrations"
            
            if os.path.exists(migrations_dir):
                migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
                logger.info(f"Найдены файлы миграций: {migration_files}")
                
                for migration_file in migration_files:
                    if migration_file not in applied_migrations:
                        logger.info(f"Применяем миграцию: {migration_file}")
                        
                        migration_path = os.path.join(migrations_dir, migration_file)
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
                logger.error("Папка migrations не найдена")
                return
    
    logger.info("Все миграции успешно применены")

if __name__ == "__main__":
    asyncio.run(run_migrations())
