#!/usr/bin/env python3
"""
Улучшенная версия скрипта для анализа незаполненных анкет из Redis
"""

import asyncio
import json
import csv
import logging
from datetime import datetime
from collections import defaultdict
from analyze_redis_dialogs import RedisDialogAnalyzer, RedisConfig

logger = logging.getLogger(__name__)

async def generate_summary_report(analyzer: RedisDialogAnalyzer, label: str):
    """Создание сводного отчета"""
    user_states = await analyzer.analyze_all_dialogs()
    
    if not user_states:
        print(f"📋 Отчет для {label}: Пользователи в процессе заполнения анкет не найдены")
        return
    
    # Подготовка статистики
    completion_ranges = defaultdict(list)
    state_counts = defaultdict(int)
    missing_field_counts = defaultdict(int)
    
    for user_state in user_states:
        # Категоризация по заполненности
        completion = user_state.completion_percentage
        if completion <= 25:
            completion_ranges['🔴 Критично (0-25%)'].append(user_state)
        elif completion <= 50:
            completion_ranges['🟡 Низко (25-50%)'].append(user_state)
        elif completion <= 75:
            completion_ranges['🟠 Средне (50-75%)'].append(user_state)
        else:
            completion_ranges['🟢 Высоко (75-100%)'].append(user_state)
        
        # Подсчет состояний
        state_counts[user_state.state] += 1
        
        # Анализ недостающих полей
        for field in user_state.missing_fields:
            missing_field_counts[field] += 1
    
    # Создание отчета
    report_filename = f"summary_report_{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(f"📋 СВОДНЫЙ ОТЧЕТ ПО НЕЗАПОЛНЕННЫМ АНКЕТАМ\n")
        f.write(f"Сервер: {label}\n")
        f.write(f"Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")
        
        f.write(f"📊 ОБЩАЯ СТАТИСТИКА:\n")
        f.write(f"Всего пользователей в процессе заполнения: {len(user_states)}\n\n")
        
        f.write(f"📈 РАСПРЕДЕЛЕНИЕ ПО ЗАПОЛНЕННОСТИ:\n")
        for category, users in completion_ranges.items():
            f.write(f"{category}: {len(users)} чел.\n")
            for user in users[:3]:  # Показываем первых 3 в каждой категории
                f.write(f"  • {user.user_id}: {user.dialog_data.get('full_name', 'Имя не указано')} "
                       f"({user.completion_percentage:.1f}%)\n")
            if len(users) > 3:
                f.write(f"  ... и еще {len(users) - 3} пользователей\n")
        f.write("\n")
        
        f.write(f"🎯 СОСТОЯНИЯ ДИАЛОГОВ:\n")
        for state, count in sorted(state_counts.items()):
            f.write(f"{state}: {count} чел.\n")
        f.write("\n")
        
        f.write(f"❌ ТОП-10 НЕДОСТАЮЩИХ ПОЛЕЙ:\n")
        top_missing = sorted(missing_field_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for field, count in top_missing:
            f.write(f"{field}: {count} чел.\n")
        f.write("\n")
        
        f.write(f"🚨 КРИТИЧЕСКИЕ СЛУЧАИ (заполненность < 25%):\n")
        critical_users = completion_ranges['🔴 Критично (0-25%)']
        if critical_users:
            for user in critical_users:
                f.write(f"User {user.user_id}: {user.dialog_data.get('full_name', 'Имя не указано')}\n")
                f.write(f"  Состояние: {user.state}\n")
                f.write(f"  Заполненность: {user.completion_percentage:.1f}%\n")
                f.write(f"  Недостает: {', '.join(user.missing_fields)}\n\n")
        else:
            f.write("Критических случаев не найдено.\n\n")
    
    print(f"📄 Сводный отчет сохранен в файл: {report_filename}")
    return report_filename

async def main():
    """Основная функция для запуска анализа локального и production серверов"""
    
    print("🚀 Запуск комплексного анализа незаполненных анкет")
    print("=" * 60)
    
    # Анализ локального сервера
    print("\n🏠 Анализ локального сервера...")
    local_config = RedisConfig(host='localhost', port=6379)
    local_analyzer = RedisDialogAnalyzer(local_config)
    
    try:
        await local_analyzer.connect()
        local_filename = await local_analyzer.export_to_csv("local")
        await generate_summary_report(local_analyzer, "local")
        print(f"✅ Локальный анализ завершен: {local_filename}")
    except Exception as e:
        print(f"❌ Ошибка анализа локального сервера: {e}")
    finally:
        await local_analyzer.disconnect()
    
    print("\n" + "=" * 60)
    
    # Анализ production сервера
    print("\n🌐 Анализ production сервера...")
    prod_config = RedisConfig(host='45.90.217.194', port=6380)
    prod_analyzer = RedisDialogAnalyzer(prod_config)
    
    try:
        await prod_analyzer.connect()
        prod_filename = await prod_analyzer.export_to_csv("production")
        await generate_summary_report(prod_analyzer, "production")
        print(f"✅ Production анализ завершен: {prod_filename}")
    except Exception as e:
        print(f"❌ Ошибка анализа production сервера: {e}")
    finally:
        await prod_analyzer.disconnect()
    
    print("\n🎉 Анализ завершен! Проверьте созданные файлы.")

if __name__ == "__main__":
    asyncio.run(main())
