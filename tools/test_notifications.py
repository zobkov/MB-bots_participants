#!/usr/bin/env python3
"""
Утилита для тестирования системы уведомлений админов.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import load_config
from app.infrastructure.logging import setup_logging
from app.infrastructure.telegram_logging import start_log_worker, get_log_context
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


async def test_notifications():
    """Тестирование уведомлений администраторов"""
    
    # Загружаем конфигурацию
    config = load_config()
    
    if not config.logging.admin_ids:
        print("❌ ADMIN_IDS не настроен в .env")
        print("Добавьте ADMIN_IDS=your_user_id в .env файл")
        return
    
    print(f"🔧 Настройка системы уведомлений...")
    print(f"📱 Админы: {config.logging.admin_ids}")
    
    # Настраиваем логирование
    setup_logging(
        log_level=config.logging.level,
        log_dir=config.logging.log_dir,
        console_output=config.logging.console_output,
        file_prefix=config.logging.file_prefix,
        admin_ids=config.logging.admin_ids
    )
    
    # Создаем бота
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Запускаем воркер уведомлений
    log_worker_task = await start_log_worker(bot, config.logging.admin_ids)
    
    try:
        print("🧪 Запуск тестов уведомлений...")
        
        # Имитируем контекст пользователя
        log_ctx = get_log_context()
        test_context = {
            "user_id": 123456789,
            "chat_id": -100123456789,
            "update_type": "Message",
            "handler": "test_handler"
        }
        
        token = log_ctx.set(test_context)
        
        try:
            logger = logging.getLogger("test")
            
            print("📤 Тестируем ERROR уведомление...")
            logger.error("Тестовая ошибка для проверки уведомлений")
            await asyncio.sleep(2)
            
            print("📤 Тестируем CRITICAL уведомление...")
            logger.critical("Критическая ошибка для проверки уведомлений")
            await asyncio.sleep(2)
            
            print("📤 Тестируем WARNING накопление (6 штук)...")
            for i in range(6):
                logger.warning(f"Тестовое предупреждение #{i+1}")
                await asyncio.sleep(0.5)
            
            print("⏳ Ожидание обработки уведомлений...")
            await asyncio.sleep(5)
            
            print("✅ Тесты завершены!")
            print("Проверьте Telegram - вы должны получить:")
            print("  • 1 уведомление ERROR")  
            print("  • 1 уведомление CRITICAL")
            print("  • 1 сводку WARNING (6 предупреждений)")
            
        finally:
            log_ctx.reset(token)
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        
    finally:
        # Останавливаем воркер
        if log_worker_task and not log_worker_task.done():
            log_worker_task.cancel()
            try:
                await log_worker_task
            except asyncio.CancelledError:
                pass
        
        await bot.session.close()


async def test_warning_threshold():
    """Тестирование порога WARNING уведомлений"""
    
    config = load_config()
    
    if not config.logging.admin_ids:
        print("❌ ADMIN_IDS не настроен в .env")
        return
    
    print("🧪 Тестирование порога WARNING (должно быть >5 за минуту)...")
    
    # Настраиваем логирование
    setup_logging(
        log_level="WARNING",  # Только WARNING и выше
        log_dir=config.logging.log_dir,
        console_output=True,
        file_prefix="test-warning",
        admin_ids=config.logging.admin_ids
    )
    
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    log_worker_task = await start_log_worker(bot, config.logging.admin_ids)
    
    try:
        logger = logging.getLogger("warning_test")
        
        print("📤 Отправляем 4 WARNING (не должно вызвать уведомление)...")
        for i in range(4):
            logger.warning(f"WARNING тест #{i+1} (не должно быть уведомления)")
            await asyncio.sleep(1)
        
        await asyncio.sleep(3)
        print("✅ 4 WARNING отправлено (уведомления быть не должно)")
        
        print("📤 Отправляем еще 2 WARNING (должно вызвать уведомление)...")
        for i in range(2):
            logger.warning(f"WARNING тест #{i+5} (должно вызвать уведомление)")
            await asyncio.sleep(1)
        
        await asyncio.sleep(5)
        print("✅ Тест завершен! Проверьте Telegram - должно быть 1 уведомление о 6 WARNING")
        
    finally:
        if log_worker_task and not log_worker_task.done():
            log_worker_task.cancel()
            try:
                await log_worker_task
            except asyncio.CancelledError:
                pass
        
        await bot.session.close()


async def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test admin notifications")
    parser.add_argument("--warnings-only", action="store_true", 
                       help="Test only WARNING threshold")
    
    args = parser.parse_args()
    
    if args.warnings_only:
        await test_warning_threshold()
    else:
        await test_notifications()


if __name__ == "__main__":
    asyncio.run(main())