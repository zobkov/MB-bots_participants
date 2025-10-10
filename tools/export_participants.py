#!/usr/bin/env python3
"""Export participants to CSV file"""

import asyncio
import csv
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import load_config
from app.infrastructure.database import DatabaseManager


async def export_to_csv():
    """Export all users and their registrations to CSV"""
    config = load_config()
    
    # Initialize managers
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    try:
        # Get all users
        async with db_manager.sessionmaker() as session:
            from sqlalchemy import select
            from app.infrastructure.database.models import User
            
            result = await session.execute(
                select(User).order_by(User.id)
            )
            users = result.scalars().all()
        
        if not users:
            print("Пользователи не найдены.")
            return
        
        # Create CSV file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"participants_{timestamp}.csv"
        
        case_names = {
            1: "ВТБ",
            2: "Алабуга", 
            3: "Б1",
            4: "Северсталь",
            5: "Альфа"
        }
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow([
                'User ID',
                'Username', 
                'Visible Name',
                'Debate Case',
                'Case Name'
            ])
            
            # Write data
            for user in users:
                username = user.username if user.username else ""
                case_name = case_names.get(user.debate_reg, "") if user.debate_reg else ""
                
                writer.writerow([
                    user.id,
                    username,
                    user.visible_name,
                    user.debate_reg if user.debate_reg else "",
                    case_name
                ])
        
        print(f"✅ Экспорт завершен: {filename}")
        print(f"Экспортировано пользователей: {len(users)}")
        
        # Statistics
        registered_count = sum(1 for user in users if user.debate_reg)
        print(f"Зарегистрированных на дебаты: {registered_count}")
        
        # Count by cases
        case_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for user in users:
            if user.debate_reg:
                case_counts[user.debate_reg] += 1
        
        print("\nПо кейсам:")
        for case_num, case_name in case_names.items():
            print(f"  {case_name}: {case_counts[case_num]}")
        
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(export_to_csv())