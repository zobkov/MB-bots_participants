#!/usr/bin/env python3
"""Utility script for viewing users and their registrations"""

import asyncio
import sys
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import load_config
from app.infrastructure.database import DatabaseManager
from app.infrastructure.database.models import User
from sqlalchemy import select, func


async def list_all_users():
    """List all users in the database"""
    config = load_config()
    
    # Initialize managers
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    try:
        async with db_manager.sessionmaker() as session:
            result = await session.execute(
                select(User).order_by(User.id)
            )
            users = result.scalars().all()
            
            if not users:
                print("Пользователи не найдены.")
                return
            
            print("=" * 80)
            print("ВСЕ ПОЛЬЗОВАТЕЛИ")
            print("=" * 80)
            print(f"{'ID':<12} {'Username':<20} {'Visible Name':<25} {'Debate Case':<12}")
            print("-" * 80)
            
            case_names = {
                1: "ВТБ",
                2: "Алабуга", 
                3: "Б1",
                4: "Северсталь",
                5: "Альфа"
            }
            
            for user in users:
                username = f"@{user.username}" if user.username else "—"
                case_name = case_names.get(user.debate_reg, "—") if user.debate_reg else "—"
                
                print(f"{user.id:<12} {username:<20} {user.visible_name:<25} {case_name:<12}")
            
            print(f"\nВсего пользователей: {len(users)}")
            
    finally:
        await db_manager.close()


async def list_registered_users():
    """List only users registered for debates"""
    config = load_config()
    
    # Initialize managers
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    try:
        async with db_manager.sessionmaker() as session:
            result = await session.execute(
                select(User)
                .where(User.debate_reg.isnot(None))
                .order_by(User.debate_reg, User.id)
            )
            users = result.scalars().all()
            
            if not users:
                print("Нет зарегистрированных пользователей.")
                return
            
            print("=" * 80)
            print("ЗАРЕГИСТРИРОВАННЫЕ НА ДЕБАТЫ")
            print("=" * 80)
            
            case_names = {
                1: "ВТБ",
                2: "Алабуга", 
                3: "Б1",
                4: "Северсталь",
                5: "Альфа"
            }
            
            current_case = None
            case_count = 0
            
            for user in users:
                if user.debate_reg != current_case:
                    if current_case is not None:
                        print(f"  Итого: {case_count} человек\n")
                    
                    current_case = user.debate_reg
                    case_count = 0
                    case_name = case_names.get(current_case, "Unknown")
                    print(f"Кейс {current_case} ({case_name}):")
                    print("-" * 40)
                
                username = f"@{user.username}" if user.username else "—"
                print(f"  {user.id:<12} {username:<20} {user.visible_name}")
                case_count += 1
            
            if current_case is not None:
                print(f"  Итого: {case_count} человек")
            
            print(f"\nВсего зарегистрированных: {len(users)}")
            
    finally:
        await db_manager.close()


async def search_user(query: str):
    """Search for a user by ID, username, or name"""
    config = load_config()
    
    # Initialize managers
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    try:
        async with db_manager.sessionmaker() as session:
            # Try to search by ID first
            if query.isdigit():
                user_id = int(query)
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    print_user_details(user)
                    return
            
            # Search by username or visible name
            search_pattern = f"%{query}%"
            result = await session.execute(
                select(User).where(
                    (User.username.ilike(search_pattern)) |
                    (User.visible_name.ilike(search_pattern))
                )
            )
            users = result.scalars().all()
            
            if not users:
                print(f"Пользователи по запросу '{query}' не найдены.")
                return
            
            if len(users) == 1:
                print_user_details(users[0])
            else:
                print(f"Найдено {len(users)} пользователей:")
                print("-" * 60)
                for user in users:
                    username = f"@{user.username}" if user.username else "—"
                    print(f"{user.id:<12} {username:<20} {user.visible_name}")
            
    finally:
        await db_manager.close()


def print_user_details(user: User):
    """Print detailed user information"""
    case_names = {
        1: "ВТБ",
        2: "Алабуга", 
        3: "Б1",
        4: "Северсталь",
        5: "Альфа"
    }
    
    print("=" * 50)
    print("ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ")
    print("=" * 50)
    print(f"ID: {user.id}")
    print(f"Username: @{user.username}" if user.username else "Username: —")
    print(f"Visible Name: {user.visible_name}")
    
    if user.debate_reg:
        case_name = case_names.get(user.debate_reg, "Unknown")
        print(f"Регистрация на дебаты: Кейс {user.debate_reg} ({case_name})")
    else:
        print("Регистрация на дебаты: Не зарегистрирован")


async def get_statistics():
    """Get database statistics"""
    config = load_config()
    
    # Initialize managers
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    try:
        async with db_manager.sessionmaker() as session:
            # Total users
            total_result = await session.execute(
                select(func.count(User.id))
            )
            total_users = total_result.scalar()
            
            # Registered users
            registered_result = await session.execute(
                select(func.count(User.id))
                .where(User.debate_reg.isnot(None))
            )
            registered_users = registered_result.scalar()
            
            # Users per case
            case_result = await session.execute(
                select(User.debate_reg, func.count(User.id))
                .where(User.debate_reg.isnot(None))
                .group_by(User.debate_reg)
            )
            
            case_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for case_num, count in case_result.fetchall():
                case_counts[case_num] = count
            
            print("=" * 50)
            print("СТАТИСТИКА БАЗЫ ДАННЫХ")
            print("=" * 50)
            print(f"Всего пользователей: {total_users}")
            print(f"Зарегистрированных на дебаты: {registered_users}")
            print(f"Не зарегистрированных: {total_users - registered_users}")
            
            print("\nПо кейсам:")
            case_names = {
                1: "ВТБ",
                2: "Алабуга", 
                3: "Б1",
                4: "Северсталь",
                5: "Альфа"
            }
            
            for case_num, case_name in case_names.items():
                count = case_counts[case_num]
                print(f"  {case_name}: {count}")
            
    finally:
        await db_manager.close()


async def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python3 tools/user_manager.py list        - показать всех пользователей")
        print("  python3 tools/user_manager.py registered  - показать зарегистрированных")
        print("  python3 tools/user_manager.py search <query> - найти пользователя")
        print("  python3 tools/user_manager.py stats       - статистика базы данных")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        await list_all_users()
    elif command == "registered":
        await list_registered_users()
    elif command == "search":
        if len(sys.argv) < 3:
            print("Укажите поисковый запрос")
            return
        query = " ".join(sys.argv[2:])
        await search_user(query)
    elif command == "stats":
        await get_statistics()
    else:
        print(f"Неизвестная команда: {command}")


if __name__ == "__main__":
    asyncio.run(main())