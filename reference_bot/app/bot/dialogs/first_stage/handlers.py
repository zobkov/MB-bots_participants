import os
import csv
import re
import logging
from datetime import datetime
from typing import Any

from aiogram import Bot
from aiogram.types import Message, CallbackQuery, Document, User
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.input import MessageInput

from config.config import Config
from app.infrastructure.database.database.db import DB
from app.bot.states.first_stage import FirstStageSG
from app.bot.states.main_menu import MainMenuSG
from app.bot.states.job_selection import JobSelectionSG
from app.services.error_monitoring import error_monitor
from app.utils.filename_utils import make_safe_filename

logger = logging.getLogger(__name__)


async def on_job_selection_result(start_data: Any, result: Any, dialog_manager: DialogManager):
    """Обработчик результата диалога выбора вакансий"""
    logger.info(f"🎯 Получен результат от диалога выбора вакансий: {result}")
    
    if result:
        # Обновляем данные диалога результатами выбора вакансий
        dialog_manager.dialog_data.update(result)
        logger.info(f"✅ Данные приоритетов сохранены в основном диалоге: {list(result.keys())}")
    
    # Проверяем, было ли это редактирование
    was_editing = start_data and start_data.get("is_editing", False)
    
    if was_editing:
        # Если это было редактирование, возвращаемся к состоянию подтверждения
        logger.info(f"🔄 Возвращение к подтверждению после редактирования вакансий")
        await dialog_manager.switch_to(FirstStageSG.confirmation)
    else:
        # Если это было первичное заполнение, продолжаем к experience
        logger.info(f"➡️ Продолжение заполнения анкеты после выбора вакансий")
        await dialog_manager.switch_to(FirstStageSG.experience)


