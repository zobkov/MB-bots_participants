#!/usr/bin/env python3
"""
Скрипт для настройки Google Sheets с правильными заголовками и тестовыми данными
"""

import asyncio
import logging
from datetime import datetime
from app.services.google_services import GoogleServicesManager
from config.config import load_config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_sheets():
    """Настройка Google Sheets с правильными заголовками и тестовыми данными"""
    try:
        # Загружаем конфигурацию
        config = load_config()
        
        if not config.google:
            logger.error("❌ Google конфигурация не найдена")
            return
        
        # Создаем менеджер Google сервисов
        google_manager = GoogleServicesManager(
            credentials_path=config.google.credentials_path,
            spreadsheet_id=config.google.spreadsheet_id,
            drive_folder_id=config.google.drive_folder_id,
            enable_drive=config.google.enable_drive
        )
        
        logger.info("✅ Google Services Manager инициализирован")
        
        # Открываем таблицу
        spreadsheet = google_manager.gc.open(google_manager.spreadsheet_name)
        logger.info(f"📋 Открыта таблица: {google_manager.spreadsheet_name}")
        
        # Получаем или создаем лист Applications
        worksheet_name = "Applications"
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            logger.info(f"✅ Лист {worksheet_name} найден")
            
            # Очищаем существующий лист
            logger.info("🧹 Очищаем существующий лист...")
            worksheet.clear()
            
        except Exception:
            logger.info(f"📄 Лист {worksheet_name} не найден, создаем новый...")
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=25)
        
        # Правильные заголовки согласно новой системе приоритетов с под-отделами
        headers = [
            'Timestamp',           # A
            'User ID',             # B
            'Username',            # C
            'Full Name',           # D
            'University',          # E
            'Course',              # F
            'Phone',               # G
            'Email',               # H
            'How Found KBK',       # I
            'Previous Department', # J
            'Department 1',        # K
            'Position 1',          # L
            'Subdepartment 1',     # M
            'Department 2',        # N
            'Position 2',          # O
            'Subdepartment 2',     # P
            'Department 3',        # Q
            'Position 3',          # R
            'Subdepartment 3',     # S
            'Priorities',          # T
            'Experience',          # U
            'Motivation',          # V
            'Status',              # W
            'Resume Local Path',   # X
            'Resume Google Drive URL'  # Y
        ]
        
        logger.info("📋 Добавляем заголовки...")
        worksheet.append_row(headers)
        
        # Добавляем тестовые данные согласно новой системе с под-отделами
        test_data = [
            [
                datetime.now().isoformat(),                    # Timestamp
                '123456789',                                   # User ID
                'test_user',                                   # Username
                'Иванов Иван Иванович',                       # Full Name
                'МГУ имени М.В. Ломоносова',                  # University
                '3',                                           # Course
                '+7-999-123-45-67',                           # Phone
                'test@example.com',                            # Email
                'Социальные сети, Друзья',                    # How Found KBK
                '',                                            # Previous Department
                'Творческий отдел',                           # Department 1
                'Сценарист',                                  # Position 1
                'Сценическое направление',                    # Subdepartment 1
                'Отдел SMM&PR',                               # Department 2
                'Контент-менеджер',                           # Position 2
                'Социальные сети на русском и китайском',     # Subdepartment 2
                'Отдел партнёров',                            # Department 3
                'Менеджер по партнерству',                    # Position 3
                '',                                            # Subdepartment 3 (у отдела партнёров нет под-отделов)
                '1) Творческий отдел - Сценическое направление - Сценарист; 2) Отдел SMM&PR - Социальные сети на русском и китайском - Контент-менеджер; 3) Отдел партнёров - Менеджер по партнерству',  # Priorities
                'Опыт написания сценариев для студенческих спектаклей',  # Experience
                'Хочу развиваться в творческой сфере и создавать контент',  # Motivation
                'submitted',                                   # Status
                'app/storage/resumes/resume_123456789.pdf',   # Resume Local Path
                'https://drive.google.com/file/d/example123/view'  # Resume Google Drive URL
            ],
            [
                datetime.now().isoformat(),                    # Timestamp
                '987654321',                                   # User ID
                'student_user',                                # Username
                'Петрова Анна Сергеевна',                     # Full Name
                'СПБГУ',                                       # University
                '2',                                           # Course
                '+7-912-345-67-89',                           # Phone
                'anna.petrova@student.spbu.ru',               # Email
                'Университет, Социальные сети',               # How Found KBK
                '',                                            # Previous Department
                'Отдел дизайна',                              # Department 1
                'Моушн-дизайнер',                             # Position 1
                '',                                            # Subdepartment 1 (у отдела дизайна нет под-отделов)
                'Творческий отдел',                           # Department 2
                'Звукорежиссер',                              # Position 2
                'Стендовая сессия',                           # Subdepartment 2
                '',                                            # Department 3
                '',                                            # Position 3
                '',                                            # Subdepartment 3
                '1) Отдел дизайна - Моушн-дизайнер; 2) Творческий отдел - Стендовая сессия - Звукорежиссер',  # Priorities
                'Изучаю After Effects, делала анимацию для курсовой',  # Experience
                'Интересно применить навыки дизайна в реальном проекте',  # Motivation
                'submitted',                                   # Status
                'app/storage/resumes/resume_987654321.pdf',   # Resume Local Path
                ''                                             # Resume Google Drive URL
            ]
        ]
        
        logger.info("📝 Добавляем тестовые данные...")
        for i, row in enumerate(test_data, 1):
            worksheet.append_row(row)
            logger.info(f"✅ Добавлена тестовая запись {i}")
        
        # Форматируем заголовки (делаем их жирными)
        logger.info("🎨 Форматируем заголовки...")
        try:
            worksheet.format('A1:Y1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })
            logger.info("✅ Заголовки отформатированы")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отформатировать заголовки: {e}")
        
        # Автоматически подгоняем ширину колонок
        logger.info("📏 Настраиваем ширину колонок...")
        try:
            # Устанавливаем ширину колонок
            requests = [
                {
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': worksheet.id,
                            'dimension': 'COLUMNS',
                            'startIndex': 0,  # A
                            'endIndex': 25    # Y
                        },
                        'properties': {
                            'pixelSize': 150
                        },
                        'fields': 'pixelSize'
                    }
                }
            ]
            
            spreadsheet.batch_update({'requests': requests})
            logger.info("✅ Ширина колонок настроена")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось настроить ширину колонок: {e}")
        
        logger.info("🎉 Google Sheets успешно настроен!")
        logger.info(f"🔗 Ссылка на таблицу: https://docs.google.com/spreadsheets/d/{config.google.spreadsheet_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка настройки Google Sheets: {e}")
        return False


