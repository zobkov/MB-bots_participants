#!/usr/bin/env python3
"""
Утилита для просмотра и управления логами бота.
"""

import argparse
import sys
import os
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.logging import get_log_files_info, cleanup_old_logs

try:
    from config.config import load_config
    config = load_config()
    default_log_dir = config.logging.log_dir
    default_retention_days = config.logging.retention_days
except Exception:
    # Fallback значения если конфигурация недоступна
    default_log_dir = "logs"
    default_retention_days = 30


def list_logs(log_dir: str = "logs"):
    """Показать список файлов логов"""
    log_files = get_log_files_info(log_dir)
    
    if not log_files:
        print(f"No log files found in '{log_dir}' directory")
        return
    
    print(f"Log files in '{log_dir}' directory:")
    print("-" * 80)
    print(f"{'File Name':<25} {'Size (KB)':<12} {'Modified':<20} {'Created':<20}")
    print("-" * 80)
    
    for log_file in log_files:
        size_kb = log_file['size'] / 1024
        modified = log_file['modified'].strftime("%Y-%m-%d %H:%M:%S")
        created = log_file['created'].strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"{log_file['name']:<25} {size_kb:<12.1f} {modified:<20} {created:<20}")


def show_log(log_dir: str, filename: str, lines: int = 50, follow: bool = False):
    """Показать содержимое лог файла"""
    log_path = Path(log_dir) / filename
    
    if not log_path.exists():
        print(f"Log file '{filename}' not found in '{log_dir}' directory")
        return
    
    try:
        if follow:
            # Режим tail -f
            import time
            with open(log_path, 'r', encoding='utf-8') as f:
                # Переходим в конец файла
                f.seek(0, 2)
                print(f"Following log file: {filename} (Press Ctrl+C to stop)")
                print("-" * 80)
                
                try:
                    while True:
                        line = f.readline()
                        if line:
                            print(line.rstrip())
                        else:
                            time.sleep(0.1)
                except KeyboardInterrupt:
                    print("\nStopped following log file")
        else:
            # Показать последние N строк
            with open(log_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                
            if lines > len(all_lines):
                lines = len(all_lines)
            
            print(f"Last {lines} lines from {filename}:")
            print("-" * 80)
            
            for line in all_lines[-lines:]:
                print(line.rstrip())
                
    except Exception as e:
        print(f"Error reading log file: {e}")


def clean_logs(log_dir: str, keep_days: int):
    """Очистить старые логи"""
    deleted_count = cleanup_old_logs(log_dir, keep_days)
    print(f"Deleted {deleted_count} old log files (older than {keep_days} days)")


def main():
    parser = argparse.ArgumentParser(description="Log management utility for the bot")
    parser.add_argument("--log-dir", default=default_log_dir, help=f"Log directory path (default: {default_log_dir})")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Команда list
    list_parser = subparsers.add_parser("list", help="List all log files")
    
    # Команда show
    show_parser = subparsers.add_parser("show", help="Show log file content")
    show_parser.add_argument("filename", help="Log file name")
    show_parser.add_argument("--lines", "-n", type=int, default=50, help="Number of lines to show")
    show_parser.add_argument("--follow", "-f", action="store_true", help="Follow log file (like tail -f)")
    
    # Команда clean
    clean_parser = subparsers.add_parser("clean", help="Clean old log files")
    clean_parser.add_argument("--keep-days", type=int, default=default_retention_days, help=f"Days to keep logs (default: {default_retention_days})")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_logs(args.log_dir)
    elif args.command == "show":
        show_log(args.log_dir, args.filename, args.lines, args.follow)
    elif args.command == "clean":
        clean_logs(args.log_dir, args.keep_days)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()