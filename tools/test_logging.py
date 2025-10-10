#!/usr/bin/env python3
"""
Утилита для тестирования различных уровней логирования.
"""

import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import load_config
from app.infrastructure.logging import setup_logging
import logging


def test_logging_levels():
    """Тестирование всех уровней логирования"""
    
    # Загружаем конфигурацию
    config = load_config()
    
    # Настраиваем логирование
    setup_logging(
        log_level=config.logging.level,
        log_dir=config.logging.log_dir,
        console_output=config.logging.console_output,
        file_prefix=config.logging.file_prefix
    )
    
    print(f"Тестирование логирования с уровнем: {config.logging.level}")
    print(f"Логи сохраняются в: {config.logging.log_dir}")
    print(f"Консольный вывод: {config.logging.console_output}")
    print("-" * 60)
    
    # Тестируем все уровни
    logging.debug("🔍 DEBUG: Детальная отладочная информация")
    logging.info("ℹ️ INFO: Общая информация о работе")
    logging.warning("⚠️ WARNING: Предупреждение о потенциальных проблемах")
    logging.error("❌ ERROR: Ошибка, которая не останавливает работу")
    logging.critical("🚨 CRITICAL: Критическая ошибка!")
    
    print("-" * 60)
    print("Тестирование завершено!")
    
    # Показываем какие сообщения должны отображаться
    levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    current_level_index = levels.index(config.logging.level.upper())
    
    print(f"\nПри уровне {config.logging.level} отображаются сообщения:")
    for i, level in enumerate(levels):
        if i >= current_level_index:
            print(f"  ✅ {level}")
        else:
            print(f"  ❌ {level} (скрыто)")


def test_different_levels():
    """Тестирование с разными уровнями логирования"""
    
    levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    for level in levels:
        print(f"\n{'='*60}")
        print(f"Тестирование уровня: {level}")
        print('='*60)
        
        setup_logging(
            log_level=level,
            log_dir="logs",
            console_output=True,
            file_prefix=f"test-{level.lower()}"
        )
        
        logging.debug(f"DEBUG сообщение при уровне {level}")
        logging.info(f"INFO сообщение при уровне {level}")
        logging.warning(f"WARNING сообщение при уровне {level}")
        logging.error(f"ERROR сообщение при уровне {level}")
        logging.critical(f"CRITICAL сообщение при уровне {level}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test logging levels")
    parser.add_argument("--all-levels", action="store_true", 
                       help="Test all logging levels")
    
    args = parser.parse_args()
    
    if args.all_levels:
        test_different_levels()
    else:
        test_logging_levels()