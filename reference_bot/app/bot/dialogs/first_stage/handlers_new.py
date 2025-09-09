import os
import csv
import logging
from datetime import datetime
from typing import Any

from aiogram import Bot
from aiogram.types import Message, CallbackQuery, Document, User
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput

from config.config import Config
from app.infrastructure.database.database.db import DB
 

logger = logging.getLogger(__name__)


async def process_name(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    dialog_manager.dialog_data["name"] = message.text.strip()
    await dialog_manager.next()


async def process_surname(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    dialog_manager.dialog_data["surname"] = message.text.strip()
    await dialog_manager.next()


async def process_patronymic(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    dialog_manager.dialog_data["patronymic"] = message.text.strip()
    # Формируем полное имя
    name = dialog_manager.dialog_data.get("name", "")
    surname = dialog_manager.dialog_data.get("surname", "")
    patronymic = dialog_manager.dialog_data.get("patronymic", "")
    full_name = f"{surname} {name} {patronymic}".strip()
    dialog_manager.dialog_data["full_name"] = full_name
    await dialog_manager.next()


async def process_university(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    dialog_manager.dialog_data["university"] = message.text.strip()
    await dialog_manager.next()


async def process_course(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    try:
        course = int(message.text.strip())
        if 1 <= course <= 6:
            dialog_manager.dialog_data["course"] = str(course)
            await dialog_manager.next()
        else:
            await message.answer("Пожалуйста, введите номер курса от 1 до 6")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный номер курса (цифру от 1 до 6)")


async def process_phone(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    phone = message.text.strip()
    # Простая валидация телефона
    if len(phone) >= 10:
        dialog_manager.dialog_data["phone"] = phone
        await dialog_manager.next()
    else:
        await message.answer("Пожалуйста, введите корректный номер телефона")


async def process_email(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    email = message.text.strip()
    if "@" in email and "." in email:
        dialog_manager.dialog_data["email"] = email
        await dialog_manager.next()
    else:
        await message.answer("Пожалуйста, введите корректный email адрес")


async def process_experience(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    dialog_manager.dialog_data["experience"] = message.text.strip()
    await dialog_manager.next()


async def process_motivation(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    dialog_manager.dialog_data["motivation"] = message.text.strip()
    await dialog_manager.next()


async def process_resume_file(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    bot: Bot = dialog_manager.middleware_data["bot"]
    document: Document = message.document
    
    if not document:
        await message.answer("Пожалуйста, прикрепите файл резюме.")
        return
    
    # Проверяем размер файла (максимум 20 МБ)
    if document.file_size > 20 * 1024 * 1024:
        await message.answer("Файл слишком большой. Максимальный размер: 20 МБ")
        return
    
    # Получаем данные пользователя из диалога
    dialog_data = dialog_manager.dialog_data
    surname = dialog_data.get("surname", "Unknown")
    name = dialog_data.get("name", "Unknown")
    
    # Генерируем имя файла
    user = message.from_user
    initials = f"{name[0]}{dialog_data.get('patronymic', [''])[0]}".upper()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(document.file_name)[1] if document.file_name else ".pdf"
    new_filename = f"{surname}_{initials}_{user.username or user.id}_{timestamp}{file_extension}"
    
    try:
        # Получаем файл от Telegram
        file = await bot.get_file(document.file_id)
        file_path = f"app/storage/resumes/{new_filename}"
        
        # Создаем директорию если её нет
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Скачиваем файл
        await bot.download_file(file.file_path, file_path)
        logger.info(f"Файл резюме скачан локально: {file_path}")
        
        # Загружаем файл в Google Drive
        try:
            from app.services.google_services import GoogleServicesManager
            google_manager = GoogleServicesManager()
            google_file_url = google_manager.upload_file_to_drive(
                local_file_path=file_path,
                drive_filename=new_filename
            )
            
            if google_file_url:
                logger.info(f"Файл успешно загружен в Google Drive: {google_file_url}")
                # Сохраняем информацию о файле в данных диалога
                dialog_manager.dialog_data["resume_file"] = new_filename
                dialog_manager.dialog_data["resume_google_url"] = google_file_url
            else:
                logger.error("Не удалось получить URL файла с Google Drive")
                dialog_manager.dialog_data["resume_file"] = new_filename
                dialog_manager.dialog_data["resume_google_error"] = "Не удалось получить URL файла"
            
        except Exception as e:
            logger.error(f"Ошибка загрузки резюме в Google Drive: {e}")
            # Продолжаем работу даже если загрузка в Google Drive не удалась
            dialog_manager.dialog_data["resume_file"] = new_filename
            dialog_manager.dialog_data["resume_google_error"] = str(e)
        
        await message.answer(
            f"✅ Резюме получено и сохранено как: {new_filename}\n"
            "Нажмите кнопку ниже, чтобы продолжить."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке файла резюме: {e}")
        await message.answer("Произошла ошибка при обработке файла. Попробуйте еще раз.")
        return


async def on_confirm_application(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Обработчик подтверждения заявки"""
    await save_application(dialog_manager)
    await dialog_manager.next()


async def save_application(dialog_manager: DialogManager):
    """Сохранение заявки в БД и экспорт"""
    from aiogram.types import User
    
    event_from_user: User = dialog_manager.event.from_user
    dialog_data = dialog_manager.dialog_data
    config: Config = dialog_manager.middleware_data.get("config")
    db: DB = dialog_manager.middleware_data.get("db")
    
    if not config or not db:
        logger.error("Ошибка системы: нет доступа к конфигурации или БД")
        return
    
    # Получаем данные резюме (уже обработанные в process_resume_file)
    resume_local_path = None
    resume_google_drive_url = None
    
    resume_filename = dialog_data.get("resume_file")
    if resume_filename:
        resume_local_path = f"app/storage/resumes/{resume_filename}"
        resume_google_drive_url = dialog_data.get("resume_google_url", "")
    
    # Парсим текстовые данные
    how_found_idx = int(dialog_data.get("how_found_kbk", "0"))
    how_found_text = config.selection.how_found_options[how_found_idx] if how_found_idx < len(config.selection.how_found_options) else ""
    
    department_key = dialog_data.get("selected_department", "")
    department_name = config.selection.departments.get(department_key, {}).get("name", "")
    
    position_idx = int(dialog_data.get("selected_position", "0"))
    if department_key in config.selection.departments:
        positions = config.selection.departments[department_key]["positions"]
        position_text = positions[position_idx] if position_idx < len(positions) else ""
    else:
        position_text = ""
    
    # Сохраняем в БД и меняем статус на submitted
    try:
        # Ensure application row exists
        await db.applications.create_application(user_id=event_from_user.id)
        await db.applications.update_first_stage_form(
            user_id=event_from_user.id,
            full_name=dialog_data.get("full_name", ""),
            university=dialog_data.get("university", ""),
            course=int(dialog_data.get("course", "1")),
            phone=dialog_data.get("phone", ""),
            email=dialog_data.get("email", ""),
            telegram_username=event_from_user.username or "",
            how_found_kbk=how_found_text,
            department=department_name,
            position=position_text,
            experience=dialog_data.get("experience", ""),
            motivation=dialog_data.get("motivation", ""),
            resume_local_path=resume_local_path,
            resume_google_drive_url=resume_google_drive_url
        )
        # Обновляем статус пользователя на submitted
        await db.users.set_submission_status(user_id=event_from_user.id, status="submitted")
        logger.info(f"Заявка пользователя {event_from_user.id} успешно сохранена в БД")
    except Exception as e:
        logger.error(f"Ошибка при сохранении в БД: {e}")
        return
    
    # Подготавливаем данные для экспорта
    application_data = {
        'timestamp': datetime.now().isoformat(),
        'user_id': event_from_user.id,
        'username': event_from_user.username or "",
        'full_name': dialog_data.get("full_name", ""),
        'university': dialog_data.get("university", ""),
        'course': dialog_data.get("course", "1"),
        'phone': dialog_data.get("phone", ""),
        'email': dialog_data.get("email", ""),
        'how_found_kbk': how_found_text,
        'department': department_name,
        'position': position_text,
        'experience': dialog_data.get("experience", ""),
        'motivation': dialog_data.get("motivation", ""),
        'status': 'submitted',
        'resume_local_path': resume_local_path or "",
        'resume_google_drive_url': resume_google_drive_url or ""
    }
    
    # Сохраняем в CSV для бекапа
    await save_to_csv(application_data)
    
    # Отправляем в Google Sheets если настроено
    if config.google:
        try:
            from app.services.google_services import GoogleServicesManager
            google_manager = GoogleServicesManager()
            success = google_manager.add_application_to_sheet(application_data)
            if success:
                logger.info("Заявка успешно добавлена в Google Sheets")
            else:
                logger.error("Не удалось добавить заявку в Google Sheets")
        except Exception as e:
            logger.error(f"Ошибка при отправке в Google Sheets: {e}")


async def save_to_csv(application_data: dict):
    """Сохранение данных в CSV файл"""
    os.makedirs("app/storage/backups", exist_ok=True)
    
    csv_path = "app/storage/backups/applications.csv"
    file_exists = os.path.exists(csv_path)
    
    with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'timestamp', 'user_id', 'username', 'full_name', 'university', 
            'course', 'phone', 'email', 'how_found_kbk', 'department', 
            'position', 'experience', 'motivation', 'status', 
            'resume_local_path', 'resume_google_drive_url'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(application_data)
