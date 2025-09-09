import os
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class GoogleServicesManager:
    """Класс для работы с Google Sheets и Google Drive"""
    
    def __init__(self, credentials_path: str, spreadsheet_id: str, drive_folder_id: str = "", 
                 spreadsheet_name: str = "Заявки КБК26", drive_folder_name: str = "Резюме_КБК26",
                 enable_drive: bool = False):
        """
        Инициализация менеджера Google сервисов
        
        Args:
            credentials_path: Путь к файлу с учетными данными сервисного аккаунта
            spreadsheet_id: ID Google Таблицы
            drive_folder_id: ID папки на Google Drive для загрузки файлов
            spreadsheet_name: Название Google Таблицы
            drive_folder_name: Название папки на Google Drive
            enable_drive: Включить ли Google Drive (по умолчанию False)
        """
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.drive_folder_id = drive_folder_id
        self.spreadsheet_name = spreadsheet_name
        self.drive_folder_name = drive_folder_name
        self.enable_drive = enable_drive
        self.drive_folder_name = drive_folder_name
        
        # Области доступа
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        self._setup_services()
    
    def _setup_services(self):
        """Настройка сервисов Google API"""
        try:
            # Создаем учетные данные
            credentials = Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=self.scopes
            )
            
            # Настраиваем gspread для работы с Google Sheets
            self.gc = gspread.authorize(credentials)
            logger.info("✅ Google Sheets API настроен")
            
            # Настраиваем Google Drive API только если включен
            if self.enable_drive:
                self.drive_service = build('drive', 'v3', credentials=credentials)
                logger.info("✅ Google Drive API настроен")
                
                # Проверяем и создаем папку если нужно
                self._ensure_drive_folder_exists()
            else:
                self.drive_service = None
                logger.info("ℹ️ Google Drive отключен")
            
            logger.info("Google Services настроены успешно")
            
        except Exception as e:
            logger.error(f"Ошибка настройки Google Services: {e}")
            raise
    
    def _ensure_drive_folder_exists(self):
        """Проверяет существование папки и создает её если нужно"""
        try:
            # Проверяем, существует ли папка с указанным ID
            if self.drive_folder_id:
                try:
                    file = self.drive_service.files().get(fileId=self.drive_folder_id).execute()
                    if file.get('mimeType') == 'application/vnd.google-apps.folder':
                        logger.info(f"Папка {self.drive_folder_name} найдена: {self.drive_folder_id}")
                        return
                except:
                    pass
            
            # Ищем папку по названию
            results = self.drive_service.files().list(
                q=f"name='{self.drive_folder_name}' and mimeType='application/vnd.google-apps.folder'",
                spaces='drive'
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                # Папка найдена, обновляем ID
                self.drive_folder_id = folders[0]['id']
                logger.info(f"Найдена существующая папка {self.drive_folder_name}: {self.drive_folder_id}")
            else:
                # Создаем новую папку
                folder_metadata = {
                    'name': self.drive_folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                
                folder = self.drive_service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                
                self.drive_folder_id = folder.get('id')
                logger.info(f"Создана новая папка {self.drive_folder_name}: {self.drive_folder_id}")
                
        except Exception as e:
            logger.error(f"Ошибка при работе с папкой Google Drive: {e}")
            # Продолжаем работу даже если не удалось создать папку
    
    async def add_application_to_sheet(self, application_data: Dict[str, Any]) -> bool:
        """
        Добавляет данные заявки в Google Таблицу
        
        Args:
            application_data: Словарь с данными заявки
            
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            logger.info(f"📊 Начинаем добавление заявки в Google Sheets...")
            logger.info(f"👤 Пользователь: {application_data.get('user_id')} (@{application_data.get('username')})")
            
            # Открываем таблицу по названию
            logger.info(f"📋 Открываем таблицу: {self.spreadsheet_name}")
            spreadsheet = self.gc.open(self.spreadsheet_name)
            
            # Получаем лист "Applications" или создаем его
            worksheet_name = "Applications"
            try:
                logger.info(f"🔍 Ищем лист: {worksheet_name}")
                worksheet = spreadsheet.worksheet(worksheet_name)
                logger.info(f"✅ Лист {worksheet_name} найден")
            except gspread.WorksheetNotFound:
                logger.info(f"📄 Лист {worksheet_name} не найден, создаем новый...")
                # Создаем лист если его нет
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=25)
                
                # Добавляем заголовки с поддержкой под-отделов
                headers = [
                    'Timestamp', 'User ID', 'Username', 'Full Name', 'University', 
                    'Course', 'Phone', 'Email', 'How Found KBK', 'Previous Department',
                    'Department 1', 'Position 1', 'Subdepartment 1',
                    'Department 2', 'Position 2', 'Subdepartment 2', 
                    'Department 3', 'Position 3', 'Subdepartment 3',
                    'Priorities', 'Experience', 'Motivation', 'Status', 
                    'Resume Local Path', 'Resume Google Drive URL'
                ]
                worksheet.append_row(headers)
                logger.info(f"✅ Лист {worksheet_name} создан с заголовками (включая под-отделы)")
            
            # Подготавливаем данные для записи
            logger.info(f"📝 Подготавливаем данные для записи...")
            row_data = [
                application_data.get('timestamp', ''),
                application_data.get('user_id', ''),
                application_data.get('username', ''),
                application_data.get('full_name', ''),
                application_data.get('university', ''),
                application_data.get('course', ''),
                application_data.get('phone', ''),
                application_data.get('email', ''),
                application_data.get('how_found_kbk', ''),
                application_data.get('previous_department', ''),
                application_data.get('department_1', ''),
                application_data.get('position_1', ''),
                application_data.get('subdepartment_1', ''),
                application_data.get('department_2', ''),
                application_data.get('position_2', ''),
                application_data.get('subdepartment_2', ''),
                application_data.get('department_3', ''),
                application_data.get('position_3', ''),
                application_data.get('subdepartment_3', ''),
                application_data.get('priorities', ''),
                application_data.get('experience', ''),
                application_data.get('motivation', ''),
                application_data.get('status', ''),
                application_data.get('resume_local_path', ''),
                application_data.get('resume_google_drive_url', '')
            ]
            
            logger.info(f"📤 Отправляем данные в Google Sheets...")
            
            # Добавляем строку в таблицу
            worksheet.append_row(row_data)
            
            logger.info(f"🎉 Заявка пользователя {application_data.get('user_id')} успешно добавлена в Google Sheets")
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Ошибка добавления заявки в Google Sheets: {e}")
            
            # Детальная диагностика ошибок Google Sheets
            if "quotaExceeded" in error_msg:
                logger.error("📊 ОШИБКА: Превышены лимиты Google Sheets API")
                logger.error("💡 РЕШЕНИЕ: Подождите и повторите попытку позже")
            elif "403" in error_msg:
                if "Forbidden" in error_msg:
                    logger.error("🚫 ОШИБКА: Нет доступа к Google Sheets (403 Forbidden)")
                    logger.error("💡 РЕШЕНИЕ: Проверьте права доступа Service Account к таблице")
                else:
                    logger.error("🚫 ОШИБКА 403: Доступ запрещен")
            elif "401" in error_msg:
                logger.error("🔐 ОШИБКА: Ошибка авторизации Google Sheets (401)")
                logger.error("💡 РЕШЕНИЕ: Проверьте учетные данные Service Account")
            elif "404" in error_msg:
                logger.error("📋 ОШИБКА: Таблица Google Sheets не найдена (404)")
                logger.error(f"💡 РЕШЕНИЕ: Проверьте название таблицы: {self.spreadsheet_name}")
                logger.error(f"💡 РЕШЕНИЕ: Проверьте ID таблицы: {self.spreadsheet_id}")
            elif "500" in error_msg:
                logger.error("🔧 ОШИБКА: Внутренняя ошибка сервера Google (500)")
                logger.error("💡 РЕШЕНИЕ: Повторите попытку позже")
            elif "PERMISSION_DENIED" in error_msg:
                logger.error("🔒 ОШИБКА: Нет прав доступа к таблице")
                logger.error("💡 РЕШЕНИЕ: Предоставьте Service Account доступ к таблице")
            else:
                logger.error(f"❓ НЕИЗВЕСТНАЯ ОШИБКА Google Sheets: {error_msg}")
                
            return False
    
    def upload_file_to_drive(self, local_file_path: str, drive_filename: str) -> Optional[str]:
        """
        Загружает файл на Google Drive
        
        Args:
            local_file_path: Путь к локальному файлу
            drive_filename: Имя файла на Google Drive
            
        Returns:
            str: Ссылка на загруженный файл или None в случае ошибки
        """
        # Проверяем, включен ли Google Drive
        if not self.enable_drive:
            logger.info("ℹ️ Google Drive отключен, пропускаем загрузку файла")
            return None
            
        if not self.drive_service:
            logger.error("❌ Google Drive сервис не инициализирован")
            return None
            
        try:
            logger.info(f"📁 Начинаем загрузку файла {drive_filename} в Google Drive...")
            
            # Проверяем существование локального файла
            if not os.path.exists(local_file_path):
                logger.error(f"❌ Локальный файл не найден: {local_file_path}")
                return None
            
            # Получаем размер файла для логирования
            file_size = os.path.getsize(local_file_path)
            logger.info(f"📄 Размер файла: {file_size} байт ({file_size / 1024 / 1024:.2f} МБ)")
            
            # Проверяем доступность папки
            if not self.drive_folder_id:
                logger.error("❌ ID папки Google Drive не настроен")
                return None
                
            logger.info(f"📂 Загрузка в папку: {self.drive_folder_name} (ID: {self.drive_folder_id})")
            
            # Метаданные файла для папки "Резюме_КБК26"
            file_metadata = {
                'name': drive_filename,
                'parents': [self.drive_folder_id]  # ID папки "Резюме_КБК26"
            }
            
            logger.info(f"🔄 Создаем медиа объект для загрузки...")
            
            # Загружаем файл
            media = MediaFileUpload(local_file_path, resumable=True)
            
            logger.info(f"🚀 Отправляем файл в Google Drive...")
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            file_id = file.get('id')
            
            if not file_id:
                logger.error("❌ Не удалось получить ID загруженного файла")
                return None
                
            logger.info(f"✅ Файл загружен с ID: {file_id}")
            
            # Делаем файл доступным для просмотра
            logger.info(f"🔓 Настраиваем права доступа к файлу...")
            
            self.drive_service.permissions().create(
                fileId=file_id,
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()
            
            # Возвращаем ссылку на файл
            file_url = f"https://drive.google.com/file/d/{file_id}/view"
            
            logger.info(f"🎉 Файл {drive_filename} успешно загружен на Google Drive: {file_url}")
            return file_url
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Ошибка загрузки файла на Google Drive: {e}")
            
            # Детальная диагностика ошибок
            if "storageQuotaExceeded" in error_msg:
                logger.error("💾 ОШИБКА: Превышена квота хранилища Google Drive")
                logger.error("💡 РЕШЕНИЕ: Очистите место на Google Drive или используйте Shared Drive")
            elif "Service Accounts do not have storage quota" in error_msg:
                logger.error("🔑 ОШИБКА: Service Account не имеет квоты хранилища")
                logger.error("💡 РЕШЕНИЕ 1: Используйте Shared Drive вместо личного Drive")
                logger.error("💡 РЕШЕНИЕ 2: Используйте OAuth делегирование")
                logger.error("💡 РЕШЕНИЕ 3: Загружайте файлы в общую папку с достаточными правами")
            elif "quotaExceeded" in error_msg:
                logger.error("📊 ОШИБКА: Превышены лимиты Google Drive API")
                logger.error("💡 РЕШЕНИЕ: Подождите и повторите попытку позже")
            elif "403" in error_msg:
                if "Forbidden" in error_msg:
                    logger.error("🚫 ОШИБКА: Нет доступа к Google Drive (403 Forbidden)")
                    logger.error("💡 РЕШЕНИЕ: Проверьте права доступа Service Account")
                else:
                    logger.error("🚫 ОШИБКА 403: Доступ запрещен")
            elif "401" in error_msg:
                logger.error("🔐 ОШИБКА: Ошибка авторизации Google Drive (401)")
                logger.error("💡 РЕШЕНИЕ: Проверьте учетные данные Service Account")
            elif "404" in error_msg:
                logger.error("📁 ОШИБКА: Папка на Google Drive не найдена (404)")
                logger.error(f"💡 РЕШЕНИЕ: Проверьте ID папки: {self.drive_folder_id}")
            elif "500" in error_msg:
                logger.error("🔧 ОШИБКА: Внутренняя ошибка сервера Google (500)")
                logger.error("💡 РЕШЕНИЕ: Повторите попытку позже")
            else:
                logger.error(f"❓ НЕИЗВЕСТНАЯ ОШИБКА: {error_msg}")
                
            return None
    
    async def create_backup_sheet(self, csv_data: List[List[str]], sheet_name: str) -> bool:
        """
        Создает резервную копию в новом листе Google Таблицы
        
        Args:
            csv_data: Данные в формате CSV (список списков)
            sheet_name: Название нового листа
            
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            # Открываем таблицу
            sheet = self.gc.open_by_key(self.spreadsheet_id)
            
            # Создаем новый лист
            worksheet = sheet.add_worksheet(title=sheet_name, rows=len(csv_data), cols=len(csv_data[0]) if csv_data else 1)
            
            # Добавляем данные
            if csv_data:
                worksheet.update('A1', csv_data)
            
            logger.info(f"Резервная копия создана в листе {sheet_name}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")
            return False


# Пример использования
async def setup_google_services() -> Optional[GoogleServicesManager]:
    """
    Настройка Google сервисов
    
    Returns:
        GoogleServicesManager или None в случае ошибки
    """
    try:
        from config.config import load_config
        config = load_config()
        
        if not config.google:
            logger.warning("Google сервисы не настроены в конфигурации")
            return None
        
        # Проверяем существование файла учетных данных
        if not os.path.exists(config.google.credentials_path):
            logger.warning(f"Файл учетных данных Google не найден: {config.google.credentials_path}")
            return None
        
        return GoogleServicesManager(
            config.google.credentials_path, 
            config.google.spreadsheet_id, 
            config.google.drive_folder_id,
            getattr(config.google, 'spreadsheet_name', 'Заявки КБК26'),
            getattr(config.google, 'drive_folder_name', 'Резюме_КБК26')
        )
        
    except Exception as e:
        logger.error(f"Ошибка настройки Google сервисов: {e}")
        return None
