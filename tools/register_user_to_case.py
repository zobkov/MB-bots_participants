#!/usr/bin/env python3
"""
Скрипт для записи пользователя на дебат-кейс
Использование: python register_user_to_case.py <user_id> <case_number>
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.infrastructure.database.database import DatabaseManager
from app.infrastructure.database.redis_manager import RedisManager
from config.config import load_config


async def register_user_to_case(user_id: int, case_number: int):
    """
    Записать пользователя на кейс с соблюдением всех процедур
    
    Args:
        user_id: ID пользователя Telegram
        case_number: Номер кейса (1-5)
    """
    print(f"🎯 Начинаю регистрацию пользователя {user_id} на кейс {case_number}...")
    
    # Валидация входных данных
    if not (1 <= case_number <= 5):
        print("❌ Ошибка: Номер кейса должен быть от 1 до 5")
        return False
    
    config = load_config()
    
    # Инициализация менеджеров
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    redis_manager = RedisManager(config.redis)
    await redis_manager.init()
    
    try:
        # 1. Проверить существует ли пользователь
        user = await db_manager.get_user(user_id)
        if not user:
            print(f"❌ Пользователь {user_id} не найден в базе данных")
            print("💡 Сначала создайте пользователя через команду /start в боте")
            return False
        
        print(f"👤 Найден пользователь: {user.visible_name}")
        
        # 2. Проверить текущую регистрацию пользователя
        if user.debate_reg:
            old_case_name = await redis_manager.get_case_name(user.debate_reg)
            print(f"⚠️ Пользователь уже зарегистрирован на кейс {user.debate_reg} ({old_case_name})")
            
            response = input("Хотите перерегистрировать на новый кейс? (y/N): ")
            if response.lower() != 'y':
                print("❌ Операция отменена")
                return False
        
        # 3. Получить название кейса
        case_name = await redis_manager.get_case_name(case_number)
        print(f"📝 Кейс: {case_name}")
        
        # 4. Проверить доступность слотов для регистрации
        can_register, reason = await redis_manager.can_register_for_case(case_number)
        if not can_register:
            print(f"❌ Невозможно зарегистрироваться на кейс {case_number}: {reason}")
            return False
        
        print(f"✅ Слоты доступны для кейса {case_number}")
        
        # 5. Если пользователь уже зарегистрирован, освободить старый слот
        if user.debate_reg:
            print(f"🔄 Освобождаю слот в кейсе {user.debate_reg}...")
            await redis_manager.unregister_from_case(user.debate_reg)
        
        # 6. Зарегистрировать на новый кейс
        print(f"📥 Регистрирую на кейс {case_number}...")
        success = await redis_manager.register_for_case(case_number)
        
        if not success:
            print(f"❌ Не удалось зарегистрироваться на кейс {case_number} (слоты заняты)")
            
            # Если была перерегистрация, нужно вернуть старый слот
            if user.debate_reg:
                print("🔄 Восстанавливаю предыдущую регистрацию...")
                await redis_manager.register_for_case(user.debate_reg)
            
            return False
        
        # 7. Обновить запись в базе данных
        print("💾 Обновляю запись в базе данных...")
        await db_manager.update_user_debate_registration(user_id, case_number)
        
        # 8. Синхронизировать Redis с базой данных (для консистентности)
        print("🔄 Синхронизирую кэш с базой данных...")
        db_counts = await db_manager.get_debate_registrations_count()
        await redis_manager.sync_with_database(db_counts)
        
        # 9. Проверить результат
        updated_user = await db_manager.get_user(user_id)
        if updated_user.debate_reg == case_number:
            remaining_slots = await redis_manager.get_remaining_slots()
            
            print(f"🎉 УСПЕХ! Пользователь зарегистрирован на кейс {case_number}")
            print(f"👤 Пользователь: {updated_user.visible_name} (ID: {user_id})")
            print(f"📝 Кейс: {case_name}")
            print(f"🎯 Осталось слотов для этого кейса: {remaining_slots[case_number]}")
            
            # Показать общую статистику
            print(f"\n📊 Текущая статистика регистрации:")
            case_names = {
                1: "ВТБ",
                2: "Алабуга", 
                3: "Б1",
                4: "Северсталь",
                5: "Альфа"
            }
            
            for i in range(1, 6):
                name = case_names[i]
                registered = db_counts[i]
                remaining = remaining_slots[i]
                print(f"  {name}: {registered} зарегистрировано, {remaining} свободно")
            
            return True
        else:
            print("❌ Ошибка: Регистрация не была сохранена в базе данных")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка во время регистрации: {e}")
        return False
    
    finally:
        # Закрыть соединения
        await redis_manager.close()


async def show_user_info(user_id: int):
    """Показать информацию о пользователе"""
    config = load_config()
    
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    redis_manager = RedisManager(config.redis)
    await redis_manager.init()
    
    try:
        user = await db_manager.get_user(user_id)
        if not user:
            print(f"❌ Пользователь {user_id} не найден")
            return
        
        print(f"\n👤 Информация о пользователе:")
        print(f"ID: {user.id}")
        print(f"Username: @{user.username}" if user.username else "Username: —")
        print(f"Visible Name: {user.visible_name}")
        
        if user.debate_reg:
            case_name = await redis_manager.get_case_name(user.debate_reg)
            print(f"Регистрация: Кейс {user.debate_reg} ({case_name})")
        else:
            print("Регистрация: Не зарегистрирован")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    finally:
        await redis_manager.close()


async def show_stats():
    """Показать статистику регистрации"""
    config = load_config()
    
    db_manager = DatabaseManager(config.db)
    await db_manager.init()
    
    redis_manager = RedisManager(config.redis)
    await redis_manager.init()
    
    try:
        db_counts = await db_manager.get_debate_registrations_count()
        remaining_slots = await redis_manager.get_remaining_slots()
        
        case_names = {
            1: "ВТБ",
            2: "Алабуга", 
            3: "Б1",
            4: "Северсталь",
            5: "Альфа"
        }
        
        print("\n📊 Статистика регистрации на дебаты:")
        for i in range(1, 6):
            name = case_names[i]
            registered = db_counts[i]
            remaining = remaining_slots[i]
            total = registered + remaining
            print(f"  {name}: {registered}/{total} ({remaining} свободно)")
        
        total_registered = sum(db_counts.values())
        print(f"\nВсего зарегистрировано: {total_registered}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    finally:
        await redis_manager.close()


def print_usage():
    """Показать справку по использованию"""
    print("📋 Использование:")
    print("  python register_user_to_case.py <user_id> <case_number>  - Зарегистрировать пользователя")
    print("  python register_user_to_case.py info <user_id>          - Показать информацию о пользователе")
    print("  python register_user_to_case.py stats                   - Показать статистику")
    print("  python register_user_to_case.py help                    - Показать эту справку")
    print()
    print("Примеры:")
    print("  python register_user_to_case.py 123456789 1  # Записать пользователя 123456789 на кейс 1 (ВТБ)")
    print("  python register_user_to_case.py info 123456789  # Показать информацию о пользователе")
    print()
    print("Кейсы:")
    print("  1 - ВТБ")
    print("  2 - Алабуга")
    print("  3 - Б1")
    print("  4 - Северсталь")
    print("  5 - Альфа")


async def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "help":
        print_usage()
        return
    
    elif command == "stats":
        await show_stats()
        return
    
    elif command == "info":
        if len(sys.argv) != 3:
            print("❌ Ошибка: Укажите user_id")
            print("Использование: python register_user_to_case.py info <user_id>")
            return
        
        try:
            user_id = int(sys.argv[2])
            await show_user_info(user_id)
        except ValueError:
            print("❌ Ошибка: user_id должен быть числом")
        return
    
    # Регистрация пользователя
    if len(sys.argv) != 3:
        print("❌ Ошибка: Неверное количество аргументов")
        print_usage()
        return
    
    try:
        user_id = int(sys.argv[1])
        case_number = int(sys.argv[2])
        
        success = await register_user_to_case(user_id, case_number)
        if success:
            print("\n✨ Регистрация завершена успешно!")
        else:
            print("\n💥 Регистрация не удалась")
            sys.exit(1)
            
    except ValueError:
        print("❌ Ошибка: user_id и case_number должны быть числами")
        print_usage()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())