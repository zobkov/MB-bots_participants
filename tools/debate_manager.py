#!/usr/bin/env python3
"""Utility script for managing debate registrations"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import load_config
from app.infrastructure.database import DatabaseManager, RedisManager


async def show_statistics():
    """Show current debate registration statistics"""
    config = load_config()
    
    # Initialize managers
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    redis_manager = RedisManager(config.redis)
    await redis_manager.init()
    
    try:
        # Get data from database and Redis
        db_counts = await db_manager.get_debate_registrations_count()
        redis_counts = await redis_manager.get_debate_counts()
        remaining = await redis_manager.get_remaining_slots()
        
        print("=" * 60)
        print("СТАТИСТИКА РЕГИСТРАЦИИ НА ДЕБАТЫ")
        print("=" * 60)
        
        case_names = {
            1: "ВТБ",
            2: "Алабуга", 
            3: "Б1",
            4: "Северсталь",
            5: "Альфа"
        }
        
        for case_num in range(1, 6):
            name = case_names[case_num]
            db_count = db_counts[case_num]
            redis_count = redis_counts[case_num]
            remaining_count = remaining[case_num]
            
            print(f"\nКейс {case_num} ({name}):")
            print(f"  БД:     {db_count} регистраций")
            print(f"  Redis:  {redis_count} регистраций")
            print(f"  Осталось мест: {remaining_count}")
            
            if db_count != redis_count:
                print(f"  ⚠️  НЕСООТВЕТСТВИЕ! Требуется синхронизация")
        
        # Show limits and shared constraints
        print("\n" + "=" * 60)
        print("ЛИМИТЫ И ОГРАНИЧЕНИЯ")
        print("=" * 60)
        print(f"ВТБ: {db_counts[1]}/32")
        print(f"Алабуга + Б1: {db_counts[2] + db_counts[3]}/41")
        print(f"Северсталь + Альфа: {db_counts[4] + db_counts[5]}/42")
        
    finally:
        await db_manager.close()
        await redis_manager.close()


async def sync_redis_with_db():
    """Sync Redis cache with database"""
    config = load_config()
    
    # Initialize managers
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    redis_manager = RedisManager(config.redis)
    await redis_manager.init()
    
    try:
        # Get counts from database
        db_counts = await db_manager.get_debate_registrations_count()
        
        # Sync Redis
        await redis_manager.sync_with_database(db_counts)
        
        print("✅ Redis успешно синхронизирован с базой данных")
        print(f"Обновленные данные: {db_counts}")
        
    finally:
        await db_manager.close()
        await redis_manager.close()


async def reset_registrations():
    """Reset all registrations (for testing)"""
    config = load_config()
    
    # Initialize managers
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    redis_manager = RedisManager(config.redis)
    await redis_manager.init()
    
    try:
        # Ask for confirmation
        confirm = input("⚠️  Вы уверены, что хотите сбросить ВСЕ регистрации? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Операция отменена")
            return
        
        # Reset database
        async with db_manager.sessionmaker() as session:
            from sqlalchemy import update
            from app.infrastructure.database.models import User
            
            await session.execute(
                update(User).values(debate_reg=None)
            )
            await session.commit()
        
        # Reset Redis
        empty_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        await redis_manager.sync_with_database(empty_counts)
        
        print("✅ Все регистрации сброшены")
        
    finally:
        await db_manager.close()
        await redis_manager.close()


async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python tools/debate_manager.py stats     - показать статистику")
        print("  python tools/debate_manager.py sync      - синхронизировать Redis с БД")
        print("  python tools/debate_manager.py reset     - сбросить все регистрации")
        return
    
    command = sys.argv[1]
    
    if command == "stats":
        await show_statistics()
    elif command == "sync":
        await sync_redis_with_db()
    elif command == "reset":
        await reset_registrations()
    else:
        print(f"Неизвестная команда: {command}")


if __name__ == "__main__":
    asyncio.run(main())