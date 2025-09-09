#!/usr/bin/env python3
"""
Скрипт для автоматической миграции StaticMedia на оптимизированные версии.
Заменяет StaticMedia(path="...") на create_optimized_static_media("...").

Использование:
    python migrate_static_media.py [--dry-run] [--file=path/to/file.py]
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_static_media_usage(file_path: Path) -> List[Tuple[int, str, str, str]]:
    """
    Найти все использования StaticMedia в файле.
    
    Returns:
        List of (line_number, original_line, path_in_line, relative_path)
    """
    matches = []
    
    if not file_path.exists():
        return matches
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️ Не удалось прочитать {file_path}: {e}")
        return matches
    
    # Паттерн для поиска StaticMedia с path
    pattern = r'StaticMedia\s*\(\s*path\s*=\s*["\']([^"\']+)["\']'
    
    for line_num, line in enumerate(lines, 1):
        match = re.search(pattern, line)
        if match:
            path_in_code = match.group(1)
            
            # Извлекаем относительный путь от папки images
            if "app/bot/assets/images/" in path_in_code:
                relative_path = path_in_code.replace("app/bot/assets/images/", "")
                matches.append((line_num, line.strip(), path_in_code, relative_path))
    
    return matches


def migrate_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Мигрировать файл на использование оптимизированной системы.
    
    Returns:
        True если файл был изменен
    """
    matches = find_static_media_usage(file_path)
    
    if not matches:
        return False
    
    print(f"📁 Файл: {file_path}")
    print(f"   Найдено {len(matches)} использований StaticMedia")
    
    if dry_run:
        for line_num, original_line, path_in_code, relative_path in matches:
            print(f"   Строка {line_num}: {original_line}")
            print(f"   → create_optimized_static_media(\"{relative_path}\")")
        return False
    
    # Читаем файл
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Ошибка чтения {file_path}: {e}")
        return False
    
    # Выполняем замены
    modified = False
    
    for _, _, path_in_code, relative_path in matches:
        escaped_path = re.escape(path_in_code)
        old_pattern = r'StaticMedia\(\s*path\s*=\s*["\']' + escaped_path + r'["\']\s*\)'
        new_replacement = f'create_optimized_static_media("{relative_path}")'
        
        new_content = re.sub(old_pattern, new_replacement, content)
        
        if new_content != content:
            content = new_content
            modified = True
            print(f"   ✅ Заменено: {path_in_code} → {relative_path}")
    
    # Добавляем импорт если его нет
    import_line = "from app.utils.optimized_dialog_widgets import create_optimized_static_media"
    
    if import_line not in content and modified:
        # Ищем место для добавления импорта (после других импортов)
        lines = content.split('\n')
        insert_pos = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                insert_pos = i + 1
        
        lines.insert(insert_pos, import_line)
        content = '\n'.join(lines)
        print(f"   ✅ Добавлен импорт")
    
    # Сохраняем файл
    if modified:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   💾 Файл сохранен")
        except Exception as e:
            print(f"   ❌ Ошибка сохранения: {e}")
            return False
    
    return modified


def find_dialog_files() -> List[Path]:
    """Найти все файлы диалогов"""
    dialog_paths = []
    
    dialogs_dir = Path("app/bot/dialogs")
    if dialogs_dir.exists():
        for py_file in dialogs_dir.rglob("*.py"):
            dialog_paths.append(py_file)
    
    return dialog_paths


def main():
    parser = argparse.ArgumentParser(description="Миграция StaticMedia на оптимизированные версии")
    parser.add_argument("--dry-run", action="store_true", help="Только показать что будет изменено")
    parser.add_argument("--file", help="Мигрировать конкретный файл")
    
    args = parser.parse_args()
    
    if args.file:
        files_to_process = [Path(args.file)]
    else:
        files_to_process = find_dialog_files()
    
    if not files_to_process:
        print("❌ Файлы для обработки не найдены")
        return
    
    print(f"🔍 Найдено файлов для проверки: {len(files_to_process)}")
    
    if args.dry_run:
        print("🧪 Режим dry-run: изменения не будут сохранены")
    
    print()
    
    modified_count = 0
    total_files_with_changes = 0
    
    for file_path in files_to_process:
        matches = find_static_media_usage(file_path)
        
        if matches:
            total_files_with_changes += 1
            modified_count += len(matches)
            
            if migrate_file(file_path, args.dry_run):
                print(f"✅ {file_path} мигрирован")
            elif args.dry_run:
                print(f"🔍 {file_path} будет мигрирован")
            print()
    
    print("📊 Итоги:")
    print(f"   Файлов с изменениями: {total_files_with_changes}")
    print(f"   Всего замен: {modified_count}")
    
    if not args.dry_run and total_files_with_changes > 0:
        print("\n✅ Миграция завершена!")
        print("📋 Не забудьте:")
        print("   1. Перезапустить бота для применения изменений")
        print("   2. Проверить работу оптимизированных диалогов")
    elif args.dry_run and total_files_with_changes > 0:
        print(f"\n🔄 Для выполнения миграции запустите:")
        print(f"   python {sys.argv[0]} # без --dry-run")


if __name__ == "__main__":
    # Проверяем, что мы в корне проекта
    if not Path("app/bot/dialogs").exists():
        print("❌ Запустите скрипт из корня проекта")
        sys.exit(1)
    
    main()