async def process_name(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    name = message.text.strip()
    logger.info(f"👤 Пользователь {message.from_user.id} ввел имя: {name}")
    dialog_manager.dialog_data["name"] = name
    await dialog_manager.next()


async def process_surname(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    surname = message.text.strip()
    logger.info(f"👤 Пользователь {message.from_user.id} ввел фамилию: {surname}")
    dialog_manager.dialog_data["surname"] = surname
    await dialog_manager.next()


async def process_patronymic(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    patronymic = message.text.strip()
    logger.info(f"👤 Пользователь {message.from_user.id} ввел отчество: {patronymic}")
    dialog_manager.dialog_data["patronymic"] = patronymic
    # Формируем полное имя
    name = dialog_manager.dialog_data.get("name", "")
    surname = dialog_manager.dialog_data.get("surname", "")
    full_name = f"{surname} {name} {patronymic}".strip()
    dialog_manager.dialog_data["full_name"] = full_name
    logger.info(f"✅ Сформировано полное имя: {full_name}")
    await dialog_manager.next()


async def process_university(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    university = message.text.strip()
    logger.info(f"🏫 Пользователь {message.from_user.id} ввел университет: {university}")
    dialog_manager.dialog_data["university"] = university
    await dialog_manager.next()


async def process_course(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    try:
        course = int(message.text.strip())
        if course < 1 or course > 6:
            logger.warning(f"⚠️ Пользователь {message.from_user.id} ввел некорректный курс: {course}")
            error_monitor.log_validation_error(
                field="course",
                value=str(course),
                user_id=message.from_user.id,
                username=message.from_user.username
            )
            await message.answer("Пожалуйста, введите курс от 1 до 6")
            return
        
        logger.info(f"📚 Пользователь {message.from_user.id} ввел курс: {course}")
        dialog_manager.dialog_data["course"] = str(course)
        await dialog_manager.next()
    except ValueError:
        logger.warning(f"⚠️ Пользователь {message.from_user.id} ввел некорректное значение курса: {message.text}")
        error_monitor.log_validation_error(
            field="course",
            value=message.text,
            user_id=message.from_user.id,
            username=message.from_user.username
        )
        await message.answer("Пожалуйста, введите число от 1 до 6")


async def process_phone(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    phone = message.text.strip()
    logger.info(f"📞 Пользователь {message.from_user.id} ввел телефон: {phone[:4]}***")  # Частично скрываем для безопасности
    
    # Простая валидация телефона
    if len(phone) < 10:
        logger.warning(f"⚠️ Пользователь {message.from_user.id} ввел слишком короткий номер телефона")
        await message.answer("Пожалуйста, введите корректный номер телефона")
        return
        
    dialog_manager.dialog_data["phone"] = phone
    await dialog_manager.next()


async def process_email(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    email = message.text.strip()
    logger.info(f"📧 Пользователь {message.from_user.id} ввел email: {email}")
    
    # Простая валидация email
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, email):
        logger.info(f"✅ Email валиден: {email}")
        dialog_manager.dialog_data["email"] = email
        await dialog_manager.next()
    else:
        logger.warning(f"⚠️ Пользователь {message.from_user.id} ввел некорректный email: {email}")
        await message.answer("Пожалуйста, введите корректный email адрес")


async def process_experience(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    experience = message.text.strip()
    logger.info(f"💼 Пользователь {message.from_user.id} ввел опыт работы ({len(experience)} символов)")
    dialog_manager.dialog_data["experience"] = experience
    await dialog_manager.next()


async def process_motivation(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    motivation = message.text.strip()
    logger.info(f"🎯 Пользователь {message.from_user.id} ввел мотивацию ({len(motivation)} символов)")
    dialog_manager.dialog_data["motivation"] = motivation
    await dialog_manager.next()


async def process_text_resume(message: Message, dialog_manager: DialogManager):
    """Обработка текстового резюме"""
    user = message.from_user
    text_content = message.text.strip()
    
    logger.info(f"📝 Обрабатываем текстовое резюме от пользователя {user.id}")
    
    # Получаем данные пользователя из диалога
    dialog_data = dialog_manager.dialog_data
    
    # Безопасно получаем имя, фамилию и отчество
    surname = dialog_data.get("surname", "")
    name = dialog_data.get("name", "")
    patronymic = dialog_data.get("patronymic", "")
    
    # Если данные пустые, используем значения по умолчанию
    if not surname or surname.strip() == "":
        surname = "User"
    if not name or name.strip() == "":
        name = "Unknown"
    if not patronymic or patronymic.strip() == "":
        patronymic = "Unknown"

    logger.info(f"👤 Данные пользователя для генерации имени файла:")
    logger.info(f"   - Фамилия: {surname}")
    logger.info(f"   - Имя: {name}")
    logger.info(f"   - Отчество: {patronymic}")

    # Генерируем имя файла
    name_initial = name[0].upper() if name and len(name) > 0 and name != "Unknown" else "U"
    
    if patronymic and patronymic.strip() != "" and patronymic != "Unknown":
        patronymic_initial = patronymic[0].upper()
        initials = f"{name_initial}{patronymic_initial}"
        logger.info(f"   📝 Инициалы (с отчеством): {initials}")
    else:
        initials = name_initial
        logger.info(f"   📝 Инициалы (без отчества): {initials}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_filename = f"{surname}_{initials}_{user.username or user.id}_{timestamp}.txt"
    new_filename = make_safe_filename(raw_filename)
    
    logger.info(f"📝 Сгенерировано имя файла для текстового резюме: {new_filename}")

    try:
        # Создаем директорию если её нет
        file_path = f"app/storage/resumes/{new_filename}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Сохраняем текст в файл
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        logger.info(f"✅ Текстовое резюме сохранено локально: {file_path}")
        
        # Обрабатываем Google Drive загрузку
        config: Config = dialog_manager.middleware_data.get("config")
        google_file_url = None
        
        if config and config.google and config.google.enable_drive:
            google_file_url = await upload_to_google_drive(file_path, new_filename, config, user.id)
            if google_file_url:
                dialog_manager.dialog_data["resume_google_url"] = google_file_url
            else:
                dialog_manager.dialog_data["resume_google_error"] = "Не удалось получить URL файла в Google Drive"
        
        # Сохраняем информацию о файле в данных диалога
        dialog_manager.dialog_data["resume_file"] = new_filename
        
        # Подготавливаем сообщение пользователю
        message_text = f"✅ Текстовое резюме получено и сохранено как: {new_filename}\n"
        message_text += "Теперь ты можешь перейти к следующему шагу."
        
        await message.answer(message_text)
        
        # Переходим к подтверждению
        logger.info(f"➡️ Переходим к подтверждению заявки для пользователя {user.id}")
        await dialog_manager.switch_to(FirstStageSG.confirmation)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке текстового резюме: {e}")
        await message.answer("Произошла ошибка при обработке текста. Попробуйте еще раз.")
        return


async def process_photo_resume(message: Message, photo_list, dialog_manager: DialogManager):
    """Обработка фотографии резюме"""
    bot: Bot = dialog_manager.middleware_data["bot"]
    user = message.from_user
    
    logger.info(f"📸 Обрабатываем фотографию резюме от пользователя {user.id}")
    
    # Берем фото самого высокого качества (последнее в списке)
    if not photo_list:
        logger.error(f"❌ Список фотографий пуст для пользователя {user.id}")
        await message.answer("Произошла ошибка при обработке фотографии. Попробуйте еще раз.")
        return
    
    # Выбираем фото наивысшего качества
    photo = photo_list[-1]
    
    logger.info(f"📋 Информация о фотографии:")
    logger.info(f"   - File ID: {photo.file_id}")
    logger.info(f"   - Размер: {photo.file_size} байт ({photo.file_size / 1024 / 1024:.2f} МБ)")
    logger.info(f"   - Разрешение: {photo.width}x{photo.height}")

    # Проверяем размер файла (максимум 15 МБ)
    max_size = 15 * 1024 * 1024
    if photo.file_size and photo.file_size > max_size:
        logger.warning(f"⚠️ Фотография пользователя {user.id} слишком большая: {photo.file_size} байт")
        await message.answer("❌ Фотография слишком большая. Максимальный размер: 15 МБ.\nПожалуйста, загрузите фотографию меньшего размера.")
        return

    # Получаем данные пользователя из диалога
    dialog_data = dialog_manager.dialog_data
    
    # Безопасно получаем имя, фамилию и отчество
    surname = dialog_data.get("surname", "")
    name = dialog_data.get("name", "")
    patronymic = dialog_data.get("patronymic", "")
    
    # Если данные пустые, используем значения по умолчанию
    if not surname or surname.strip() == "":
        surname = "User"
    if not name or name.strip() == "":
        name = "Unknown"
    if not patronymic or patronymic.strip() == "":
        patronymic = "Unknown"

    logger.info(f"👤 Данные пользователя для генерации имени файла:")
    logger.info(f"   - Фамилия: {surname}")
    logger.info(f"   - Имя: {name}")
    logger.info(f"   - Отчество: {patronymic}")

    # Генерируем имя файла
    name_initial = name[0].upper() if name and len(name) > 0 and name != "Unknown" else "U"
    
    if patronymic and patronymic.strip() != "" and patronymic != "Unknown":
        patronymic_initial = patronymic[0].upper()
        initials = f"{name_initial}{patronymic_initial}"
        logger.info(f"   📝 Инициалы (с отчеством): {initials}")
    else:
        initials = name_initial
        logger.info(f"   📝 Инициалы (без отчества): {initials}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Для фотографий используем расширение .jpg
    raw_filename = f"{surname}_{initials}_{user.username or user.id}_{timestamp}.jpg"
    new_filename = make_safe_filename(raw_filename)
    
    logger.info(f"📝 Сгенерировано имя файла для фотографии: {new_filename}")

    try:
        # Получаем файл от Telegram
        file = await bot.get_file(photo.file_id)
        file_path = f"app/storage/resumes/{new_filename}"
        
        # Создаем директорию если её нет
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Скачиваем файл
        await bot.download_file(file.file_path, file_path)
        logger.info(f"✅ Фотография резюме скачана локально: {file_path}")
        
        # Обрабатываем Google Drive загрузку
        config: Config = dialog_manager.middleware_data.get("config")
        google_file_url = None
        
        if config and config.google and config.google.enable_drive:
            google_file_url = await upload_to_google_drive(file_path, new_filename, config, user.id)
            if google_file_url:
                dialog_manager.dialog_data["resume_google_url"] = google_file_url
            else:
                dialog_manager.dialog_data["resume_google_error"] = "Не удалось получить URL файла в Google Drive"
        
        # Сохраняем информацию о файле в данных диалога
        dialog_manager.dialog_data["resume_file"] = new_filename
        
        # Подготавливаем сообщение пользователю
        message_text = f"✅ Фотография резюме получена и сохранена как: {new_filename}\n"
        message_text += "Теперь ты можешь перейти к следующему шагу."
        
        await message.answer(message_text)
        
        # Переходим к подтверждению
        logger.info(f"➡️ Переходим к подтверждению заявки для пользователя {user.id}")
        await dialog_manager.switch_to(FirstStageSG.confirmation)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке фотографии резюме: {e}")
        await message.answer("Произошла ошибка при обработке фотографии. Попробуйте еще раз.")
        return


async def process_file_resume(message: Message, document: Document, dialog_manager: DialogManager):
    """Обработка файлового резюме (любые типы файлов)"""
    bot: Bot = dialog_manager.middleware_data["bot"]
    user = message.from_user
    
    logger.info(f"📄 Получен файл от пользователя {user.id} (@{user.username})")

    # Логируем информацию о файле
    logger.info(f"📋 Информация о файле:")
    logger.info(f"   - Название: {document.file_name}")
    logger.info(f"   - Размер: {document.file_size} байт ({document.file_size / 1024 / 1024:.2f} МБ)")
    logger.info(f"   - MIME-тип: {document.mime_type}")

    # Проверяем размер файла (максимум 15 МБ)
    max_size = 15 * 1024 * 1024
    if document.file_size > max_size:
        logger.warning(f"⚠️ Файл пользователя {user.id} слишком большой: {document.file_size} байт")
        await message.answer("❌ Файл слишком большой. Максимальный размер: 15 МБ.\nПожалуйста, загрузите файл меньшего размера.")
        return

    # Получаем данные пользователя из диалога
    dialog_data = dialog_manager.dialog_data
    
    # Безопасно получаем имя, фамилию и отчество
    surname = dialog_data.get("surname", "")
    name = dialog_data.get("name", "")
    patronymic = dialog_data.get("patronymic", "")
    
    # Если данные пустые, используем значения по умолчанию
    if not surname or surname.strip() == "":
        surname = "User"
    if not name or name.strip() == "":
        name = "Unknown"
    if not patronymic or patronymic.strip() == "":
        patronymic = "Unknown"

    logger.info(f"👤 Данные пользователя для генерации имени файла:")
    logger.info(f"   - Фамилия: {surname}")
    logger.info(f"   - Имя: {name}")
    logger.info(f"   - Отчество: {patronymic}")

    # Генерируем имя файла
    name_initial = name[0].upper() if name and len(name) > 0 and name != "Unknown" else "U"
    
    if patronymic and patronymic.strip() != "" and patronymic != "Unknown":
        patronymic_initial = patronymic[0].upper()
        initials = f"{name_initial}{patronymic_initial}"
        logger.info(f"   📝 Инициалы (с отчеством): {initials}")
    else:
        initials = name_initial
        logger.info(f"   📝 Инициалы (без отчества): {initials}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(document.file_name)[1] if document.file_name else ".bin"
    raw_filename = f"{surname}_{initials}_{user.username or user.id}_{timestamp}{file_extension}"
    new_filename = make_safe_filename(raw_filename)
    
    logger.info(f"📝 Сгенерировано имя файла: {new_filename}")

    try:
        # Получаем файл от Telegram
        file = await bot.get_file(document.file_id)
        file_path = f"app/storage/resumes/{new_filename}"
        
        # Создаем директорию если её нет
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Скачиваем файл
        await bot.download_file(file.file_path, file_path)
        logger.info(f"✅ Файл резюме скачан локально: {file_path}")
        
        # Обрабатываем Google Drive загрузку
        config: Config = dialog_manager.middleware_data.get("config")
        google_file_url = None
        
        if config and config.google and config.google.enable_drive:
            google_file_url = await upload_to_google_drive(file_path, new_filename, config, user.id)
            if google_file_url:
                dialog_manager.dialog_data["resume_google_url"] = google_file_url
            else:
                dialog_manager.dialog_data["resume_google_error"] = "Не удалось получить URL файла в Google Drive"
        
        # Сохраняем информацию о файле в данных диалога
        dialog_manager.dialog_data["resume_file"] = new_filename
        
        # Подготавливаем сообщение пользователю
        message_text = f"✅ Резюме получено и сохранено как: {new_filename}\n"
        message_text += "Теперь ты можешь перейти к следующему шагу."
        
        await message.answer(message_text)
        
        # Переходим к подтверждению
        logger.info(f"➡️ Переходим к подтверждению заявки для пользователя {user.id}")
        await dialog_manager.switch_to(FirstStageSG.confirmation)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке файла резюме: {e}")
        await message.answer("Произошла ошибка при обработке файла. Попробуйте еще раз.")
        return


async def upload_to_google_drive(file_path: str, filename: str, config: Config, user_id: int) -> str:
    """Загружает файл в Google Drive и возвращает URL"""
    logger.info(f"🔄 Google Drive включен, начинаем загрузку файла для пользователя {user_id}")
    try:
        from app.services.google_services import GoogleServicesManager
        import asyncio
        
        # Создаем менеджер Google сервисов с параметрами из конфига
        google_manager = GoogleServicesManager(
            credentials_path=config.google.credentials_path,
            spreadsheet_id=config.google.spreadsheet_id,
            drive_folder_id=config.google.drive_folder_id or "",
            enable_drive=config.google.enable_drive
        )
        
        logger.info(f"🚀 Запускаем загрузку файла {filename} в Google Drive...")
        
        # Запускаем загрузку в отдельном потоке (так как метод синхронный)
        loop = asyncio.get_event_loop()
        google_file_url = await loop.run_in_executor(
            None, 
            google_manager.upload_file_to_drive,
            file_path,
            filename
        )
        
        if google_file_url:
            logger.info(f"✅ Файл успешно загружен в Google Drive: {google_file_url}")
            return google_file_url
        else:
            logger.error("❌ Не удалось загрузить файл в Google Drive - получен пустой URL")
            return ""
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Ошибка загрузки резюме в Google Drive: {e}")
        
        # Определяем тип ошибки для более понятного сообщения пользователю
        if "Service Accounts do not have storage quota" in error_msg:
            logger.warning("⚠️ Google Drive: сервисный аккаунт не имеет квоты хранилища - нужен Shared Drive")
        elif "storageQuotaExceeded" in error_msg:
            logger.warning("⚠️ Google Drive: превышена квота хранилища")
        elif "quotaExceeded" in error_msg:
            logger.warning("⚠️ Google Drive: превышены лимиты API")
        elif "403" in error_msg:
            logger.warning("⚠️ Google Drive: ошибка доступа (403)")
        elif "401" in error_msg:
            logger.warning("⚠️ Google Drive: ошибка авторизации (401)")
        elif "404" in error_msg:
            logger.warning("⚠️ Google Drive: папка не найдена (404)")
        else:
            logger.error(f"⚠️ Google Drive: неизвестная ошибка - {error_msg}")
        
        return ""


async def process_resume_file(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    bot: Bot = dialog_manager.middleware_data["bot"]
    document: Document = message.document
    photo = message.photo
    user = message.from_user
    
    logger.info(f"📄 Начинаем обработку резюме от пользователя {user.id} (@{user.username})")
    
    # Проверяем, что пришло: файл, фото или текст
    if message.text and not document and not photo:
        # Обработка текстового резюме
        logger.info(f"📝 Получен текст резюме от пользователя {user.id} ({len(message.text)} символов)")
        await process_text_resume(message, dialog_manager)
        return
    
    if photo:
        # Обработка фотографии
        logger.info(f"📸 Получена фотография от пользователя {user.id}")
        await process_photo_resume(message, photo, dialog_manager)
        return
    
    if document:
        # Обработка файлового резюме
        await process_file_resume(message, document, dialog_manager)
        return
    
    if not document and not photo and not message.text:
        logger.warning(f"⚠️ Пользователь {user.id} не прикрепил файл, фото и не отправил текст")
        await message.answer("Пожалуйста, прикрепите файл резюме, фото или отправьте текст резюме.")
        return


async def on_confirm_application(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Обработчик подтверждения заявки"""
    await save_application(dialog_manager)
    await dialog_manager.switch_to(FirstStageSG.success)

async def go_to_menu(callback: CallbackQuery, button, dialog_manager: DialogManager):
    await dialog_manager.start(MainMenuSG.main_menu, mode=StartMode.RESET_STACK)


async def save_application(dialog_manager: DialogManager):
    """Сохранение заявки в БД и экспорт"""
    from aiogram.types import User
    
    event_from_user: User = dialog_manager.event.from_user
    dialog_data = dialog_manager.dialog_data
    config: Config = dialog_manager.middleware_data.get("config")
    db: DB = dialog_manager.middleware_data.get("db")
    
    logger.info(f"🎯 Начинаем сохранение заявки пользователя {event_from_user.id} (@{event_from_user.username})")
    
    if not config or not db:
        logger.error("❌ Критическая ошибка: нет доступа к конфигурации или БД")
        if not config:
            logger.error("❌ Config объект отсутствует")
        if not db:
            logger.error("❌ DB объект отсутствует")
        return
    
    logger.info(f"✅ Конфигурация и БД доступны")
    
    # Получаем данные резюме (уже обработанные в process_resume_file)
    resume_local_path = None
    resume_google_drive_url = None
    
    resume_filename = dialog_data.get("resume_file")
    if resume_filename:
        resume_local_path = f"app/storage/resumes/{resume_filename}"
        resume_google_drive_url = dialog_data.get("resume_google_url", "")
        logger.info(f"📄 Файл резюме: {resume_filename}")
        if resume_google_drive_url:
            logger.info(f"☁️ Google Drive URL: {resume_google_drive_url}")
        else:
            logger.info(f"💾 Только локальное сохранение резюме")
    else:
        logger.warning("⚠️ Файл резюме не загружен")
    
    logger.info(f"📊 Подготавливаем данные заявки...")
    
    # Парсим текстовые данные с защитой от ошибок
    try:
        # Обрабатываем множественный выбор "Откуда узнали о КБК" из Multiselect
        multiselect = dialog_manager.find("how_found_multiselect")
        how_found_selections: list[str] = []

        if multiselect:
            how_found_selections = list(multiselect.get_checked())
        else:
            # Fallback к dialog_data если Multiselect не найден
            how_found_selections = dialog_data.get("how_found_selections", [])

        how_found_texts = []
        for selection in how_found_selections:
            try:
                idx = int(selection)
                if idx < len(config.selection.how_found_options):
                    how_found_texts.append(config.selection.how_found_options[idx])
            except (ValueError, IndexError):
                continue

        how_found_text = ", ".join(how_found_texts) if how_found_texts else ""
        logger.info(f"🔍 Как узнал о КБК: {how_found_text}")

        # Обрабатываем предыдущий отдел если участвовал в КБК
        previous_department_text = ""
        if "6" in how_found_selections:  # "Ранее участвовал в КБК"
            previous_dept_key = dialog_data.get("previous_department", "")
            previous_dept_name = dialog_data.get("previous_department_name")
            if previous_dept_key or previous_dept_name:
                previous_department_text = previous_dept_name or config.selection.departments.get(previous_dept_key, {}).get('name', previous_dept_key)
                logger.info(f"🏢 Предыдущий отдел в КБК: {previous_department_text}")

    except Exception as e:
        logger.error(f"❌ Ошибка обработки 'how_found_kbk': {e}")
        how_found_text = ""
        previous_department_text = ""
    
    try:
        # Обрабатываем приоритеты вакансий с учетом под-отделов
        priorities_data = {}
        priorities_text = ""
        
        # Для обратной совместимости используем первый приоритет как основной department/position
        main_department_name = ""
        main_position_text = ""
        
        for i in range(1, 4):
            dept_key = dialog_data.get(f"priority_{i}_department")
            subdept_key = dialog_data.get(f"priority_{i}_subdepartment")
            pos_index = dialog_data.get(f"priority_{i}_position")
            
            if dept_key and pos_index is not None:
                dept_data = config.selection.departments.get(dept_key, {})
                dept_name = dept_data.get("name", dept_key)
                
                # Если есть под-отдел
                if subdept_key and "subdepartments" in dept_data:
                    subdept_data = dept_data["subdepartments"].get(subdept_key, {})
                    subdept_name = subdept_data.get("name", subdept_key)
                    positions_list = subdept_data.get("positions", [])
                    full_dept_name = f"{dept_name} - {subdept_name}"
                else:
                    positions_list = dept_data.get("positions", [])
                    full_dept_name = dept_name
                
                # Получаем позицию по индексу из массива
                try:
                    pos_name = positions_list[int(pos_index)]
                except (IndexError, ValueError):
                    pos_name = "Неизвестная позиция"
                
                priorities_data[f"priority_{i}"] = f"{full_dept_name} - {pos_name}"
                priorities_text += f"{i}: {full_dept_name} - {pos_name}; "
                
                # Используем первый приоритет как основной
                if i == 1:
                    main_department_name = full_dept_name
                    main_position_text = pos_name
                
                logger.info(f"🎯 Приоритет {i}: {full_dept_name} - {pos_name}")
            else:
                priorities_data[f"priority_{i}"] = "Не выбрано"
        
        if not priorities_text:
            priorities_text = "Приоритеты не заданы"
        else:
            priorities_text = priorities_text.rstrip("; ")
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки приоритетов: {e}")
        priorities_text = "Ошибка обработки приоритетов"
        main_department_name = ""
        main_position_text = ""
    
    # Логируем все собранные данные
    logger.info(f"👤 ФИО: {dialog_data.get('full_name', 'не указано')}")
    logger.info(f"🎓 Университет: {dialog_data.get('university', 'не указано')}")
    logger.info(f"📚 Курс: {dialog_data.get('course', 'не указано')}")
    logger.info(f"📞 Телефон: {dialog_data.get('phone', 'не указано')}")
    logger.info(f"📧 Email: {dialog_data.get('email', 'не указано')}")
    
    # Сохраняем в БД и меняем статус на submitted
    logger.info(f"💾 Сохраняем заявку в базу данных...")
    
    def get_department_and_position_data(priority_num):
        """Получить данные департамента, под-отдела и позиции для приоритета"""
        dept_key = dialog_data.get(f"priority_{priority_num}_department")
        subdept_key = dialog_data.get(f"priority_{priority_num}_subdepartment")
        pos_index = dialog_data.get(f"priority_{priority_num}_position")
        
        logger.info(f"🔍 Обрабатываем приоритет {priority_num}: dept={dept_key}, subdept={subdept_key}, pos={pos_index}")
        
        if not dept_key or pos_index is None:
            logger.warning(f"⚠️ Приоритет {priority_num}: недостаточно данных")
            return None, None, None
            
        dept_data = config.selection.departments.get(dept_key, {})
        dept_name = dept_data.get("name", dept_key)
        subdept_name = None
        
        # Если есть под-отдел
        if subdept_key and "subdepartments" in dept_data:
            subdept_data = dept_data["subdepartments"].get(subdept_key, {})
            subdept_name = subdept_data.get("name", subdept_key)
            positions_list = subdept_data.get("positions", [])
            logger.info(f"📂 Приоритет {priority_num}: используем под-отдел '{subdept_name}' с {len(positions_list)} позициями")
        else:
            # Берем позиции напрямую из отдела
            positions_list = dept_data.get("positions", [])
            logger.info(f"📂 Приоритет {priority_num}: используем отдел '{dept_name}' с {len(positions_list)} позициями")
        
        try:
            position_name = positions_list[int(pos_index)]
            logger.info(f"✅ Приоритет {priority_num}: найдена позиция '{position_name}' по индексу {pos_index}")
        except (IndexError, ValueError) as e:
            position_name = "Неизвестная позиция"
            logger.error(f"❌ Приоритет {priority_num}: ошибка получения позиции по индексу {pos_index}: {e}")
            logger.error(f"❌ Доступные позиции: {positions_list}")
            
        return dept_name, subdept_name, position_name
    
    # Подготавливаем данные приоритетов для БД
    db_department_1, db_subdepartment_1, db_position_1 = get_department_and_position_data(1)
    db_department_2, db_subdepartment_2, db_position_2 = get_department_and_position_data(2)
    db_department_3, db_subdepartment_3, db_position_3 = get_department_and_position_data(3)

    logger.info(f"🎯 Сохраняем приоритеты:")
    logger.info(f"   1) {db_department_1} - {db_position_1} (под-отдел: {db_subdepartment_1})")
    logger.info(f"   2) {db_department_2} - {db_position_2} (под-отдел: {db_subdepartment_2})")
    logger.info(f"   3) {db_department_3} - {db_position_3} (под-отдел: {db_subdepartment_3})")
    
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
            department_1=db_department_1,
            position_1=db_position_1,
            subdepartment_1=db_subdepartment_1,
            department_2=db_department_2,
            position_2=db_position_2,
            subdepartment_2=db_subdepartment_2,
            department_3=db_department_3,
            position_3=db_position_3,
            subdepartment_3=db_subdepartment_3,
            experience=dialog_data.get("experience", ""),
            motivation=dialog_data.get("motivation", ""),
            resume_local_path=resume_local_path,
            resume_google_drive_url=resume_google_drive_url,
            previous_department=previous_department_text
        )
        logger.info(f"✅ Данные заявки сохранены в БД")
        
        # Обновляем статус пользователя на submitted
        logger.info(f"🔄 Обновляем статус пользователя на SUBMITTED...")
        await db.users.set_submission_status(user_id=event_from_user.id, status="submitted")
        logger.info(f"✅ Статус пользователя обновлен на SUBMITTED")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при сохранении в БД: {e}")
        logger.error(f"📋 Данные заявки: {dialog_data}")
        return
    
    # Подготавливаем данные для экспорта
    logger.info(f"📤 Подготавливаем данные для экспорта...")
    
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
        'previous_department': previous_department_text,
        # Новая система приоритетов с поддержкой под-отделов
        'department_1': db_department_1 or "",
        'position_1': db_position_1 or "",
        'subdepartment_1': db_subdepartment_1 or "",
        'department_2': db_department_2 or "",
        'position_2': db_position_2 or "",
        'subdepartment_2': db_subdepartment_2 or "",
        'department_3': db_department_3 or "",
        'position_3': db_position_3 or "",
        'subdepartment_3': db_subdepartment_3 or "",
        'priorities': priorities_text,
        'experience': dialog_data.get("experience", ""),
        'motivation': dialog_data.get("motivation", ""),
        'status': 'submitted',
        'resume_local_path': resume_local_path or "",
        'resume_google_drive_url': resume_google_drive_url or ""
    }
    
    logger.info(f"📊 Данные для экспорта подготовлены")
    
    # Сохраняем в CSV для бекапа
    logger.info(f"💾 Сохраняем резервную копию в CSV...")
    try:
        await save_to_csv(application_data)
        logger.info(f"✅ Резервная копия сохранена в CSV")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения в CSV: {e}")
    
    # Отправляем в Google Sheets если настроено
    if config.google:
        logger.info(f"☁️ Отправляем данные в Google Sheets...")
        try:
            from app.services.google_services import GoogleServicesManager
            google_manager = GoogleServicesManager(
                credentials_path=config.google.credentials_path,
                spreadsheet_id=config.google.spreadsheet_id,
                drive_folder_id=config.google.drive_folder_id,
                enable_drive=config.google.enable_drive
            )
            logger.info(f"📊 GoogleServicesManager инициализирован (Drive: {'включен' if config.google.enable_drive else 'отключен'})")
            
            success = await google_manager.add_application_to_sheet(application_data)
            if success:
                logger.info("✅ Заявка успешно добавлена в Google Sheets")
            else:
                logger.error("❌ Не удалось добавить заявку в Google Sheets")
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке в Google Sheets: {e}")
            if "quotaExceeded" in str(e):
                logger.error("💡 Возможно превышены лимиты Google Sheets API")
            elif "403" in str(e):
                logger.error("💡 Проверьте права доступа к Google Sheets")
            elif "404" in str(e):
                logger.error("💡 Проверьте ID таблицы Google Sheets")
    else:
        logger.info("ℹ️ Google Sheets не настроен, пропускаем экспорт")
    
    logger.info(f"🎉 Сохранение заявки пользователя {event_from_user.id} завершено успешно!")


async def save_to_csv(application_data: dict):
    """Сохранение данных в CSV файл"""
    import csv
    logger.info(f"📝 Сохраняем данные в CSV файл...")
    
    try:
        # Создаем директорию если её нет
        backup_dir = "app/storage/backups"
        os.makedirs(backup_dir, exist_ok=True)
        logger.info(f"📁 Директория {backup_dir} подготовлена")
        
        csv_path = f"{backup_dir}/applications.csv"
        file_exists = os.path.exists(csv_path)
        
        logger.info(f"📄 Путь к CSV файлу: {csv_path}")
        logger.info(f"📄 Файл существует: {file_exists}")
        
        with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'timestamp', 'user_id', 'username', 'full_name', 'university', 
                'course', 'phone', 'email', 'how_found_kbk', 'previous_department',
                'department_1', 'subdepartment_1', 'position_1', 
                'department_2', 'subdepartment_2', 'position_2', 
                'department_3', 'subdepartment_3', 'position_3', 
                'priorities', 'experience', 'motivation', 'status', 
                'resume_local_path', 'resume_google_drive_url'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                logger.info("📋 Создаем заголовки CSV файла...")
                writer.writeheader()
            
            logger.info("📝 Записываем данные заявки в CSV...")
            writer.writerow(application_data)
            logger.info("✅ Данные успешно записаны в CSV")
            
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения в CSV: {e}")
        raise


# Дополнительные обработчики для совместимости с dialogs.py
async def on_apply_clicked(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Начало заполнения заявки"""
    logger.info(f"🚀 Пользователь {callback.from_user.id} начал заполнение заявки")
    await callback.message.edit_caption("<b>Краткая справка по заполнению анкеты:</b>\n\nИспользуй /menu, чтобы отменить заполнение анкеты и вернуться в Личный Кабинет."
                                     "\n\nПеред отправкой у тебя будет возможность изменить данные, которые были введены.")
    await callback.message.answer("<b>Краткая справка по заполнению анкеты:</b>\n\nИспользуй /menu, чтобы отменить заполнение анкеты и вернуться в Личный Кабинет."
                                     "\n\nПеред отправкой у тебя будет возможность изменить данные, которые были введены.")
    await dialog_manager.switch_to(state=FirstStageSG.full_name, show_mode=ShowMode.SEND)

async def on_full_name_input(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    """Обработка ввода полного имени"""
    full_name = message.text.strip()
    logger.info(f"👤 Получено ФИО: {full_name} от пользователя {message.from_user.id}")
    
    # Разбиваем ФИО на части (Фамилия Имя Отчество)
    name_parts = full_name.split()
    
    if len(name_parts) >= 1:
        surname = name_parts[0]  # Первая часть - фамилия
        dialog_manager.dialog_data["surname"] = surname
        logger.info(f"   📝 Фамилия: {surname}")
    else:
        dialog_manager.dialog_data["surname"] = "User"
        logger.warning(f"⚠️ Не удалось извлечь фамилию из: {full_name}")
    
    if len(name_parts) >= 2:
        name = name_parts[1]  # Вторая часть - имя
        dialog_manager.dialog_data["name"] = name
        logger.info(f"   📝 Имя: {name}")
    else:
        dialog_manager.dialog_data["name"] = "Unknown"
        logger.warning(f"⚠️ Не удалось извлечь имя из: {full_name}")
    
    if len(name_parts) >= 3:
        patronymic = name_parts[2]  # Третья часть - отчество
        dialog_manager.dialog_data["patronymic"] = patronymic
        logger.info(f"   📝 Отчество: {patronymic}")
    else:
        dialog_manager.dialog_data["patronymic"] = ""  # Отчество может отсутствовать
        logger.info(f"   📝 Отчество: не указано")
    
    # Сохраняем полное имя
    dialog_manager.dialog_data["full_name"] = full_name
    
    logger.info(f"✅ ФИО успешно разобрано для пользователя {message.from_user.id}")
    await dialog_manager.next()

async def on_university_input(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    """Обработка ввода университета"""
    university = message.text.strip()
    logger.info(f"🏫 Получен университет: {university} от пользователя {message.from_user.id}")
    dialog_manager.dialog_data["university"] = university
    await dialog_manager.next()

async def on_phone_input(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    """Обработка ввода телефона"""
    phone = message.text.strip()
    logger.info(f"📞 Получен телефон: {phone} от пользователя {message.from_user.id}")
    
    # Простая валидация телефона
    if len(phone) >= 10:
        dialog_manager.dialog_data["phone"] = phone
        await dialog_manager.next()
    else:
        logger.warning(f"⚠️ Некорректный телефон от пользователя {message.from_user.id}: {phone}")
        await message.answer("Пожалуйста, введите корректный номер телефона (минимум 10 цифр)")

async def on_email_input(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    """Обработка ввода email"""
    email = message.text.strip()
    logger.info(f"📧 Получен email: {email} от пользователя {message.from_user.id}")
    
    if "@" in email and "." in email:
        dialog_manager.dialog_data["email"] = email
        await dialog_manager.next()
    else:
        logger.warning(f"⚠️ Некорректный email от пользователя {message.from_user.id}: {email}")
        await message.answer("Пожалуйста, введите корректный email адрес")

async def on_course_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id, **kwargs):
    """Обработка выбора курса"""
    logger.info(f"📚 Выбран курс: {item_id} пользователем {callback.from_user.id}")
    dialog_manager.dialog_data["course"] = item_id
    await dialog_manager.next()

async def on_how_found_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id, **kwargs):
    """Обработка выбора способа узнавания о КБК"""
    logger.info(f"🔍 Выбран способ узнавания: {item_id} пользователем {callback.from_user.id}")
    dialog_manager.dialog_data["how_found_kbk"] = item_id
    await dialog_manager.next()

async def on_department_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id, **kwargs):
    """Обработка выбора департамента"""
    logger.info(f"🏢 Выбран департамент: {item_id} пользователем {callback.from_user.id}")
    dialog_manager.dialog_data["selected_department"] = item_id
    await dialog_manager.next()

async def on_position_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id, **kwargs):
    """Обработка выбора позиции"""
    logger.info(f"💼 Выбрана позиция: {item_id} пользователем {callback.from_user.id}")
    dialog_manager.dialog_data["selected_position"] = item_id
    await dialog_manager.next()

async def on_experience_input(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    """Обработка ввода опыта"""
    experience = message.text.strip()
    logger.info(f"💼 Получен опыт от пользователя {message.from_user.id}: {len(experience)} символов")
    dialog_manager.dialog_data["experience"] = experience
    await dialog_manager.next()

async def on_motivation_input(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    """Обработка ввода мотивации"""
    motivation = message.text.strip()
    logger.info(f"💭 Получена мотивация от пользователя {message.from_user.id}: {len(motivation)} символов")
    dialog_manager.dialog_data["motivation"] = motivation
    await dialog_manager.next()

async def on_resume_uploaded(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    """Обработка загрузки резюме"""
    logger.info(f"📎 Начинаем обработку резюме от пользователя {message.from_user.id}")
    await process_resume_file(message, widget, dialog_manager, **kwargs)


async def on_skip_resume(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Обработка пропуска отправки резюме"""
    logger.info(f"⏭️ Пользователь {callback.from_user.id} пропускает отправку резюме")
    # Очищаем данные резюме
    dialog_manager.dialog_data.pop("resume_file_id", None)
    dialog_manager.dialog_data.pop("resume_filename", None)
    dialog_manager.dialog_data.pop("resume_text", None)
    await callback.answer("✅ Резюме пропущено!")
    await dialog_manager.switch_to(FirstStageSG.confirmation)


async def on_yes_previous_kbk(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Обработка выбора 'Да' для участия в предыдущих КБК"""
    logger.info(f"✅ Пользователь {callback.from_user.id} подтвердил участие в предыдущих КБК")
    dialog_manager.dialog_data["was_in_kbk"] = True
    await callback.answer("✅ Отлично!")
    await dialog_manager.switch_to(FirstStageSG.previous_department)


async def on_no_previous_kbk(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Обработка выбора 'Нет' для участия в предыдущих КБК"""
    logger.info(f"❌ Пользователь {callback.from_user.id} НЕ участвовал в предыдущих КБК")
    dialog_manager.dialog_data["was_in_kbk"] = False
    await callback.answer("✅ Понятно!")
    # Пропускаем выбор отдела КБК и переходим к выбору вакансий
    await dialog_manager.start("job_selection", data=dialog_manager.dialog_data)


async def on_submit_application(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Обработка финальной отправки заявки"""
    logger.info(f"🚀 Пользователь {callback.from_user.id} финально отправляет заявку")
    await save_application(dialog_manager)
    await callback.answer("✅ Заявка успешно отправлена!")
    await dialog_manager.switch_to(FirstStageSG.success)


async def on_back_to_menu(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Возврат в главное меню"""
    logger.info(f"🏠 Пользователь {callback.from_user.id} возвращается в главное меню")
    await callback.answer("🏠 Возвращаемся в меню")
    # Тут нужно будет перейти в главное меню диалога
    await dialog_manager.done()


# Новые обработчики для множественного выбора "Откуда узнали о КБК"
async def on_how_found_state_changed(callback: CallbackQuery, widget, dialog_manager: DialogManager, *args, **kwargs):
    """Обработчик изменения состояния в Multiselect"""
    logger.info(f"📢 Пользователь {callback.from_user.id} изменил выбор источников информации о КБК")
    
    # Получаем текущие выбранные элементы из Multiselect
    multiselect = dialog_manager.find("how_found_multiselect")
    if multiselect:
        checked_items = multiselect.get_checked()
        logger.info(f"📢 Текущие выборы: {checked_items}")
        logger.info(f"📢 Тип checked_items: {type(checked_items)}")
        
        # Сохраняем в dialog_data для совместимости с остальным кодом (как список)
        dialog_manager.dialog_data["how_found_selections"] = list(checked_items)
        logger.info(f"📢 Сохранено в dialog_data: {dialog_manager.dialog_data.get('how_found_selections')}")
        
        # Дополнительно сохраним в middleware_data для Redis
        if "dialog_data" not in dialog_manager.middleware_data:
            dialog_manager.middleware_data["dialog_data"] = {}
        dialog_manager.middleware_data["dialog_data"]["how_found_selections"] = list(checked_items)
        logger.info(f"📢 Также сохранено в middleware_data для Redis")
    else:
        logger.error(f"❌ Multiselect widget 'how_found_multiselect' не найден!")
    
    # Отвечаем на callback чтобы убрать "loading"
    await callback.answer()


async def on_how_found_toggled(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id, **kwargs):
    """Обработчик изменения состояния в Multiselect (устаревший)"""
    logger.info(f"📢 Пользователь {callback.from_user.id} изменил выбор опции: {item_id}")
    
    # Получаем текущие выбранные элементы из Multiselect
    multiselect = dialog_manager.find("how_found_multiselect")
    if multiselect:
        checked_items = multiselect.get_checked()
        logger.info(f"📢 Текущие выборы: {checked_items}")
        
    # Сохраняем в dialog_data для совместимости с остальным кодом (как список)
    dialog_manager.dialog_data["how_found_selections"] = list(checked_items)


async def on_how_found_continue(callback: CallbackQuery, widget, dialog_manager: DialogManager, **kwargs):
    """Обработчик кнопки 'Далее' после выбора источников информации о КБК"""
    logger.info(f"🔄 Пользователь {callback.from_user.id} нажал 'Далее' для источников информации")
    
    # Получаем выбранные опции из Multiselect виджета
    multiselect = dialog_manager.find("how_found_multiselect")
    checked_items = []
    
    if multiselect:
        checked_items = multiselect.get_checked()
        logger.info(f"📢 Найден multiselect, checked_items: {checked_items}")
    else:
        logger.warning(f"❌ Multiselect not found!")
        
    # Также попробуем получить из dialog_data (для Redis)
    saved_selections = dialog_manager.dialog_data.get("how_found_selections", [])
    logger.info(f"📢 Из dialog_data: {saved_selections}")
    
    # Используем тот список, который не пустой
    if not checked_items and saved_selections:
        checked_items = list(saved_selections)
        logger.info(f"📢 Используем сохраненные выборы: {checked_items}")
    
    logger.info(f"📢 Пользователь {callback.from_user.id} завершил выбор источников: {checked_items}")
    
    # Проверяем, есть ли хотя бы один выбор
    if not checked_items:
        await callback.answer("❌ Пожалуйста, выберите хотя бы один вариант", show_alert=True)
        return
    
    # Сохраняем выбранные варианты в dialog_data для использования в других частях кода (как список)
    dialog_manager.dialog_data["how_found_selections"] = list(checked_items)
    
    # Если пользователь НЕ выбрал "Ранее участвовал в КБК" (индекс 6), пропускаем окно previous_department
    if "6" not in checked_items:
        logger.info(f"⏭️ Пользователь не участвовал в КБК, пропускаем выбор предыдущего отдела")
        await callback.message.edit_text(
            text="Ты можешь выбрать до 3-х направлений, в которых хотел бы себя попробовать.\n\n" \
                "Не забудь расставить их по уровню предпочтительности: приоритет №1 — самое желанное.\n\n" \
                "Если ты успешно пройдешь отбор на несколько направлений, то мы определим тебя в отдел с самым высоким приоритетом!\n\n" \
                "<b>Пример:</b> 1-й приоритет — отдел SMM&PR, 2-й приоритет — отдел партнеров, 3-й приоритет — отдел программы&"
                                                    )
        await dialog_manager.start(JobSelectionSG.select_department, show_mode=ShowMode.SEND)  # Пропускаем его и идем к experience
        return
    
    # Переходим к следующему окну (previous_department)
    await dialog_manager.next()


async def on_previous_department_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id, **kwargs):
    """Обработчик выбора отдела предыдущего участия в КБК"""
    logger.info(f"🏢 Пользователь {callback.from_user.id} выбрал предыдущий отдел: {item_id}")
    # Сохраняем и ключ, и отображаемое имя (для legacy списков)
    dialog_manager.dialog_data["previous_department"] = item_id
    try:
        # widget should be Radio; get item text
        item = widget.get_checked() if hasattr(widget, "get_checked") else None
    except Exception:
        item = None
    # Надежнее получить текст через data из getter'а, но проще — взять его из callback.data недоступно, поэтому используем find
    # aiogram-dialog предоставляет метод find для Radio, но здесь мы просто попробуем взять текст из текущих items
    try:
        dm = dialog_manager
        data = await dm.middleware_data.get("dialog_data", {})  # may be empty
    except Exception:
        data = {}
    # Установим имя через mapping из нашего legacy getter: повторно построим карту
    legacy_map = {
        "legacy_program": "Отдел программы",
        "legacy_creative": "Творческий отдел",
        "legacy_partners": "Отдел партнёров",
        "legacy_smm_pr": "SMM&PR",
        "legacy_design": "Отдел дизайна",
        "legacy_logistics_it": "Логистика и ИТ",
        "legacy_cultural": "Культурно-экспертный отдел",
    }
    dialog_manager.dialog_data["previous_department_name"] = legacy_map.get(item_id, item_id)
    await callback.message.edit_text(
            text="Ты можешь выбрать до 3-х направлений, в которых хотел бы себя попробовать.\n\n" \
                "Не забудь расставить их по уровню предпочтительности: приоритет №1 — самое желанное.\n\n" \
                "Если ты успешно пройдешь отбор на несколько направлений, то мы определим тебя в отдел с самым высоким приоритетом!\n\n" \
                "<b>Пример:</b> 1-й приоритет — отдел SMM&PR, 2-й приоритет — отдел партнеров, 3-й приоритет — отдел программы."
                                                    )
    await dialog_manager.start(JobSelectionSG.select_department, show_mode=ShowMode.SEND)


# ======================
# ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ
# ======================

async def on_edit_clicked(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Обработчик кнопки 'Изменить' на окне подтверждения"""
    logger.info(f"✏️ Пользователь {callback.from_user.id} запросил редактирование заявки")
    await dialog_manager.switch_to(FirstStageSG.edit_menu)


async def on_edit_field_clicked(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Универсальный обработчик кнопок редактирования полей"""
    button_id = button.widget_id
    user_id = callback.from_user.id
    
    logger.info(f"✏️ Пользователь {user_id} выбрал редактирование поля: {button_id}")
    
    # Специальная обработка для выбора вакансий
    if button_id == "edit_department":
        # Переходим к новой системе выбора вакансий в режиме редактирования
        from app.bot.states.job_selection import JobSelectionSG
        logger.info(f"🎯 Пользователь {user_id} переходит к редактированию выбора вакансий")
        
        # Передаем ВСЕ текущие данные формы в диалог выбора вакансий
        current_data = dict(dialog_manager.dialog_data)
        
        # Добавляем также данные из start_data если они есть
        if dialog_manager.start_data:
            current_data.update(dialog_manager.start_data)
        
        # ВАЖНО: Добавляем флаг редактирования
        current_data["is_editing"] = True
        
        logger.info(f"🔄 Передаем данные в диалог выбора вакансий: {list(current_data.keys())}")
        await dialog_manager.start(JobSelectionSG.priorities_overview, data=current_data)
        return
    
    # Определяем состояние для редактирования на основе ID кнопки
    field_to_state = {
        "edit_full_name": FirstStageSG.edit_full_name,
        "edit_university": FirstStageSG.edit_university,
        "edit_course": FirstStageSG.edit_course,
        "edit_phone": FirstStageSG.edit_phone,
        "edit_email": FirstStageSG.edit_email,
        "edit_how_found": FirstStageSG.edit_how_found_kbk,
        "edit_experience": FirstStageSG.edit_experience,
        "edit_motivation": FirstStageSG.edit_motivation,
        "edit_resume": FirstStageSG.edit_resume_upload,
    }
    
    target_state = field_to_state.get(button_id)
    if target_state:
        await dialog_manager.switch_to(target_state)
    else:
        logger.error(f"❌ Неизвестная кнопка редактирования: {button_id}")


async def on_edit_full_name_input(message: Message, widget, dialog_manager: DialogManager, value, **kwargs):
    """Обработка изменения ФИО"""
    full_name = value.strip()
    logger.info(f"✏️👤 Пользователь {message.from_user.id} изменил ФИО: {full_name}")
    
    # Обновляем данные (аналогично основной логике)
    name_parts = full_name.split()
    
    if len(name_parts) >= 1:
        dialog_manager.dialog_data["surname"] = name_parts[0]
    else:
        dialog_manager.dialog_data["surname"] = "User"
    
    if len(name_parts) >= 2:
        dialog_manager.dialog_data["name"] = name_parts[1]
    else:
        dialog_manager.dialog_data["name"] = "Unknown"
    
    if len(name_parts) >= 3:
        dialog_manager.dialog_data["patronymic"] = name_parts[2]
    else:
        dialog_manager.dialog_data["patronymic"] = ""
    
    dialog_manager.dialog_data["full_name"] = full_name
    
    await message.answer("✅ ФИО успешно изменено!")
    await dialog_manager.switch_to(FirstStageSG.confirmation)


async def on_edit_university_input(message: Message, widget, dialog_manager: DialogManager, value, **kwargs):
    """Обработка изменения университета"""
    university = value.strip()
    logger.info(f"✏️🏫 Пользователь {message.from_user.id} изменил университет: {university}")
    dialog_manager.dialog_data["university"] = university
    await message.answer("✅ Учебное заведение успешно изменено!")
    await dialog_manager.switch_to(FirstStageSG.confirmation)


async def on_edit_course_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id, **kwargs):
    """Обработка изменения курса"""
    logger.info(f"✏️📚 Пользователь {callback.from_user.id} изменил курс: {item_id}")
    dialog_manager.dialog_data["course"] = item_id
    await callback.answer("✅ Курс успешно изменен!")
    await dialog_manager.switch_to(FirstStageSG.confirmation)


async def on_edit_phone_input(message: Message, widget, dialog_manager: DialogManager, value, **kwargs):
    """Обработка изменения телефона"""
    phone = value.strip()
    logger.info(f"✏️📞 Пользователь {message.from_user.id} изменил телефон: {phone}")
    
    if len(phone) >= 10:
        dialog_manager.dialog_data["phone"] = phone
        await message.answer("✅ Номер телефона успешно изменен!")
        await dialog_manager.switch_to(FirstStageSG.confirmation)
    else:
        logger.warning(f"⚠️ Некорректный телефон от пользователя {message.from_user.id}: {phone}")
        await message.answer("❌ Пожалуйста, введите корректный номер телефона (минимум 10 цифр)")


async def on_edit_email_input(message: Message, widget, dialog_manager: DialogManager, value, **kwargs):
    """Обработка изменения email"""
    email = value.strip()
    logger.info(f"✏️📧 Пользователь {message.from_user.id} изменил email: {email}")
    
    if "@" in email and "." in email:
        dialog_manager.dialog_data["email"] = email
        await message.answer("✅ Email успешно изменен!")
        await dialog_manager.switch_to(FirstStageSG.confirmation)
    else:
        logger.warning(f"⚠️ Некорректный email от пользователя {message.from_user.id}: {email}")
        await message.answer("❌ Пожалуйста, введите корректный email адрес")


async def on_edit_how_found_state_changed(callback: CallbackQuery, widget, dialog_manager: DialogManager, *args, **kwargs):
    """Обработчик изменения множественного выбора при редактировании"""
    logger.info(f"✏️📢 Пользователь {callback.from_user.id} изменил выбор источников информации о КБК")
    
    # Получаем текущие выбранные элементы из Multiselect
    multiselect = dialog_manager.find("edit_how_found_multi")
    if multiselect:
        checked_items = multiselect.get_checked()
        logger.info(f"📢 Обновленный выбор: {checked_items}")
        # Сохраняем в dialog_data как список (JSON-совместимый)
        dialog_manager.dialog_data["how_found_selections"] = list(checked_items)


async def on_edit_how_found_continue(callback: CallbackQuery, widget, dialog_manager: DialogManager, **kwargs):
    """Обработчик завершения редактирования источников информации"""
    multiselect = dialog_manager.find("edit_how_found_multi")
    
    if multiselect:
        checked_items = multiselect.get_checked()
        if not checked_items:
            await callback.answer("❌ Пожалуйста, выберите хотя бы один вариант", show_alert=True)
            return
        dialog_manager.dialog_data["how_found_selections"] = list(checked_items)
        
        # Проверяем, выбрал ли пользователь "Ранее участвовал в КБК" (индекс 6)
        if "6" in checked_items:
            logger.info(f"⏭️ Пользователь {callback.from_user.id} выбрал 'Ранее участвовал в КБК', переходим к выбору предыдущего отдела")
            await callback.answer("✅ Источники информации обновлены!")
            await dialog_manager.switch_to(FirstStageSG.edit_previous_department)
        else:
            # Если не выбрал участие в КБК, очищаем данные о предыдущем отделе
            dialog_manager.dialog_data.pop("previous_department", None)
            dialog_manager.dialog_data.pop("previous_department_name", None)
            logger.info(f"🔄 Пользователь {callback.from_user.id} не участвовал в КБК, очищаем данные о предыдущем отделе")
            await callback.answer("✅ Источники информации о КБК успешно изменены!")
            await dialog_manager.switch_to(FirstStageSG.confirmation)


async def on_edit_previous_department_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id, **kwargs):
    """Обработка изменения предыдущего отдела"""
    logger.info(f"✏️🏢 Пользователь {callback.from_user.id} изменил предыдущий отдел: {item_id}")
    dialog_manager.dialog_data["previous_department"] = item_id
    legacy_map = {
        "legacy_program": "Отдел программы",
        "legacy_creative": "Творческий отдел",
        "legacy_partners": "Отдел партнёров",
        "legacy_smm_pr": "SMM&PR",
        "legacy_design": "Отдел дизайна",
        "legacy_logistics_it": "Логистика и ИТ",
        "legacy_cultural": "Культурно-экспертный отдел",
    }
    dialog_manager.dialog_data["previous_department_name"] = legacy_map.get(item_id, item_id)
    await callback.answer("✅ Предыдущий отдел успешно изменен!")
    await dialog_manager.switch_to(FirstStageSG.confirmation)


async def on_edit_experience_input(message: Message, widget, dialog_manager: DialogManager, value, **kwargs):
    """Обработка изменения опыта"""
    experience = value.strip()
    logger.info(f"✏️💼 Пользователь {message.from_user.id} изменил опыт: {len(experience)} символов")
    dialog_manager.dialog_data["experience"] = experience
    await message.answer("✅ Опыт успешно изменен!")
    await dialog_manager.switch_to(FirstStageSG.confirmation)


async def on_edit_motivation_input(message: Message, widget, dialog_manager: DialogManager, value, **kwargs):
    """Обработка изменения мотивации"""
    motivation = value.strip()
    logger.info(f"✏️💭 Пользователь {message.from_user.id} изменил мотивацию: {len(motivation)} символов")
    dialog_manager.dialog_data["motivation"] = motivation
    await message.answer("✅ Мотивация успешно изменена!")
    await dialog_manager.switch_to(FirstStageSG.confirmation)


async def on_edit_resume_uploaded(message: Message, widget, dialog_manager: DialogManager, **kwargs):
    """Обработка изменения резюме"""
    logger.info(f"✏️📎 Пользователь {message.from_user.id} загружает новое резюме")
    # Используем расширенную логику обработки резюме (поддерживает файлы и текст)
    await process_resume_file(message, widget, dialog_manager, **kwargs)
    await message.answer("✅ Резюме успешно изменено!")
    await dialog_manager.switch_to(FirstStageSG.confirmation)


async def on_skip_edit_resume(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Обработка пропуска отправки резюме при редактировании"""
    logger.info(f"✏️⏭️ Пользователь {callback.from_user.id} пропускает отправку резюме при редактировании")
    # Очищаем данные резюме, если нужно
    dialog_manager.dialog_data.pop("resume_file_id", None)
    dialog_manager.dialog_data.pop("resume_filename", None)
    dialog_manager.dialog_data.pop("resume_text", None)
    await callback.answer("✅ Резюме не будет изменено!")
    await dialog_manager.switch_to(FirstStageSG.confirmation)


async def on_edit_department_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id, **kwargs):
    """Обработка изменения отдела"""
    logger.info(f"✏️🏢 Пользователь {callback.from_user.id} изменил отдел: {item_id}")
    dialog_manager.dialog_data["selected_department"] = item_id
    await callback.answer("✅ Отдел успешно изменен!")
    # Переходим к выбору должности в новом отделе
    await dialog_manager.switch_to(FirstStageSG.edit_position)


async def on_edit_position_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id, **kwargs):
    """Обработка изменения должности"""
    logger.info(f"✏️💼 Пользователь {callback.from_user.id} изменил должность: {item_id}")
    dialog_manager.dialog_data["selected_position"] = item_id
    await callback.answer("✅ Должность успешно изменена!")
    await dialog_manager.switch_to(FirstStageSG.confirmation)


async def on_back_to_confirmation(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Возврат к окну подтверждения без изменений"""
    logger.info(f"🔙 Пользователь {callback.from_user.id} вернулся к подтверждению")
    await dialog_manager.switch_to(FirstStageSG.confirmation)


async def check_previous_participation_and_skip(dialog_manager: DialogManager):
    """Проверяет, участвовал ли пользователь в КБК ранее, и пропускает окно если нет"""
    selections = dialog_manager.dialog_data.get("how_found_selections", [])
    
    # Если не выбрал "Ранее участвовал в КБК" (индекс 6), пропускаем окно
    if "6" not in selections:
        logger.info(f"⏭️ Пользователь не участвовал в КБК ранее, пропускаем окно выбора предыдущего отдела")
        await dialog_manager.next()  # Пропускаем окно предыдущего отдела
        return True
    
    return False
