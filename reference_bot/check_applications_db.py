#!/usr/bin/env python3
"""
Скрипт для проверки данных в БД заявок
"""
import asyncio
import logging
from config.config import load_config
from app.infrastructure.database.connect_to_pg import get_pg_pool

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='#%(levelname)-8s [%(asctime)s] - %(filename)s:%(lineno)d - %(name)s:%(funcName)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_applications_db():
    """Проверяет данные в БД заявок"""
    try:
        # Загружаем конфигурацию
        config = load_config()
        
        # Подключаемся к БД заявок
        pool = await get_pg_pool(
            db_name=config.db_applications.database,
            host=config.db_applications.host,
            port=config.db_applications.port,
            user=config.db_applications.user,
            password=config.db_applications.password
        )
        
        async with pool.connection() as conn:
            # Проверяем структуру таблицы applications
            cursor = await conn.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'applications' 
                ORDER BY ordinal_position;
            """)
            
            columns = await cursor.fetchall()
            logger.info("Структура таблицы applications:")
            for col in columns:
                logger.info(f"  {col[0]} | {col[1]} | nullable: {col[2]} | default: {col[3]}")
            
            # Проверяем данные в таблице (основные поля, без статуса)
            cursor = await conn.execute("""
            SELECT 
                user_id, full_name, 
                COALESCE(department_1, 'NULL') as dept1,
                COALESCE(subdepartment_1, 'NULL') as subdept1,
                COALESCE(position_1, 'Неизвестная позиция') as pos1,
                created
            FROM applications 
            ORDER BY created DESC 
            LIMIT 10
        """)
            
            applications = await cursor.fetchall()
        logger.info(f"🔍 Последние 10 заявок:")
        
        for i, app in enumerate(applications, 1):
            user_id, full_name, dept1, subdept1, pos1, created = app
            dept_display = f"{dept1}" + (f" / {subdept1}" if subdept1 != 'NULL' else "")
            logger.info(f"📋 {i}. User {user_id} ({full_name}): {dept_display} - {pos1} | {created}")

            # Дополнительно: обзор по таблице users
            cursor = await conn.execute("""
                SELECT submission_status, COUNT(*)
                FROM users
                GROUP BY submission_status
                ORDER BY submission_status;
            """)
            groups = await cursor.fetchall()
            logger.info("\nПользователи по статусам отправки заявки:")
            for status, cnt in groups:
                logger.info(f"  {status}: {cnt}")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке БД заявок: {e}")

if __name__ == "__main__":
    asyncio.run(check_applications_db())