async def test_application_export():
    """Тест экспорта заявки в Google Sheets"""
    try:
        config = load_config()
        
        google_manager = GoogleServicesManager(
            credentials_path=config.google.credentials_path,
            spreadsheet_id=config.google.spreadsheet_id,
            drive_folder_id=config.google.drive_folder_id,
            enable_drive=config.google.enable_drive
        )
        
        # Тестовые данные заявки в формате системы приоритетов с под-отделами
        test_application = {
            'timestamp': datetime.now().isoformat(),
            'user_id': '555666777',
            'username': 'priority_test_user',
            'full_name': 'Тестов Приоритет Системович',
            'university': 'Тестовый Технический Университет',
            'course': '4',
            'phone': '+7-555-666-77-88',
            'email': 'priority.test@example.com',
            'how_found_kbk': 'Тестирование системы приоритетов',
            'previous_department': '',
            'department_1': 'Творческий отдел',
            'position_1': 'Сценарист',
            'subdepartment_1': 'Сценическое направление',
            'department_2': 'Отдел SMM&PR',
            'position_2': 'Аналитик',
            'subdepartment_2': 'Социальные сети на русском и китайском',
            'department_3': 'Отдел дизайна',
            'position_3': 'Моушн-дизайнер',
            'subdepartment_3': '',  # У отдела дизайна нет под-отделов
            'priorities': '1) Творческий отдел - Сценическое направление - Сценарист; 2) Отдел SMM&PR - Социальные сети на русском и китайском - Аналитик; 3) Отдел дизайна - Моушн-дизайнер',
            'experience': 'Опыт в тестировании системы приоритетов с под-отделами',
            'motivation': 'Хочу проверить работу новой системы приоритетов с под-отделами',
            'status': 'submitted',
            'resume_local_path': 'app/storage/resumes/priority_test.pdf',
            'resume_google_drive_url': 'https://drive.google.com/file/d/test_priority/view'
        }
        
        logger.info("🧪 Тестируем экспорт заявки с системой приоритетов...")
        success = await google_manager.add_application_to_sheet(test_application)
        
        if success:
            logger.info("✅ Тест экспорта прошел успешно!")
        else:
            logger.error("❌ Тест экспорта не удался!")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Ошибка теста экспорта: {e}")
        return False


async def main():
    """Главная функция"""
    logger.info("🚀 Запуск настройки Google Sheets...")
    
    # Настраиваем Google Sheets
    setup_success = await setup_sheets()
    
    if setup_success:
        logger.info("✅ Настройка Google Sheets завершена")
        
        # Тестируем экспорт
        logger.info("🧪 Запуск теста экспорта...")
        test_success = await test_application_export()
        
        if test_success:
            logger.info("🎉 Все тесты прошли успешно!")
        else:
            logger.error("❌ Тесты не прошли")
    else:
        logger.error("❌ Настройка Google Sheets не удалась")


if __name__ == "__main__":
    asyncio.run(main())
