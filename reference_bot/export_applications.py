#!/usr/bin/env python3
"""
Скрипт для экспорта всех заявок из БД в CSV и Google Sheets
"""
import asyncio
import csv
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

from config.config import load_config
from app.infrastructure.database.connect_to_pg import get_pg_pool
from app.services.google_services import setup_google_services

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='#%(levelname)-8s [%(asctime)s] - %(filename)s:%(lineno)d - %(name)s:%(funcName)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def export_applications():
    """Экспортирует все заявки из БД в CSV и Google Sheets"""
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
            # Получаем все заявки из БД
            cursor = await conn.execute("""
                SELECT user_id, status, created, updated,
                       full_name, university, course, phone, email, telegram_username,
                       how_found_kbk, department, position, experience, motivation,
                       resume_local_path, resume_google_drive_url
                FROM applications
                ORDER BY created DESC
            """)
            
            applications = await cursor.fetchall()
            logger.info(f"Найдено {len(applications)} заявок в БД")
            
            if not applications:
                logger.info("Заявки в БД не найдены")
                return
            
            # Подготавливаем данные для экспорта
            fieldnames = [
                'timestamp', 'user_id', 'username', 'full_name', 'university', 
                'course', 'phone', 'email', 'how_found_kbk', 'previous_department',
                'department', 'position', 'priorities', 'experience', 'motivation', 'status', 
                'resume_local_path', 'resume_google_drive_url', 'created', 'updated'
            ]
            
            export_data = []
            for app in applications:
                (user_id, status, created, updated, full_name, university, course, 
                 phone, email, telegram_username, how_found_kbk, department, position, 
                 experience, motivation, resume_local_path, resume_google_drive_url) = app
                
                export_data.append({
                    'timestamp': datetime.now().isoformat(),
                    'user_id': user_id,
                    'username': telegram_username or "",
                    'full_name': full_name or "",
                    'university': university or "",
                    'course': course or "",
                    'phone': phone or "",
                    'email': email or "",
                    'how_found_kbk': how_found_kbk or "",
                    'previous_department': "",  # Добавить когда будет в БД
                    'department': department or "",
                    'position': position or "",
                    'priorities': "",  # Добавить когда будет в БД
                    'experience': experience or "",
                    'motivation': motivation or "",
                    'status': status,
                    'resume_local_path': resume_local_path or "",
                    'resume_google_drive_url': resume_google_drive_url or "",
                    'created': created.isoformat() if created else "",
                    'updated': updated.isoformat() if updated else ""
                })
            
            # Экспортируем в CSV
            await export_to_csv(export_data, fieldnames)
            
            # Экспортируем в Google Sheets
            await export_to_google_sheets(export_data, config)
            
    except Exception as e:
        logger.error(f"Ошибка при экспорте заявок: {e}")


async def export_to_csv(data: List[Dict[str, Any]], fieldnames: List[str]):
    """Экспортирует данные в CSV файл"""
    try:
        # Создаем директорию если её нет
        os.makedirs("app/storage/backups", exist_ok=True)
        
        # Создаем файл с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"app/storage/backups/applications_export_{timestamp}.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"Данные экспортированы в CSV: {csv_path}")
        
        # Также создаем файл с актуальными данными
        current_csv_path = "app/storage/backups/applications_current.csv"
        with open(current_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"Текущие данные обновлены: {current_csv_path}")
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте в CSV: {e}")


async def export_to_google_sheets(data: List[Dict[str, Any]], config):
    """Экспортирует данные в Google Sheets"""
    try:
        logger.info(f"Проверяем настройки Google: config.google = {config.google}")
        
        if not config.google:
            logger.warning("Google сервисы не настроены, пропускаем экспорт в Google Sheets")
            return
        
        google_manager = await setup_google_services()
        if not google_manager:
            logger.warning("Не удалось настроить Google сервисы, пропускаем экспорт")
            return
        
        # Открываем таблицу по названию из конфигурации
        spreadsheet_name = getattr(config.google, 'spreadsheet_name', 'Заявки КБК26')
        spreadsheet = google_manager.gc.open(spreadsheet_name)
        
        # Очищаем существующий лист Applications или создаем новый
        try:
            worksheet = spreadsheet.worksheet("Applications")
            worksheet.clear()
        except:
            worksheet = spreadsheet.add_worksheet(title="Applications", rows="1000", cols="20")
        
        # Подготавливаем данные для записи
        headers = [
            'Timestamp', 'User ID', 'Username', 'Full Name', 'University', 
            'Course', 'Phone', 'Email', 'How Found KBK', 'Previous Department',
            'Department', 'Position', 'Priorities', 'Experience', 'Motivation', 'Status',
            'Resume Local Path', 'Resume Google Drive URL', 'Created', 'Updated'
        ]
        
        # Записываем заголовки
        worksheet.append_row(headers)
        
        # Записываем данные
        for item in data:
            row_data = [
                item.get('timestamp', ''),
                item.get('user_id', ''),
                item.get('username', ''),
                item.get('full_name', ''),
                item.get('university', ''),
                item.get('course', ''),
                item.get('phone', ''),
                item.get('email', ''),
                item.get('how_found_kbk', ''),
                item.get('previous_department', ''),
                item.get('department', ''),
                item.get('position', ''),
                item.get('priorities', ''),
                item.get('experience', ''),
                item.get('motivation', ''),
                item.get('status', ''),
                item.get('resume_local_path', ''),
                item.get('resume_google_drive_url', ''),
                item.get('created', ''),
                item.get('updated', '')
            ]
            worksheet.append_row(row_data)
        
        logger.info(f"Данные экспортированы в Google Sheets: {len(data)} заявок")
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте в Google Sheets: {e}")


if __name__ == "__main__":
    asyncio.run(export_applications())
