#!/usr/bin/env python3
"""
Скрипт для проверки полей приоритетов в БД заявок
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

async def check_priority_fields():
    """Проверяет поля приоритетов в БД заявок"""
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
            # Проверяем поля приоритетов в существующих записях
            query = """
                SELECT 
                    user_id, full_name,
                    department_1, subdepartment_1, position_1,
                    department_2, subdepartment_2, position_2,
                    department_3, subdepartment_3, position_3,
                    created, updated
                FROM applications 
                ORDER BY id DESC 
                LIMIT 5
            """
            cursor = await conn.execute(query)
            
            applications = await cursor.fetchall()
            logger.info(f"🔍 Проверка полей приоритетов в {len(applications)} заявках:")
            
            for i, app in enumerate(applications, 1):
                user_id, full_name = app[0], app[1]
                dept1, subdept1, pos1 = app[2], app[3], app[4]
                dept2, subdept2, pos2 = app[5], app[6], app[7]
                dept3, subdept3, pos3 = app[8], app[9], app[10]
                created, updated = app[11], app[12]
                
                logger.info(f"\n📋 Заявка {i} (User ID: {user_id}, {full_name}):")
                logger.info(f"   📅 Создана: {created}")
                logger.info(f"   🔄 Обновлена: {updated}")
                
                # Новая система приоритетов
                logger.info(f"   🎯 Система приоритетов:")
                logger.info(f"      1-й приоритет: {dept1 or 'NULL'} / {subdept1 or 'NULL'} - {pos1 or 'NULL'}")
                logger.info(f"      2-й приоритет: {dept2 or 'NULL'} / {subdept2 or 'NULL'} - {pos2 or 'NULL'}")
                logger.info(f"      3-й приоритет: {dept3 or 'NULL'} / {subdept3 or 'NULL'} - {pos3 or 'NULL'}")
                
                # Анализ
                has_new_data = any([dept1, pos1, dept2, pos2, dept3, pos3])
                
                if has_new_data:
                    logger.info(f"   ✅ ОК: Использует систему приоритетов")
                else:
                    logger.info(f"   ❌ ПУСТО: Нет данных в системе приоритетов")
            
            # Статистика по полям
            stats_query = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(department_1) as has_dept_1,
                    COUNT(subdepartment_1) as has_subdept_1,
                    COUNT(position_1) as has_pos_1,
                    COUNT(department_2) as has_dept_2,
                    COUNT(subdepartment_2) as has_subdept_2,
                    COUNT(position_2) as has_pos_2,
                    COUNT(department_3) as has_dept_3,
                    COUNT(subdepartment_3) as has_subdept_3,
                    COUNT(position_3) as has_pos_3
                FROM applications;
            """
            cursor = await conn.execute(stats_query)
            
            stats = await cursor.fetchone()
            total = stats[0]
            
            logger.info(f"\n📊 СТАТИСТИКА ПО ПОЛЯМ:")
            logger.info(f"   📋 Всего заявок: {total}")
            logger.info(f"   🎯 Система приоритетов:")
            logger.info(f"      - department_1: {stats[1]}/{total}")
            logger.info(f"      - subdepartment_1: {stats[2]}/{total}")
            logger.info(f"      - position_1: {stats[3]}/{total}")
            logger.info(f"      - department_2: {stats[4]}/{total}")
            logger.info(f"      - subdepartment_2: {stats[5]}/{total}")
            logger.info(f"      - position_2: {stats[6]}/{total}")
            logger.info(f"      - department_3: {stats[7]}/{total}")
            logger.info(f"      - subdepartment_3: {stats[8]}/{total}")
            logger.info(f"      - position_3: {stats[9]}/{total}")
            
            if stats[1] == 0 and stats[3] == 0:
                logger.error(f"\n❌ КРИТИЧЕСКАЯ ПРОБЛЕМА:")
                logger.error(f"   Ни одна заявка не использует систему приоритетов!")
                logger.error(f"   Код сохранения НЕ обновлен для работы с новыми полями.")
            else:
                logger.info(f"\n✅ СИСТЕМА РАБОТАЕТ:")
                logger.info(f"   Используется система приоритетов")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке БД заявок: {e}")

if __name__ == "__main__":
    asyncio.run(check_priority_fields())
