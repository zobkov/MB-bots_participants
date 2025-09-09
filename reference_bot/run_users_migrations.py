#!/usr/bin/env python3
"""
Скрипт для применения миграций к базе данных пользователей
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

async def run_users_migrations():
    """Применяет миграции для пользователей"""
    logger.info("Загрузка конфигурации")
    config = load_config()
    
    # Подключение к базе данных пользователей
    connection_string = f"postgresql://{config.db.user}:{config.db.password}@{config.db.host}:{config.db.port}/{config.db.database}"
    
    logger.info("Подключение к базе данных пользователей")
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
            
            # Читаем и применяем миграцию пользователей
            import os
            migrations_dir = "migrations"
            
            migration_file = "001_create_users_table.sql"
            migration_path = os.path.join(migrations_dir, migration_file)
            
            if os.path.exists(migration_path):
                if migration_file not in applied_migrations:
                    logger.info(f"Применяем миграцию: {migration_file}")
                    
                    with open(migration_path, 'r', encoding='utf-8') as f:
                        migration_sql = f.read()
                    #!/usr/bin/env python3
                    """
                    DEPRECATED: Users migrations are now part of the applications database.

                    Use run_applications_migrations.py instead. This script is kept for
                    backward compatibility but does nothing.
                    """
                    if __name__ == "__main__":
                        print("run_users_migrations.py is deprecated. Use run_applications_migrations.py instead.")
                        await conn.rollback()
