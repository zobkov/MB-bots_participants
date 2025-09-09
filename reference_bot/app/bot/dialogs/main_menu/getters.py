from datetime import datetime
from typing import Dict, Any

from aiogram.types import User
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram.enums import ContentType

from config.config import Config
from app.infrastructure.database.database.db import DB
from app.utils.optimized_dialog_widgets import get_file_id_for_path


async def get_user_info(dialog_manager: DialogManager, event_from_user: User, **kwargs) -> Dict[str, Any]:
    """Получаем информацию о пользователе"""
    
    return {
        "user_id": event_from_user.id,
        "username": event_from_user.username or "",
        "first_name": event_from_user.first_name or "",
        "last_name": event_from_user.last_name or "",
    }


async def get_current_stage_info(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """Получаем информацию о текущем этапе отбора"""
    config: Config = dialog_manager.middleware_data.get("config")
    db: DB = dialog_manager.middleware_data.get("db")
    event_from_user: User = dialog_manager.event.from_user
    
    if not config:
        return {
            "current_stage": "Неизвестно",
            "current_stage_description": "Информация недоступна",
            "is_active": False
        }
    
    # Получаем статус заявки пользователя из таблицы users (submission_status)
    application_submitted = False
    try:
        if db:
            user_record = await db.users.get_user_record(user_id=event_from_user.id)
            application_submitted = bool(user_record and user_record.submission_status == "submitted")
    except Exception:
        application_submitted = False
    
    now = datetime.now()
    current_stage = None
    current_stage_info = None
    next_stage_info = None
    
    # Сортируем этапы по дате начала
    sorted_stages = sorted(
        config.selection.stages.items(),
        key=lambda x: datetime.fromisoformat(x[1]["start_date"])
    )
    
    # Находим текущий этап
    for i, (stage_key, stage_data) in enumerate(sorted_stages):
        start_date = datetime.fromisoformat(stage_data["start_date"])
        end_date = datetime.fromisoformat(stage_data["end_date"])
        
        if start_date <= now <= end_date:
            current_stage = stage_key
            current_stage_info = stage_data
            # Находим следующий этап
            if i + 1 < len(sorted_stages):
                next_stage_info = sorted_stages[i + 1][1]
            break
    
    if not current_stage:
        # Проверяем будущие этапы
        for stage_key, stage_data in sorted_stages:
            start_date = datetime.fromisoformat(stage_data["start_date"])
            if now < start_date:
                current_stage = stage_key
                current_stage_info = stage_data
                current_stage_info["status"] = "upcoming"
                break
    
    if not current_stage_info:
        current_stage_info = {
            "name": "Отбор завершен",
            "description": "Все этапы отбора завершены",
            "status": "completed"
        }
    
    # Добавляем информацию о дедлайнах
    deadline_info = ""
    if current_stage_info and current_stage != "completed":
        if "start_date" in current_stage_info and current_stage_info.get("status") == "upcoming":
            # Для будущих этапов показываем дату начала
            start_date = datetime.fromisoformat(current_stage_info["start_date"])
            deadline_info = f"🚀 Начало: {start_date.strftime('%d.%m.%Y, %H:%M')}"
            
            # Рассчитываем время до начала
            time_until = start_date - now
            if time_until.days > 0:
                deadline_info += f"\n⏳ До начала: {time_until.days} дн."
            elif time_until.seconds > 3600:
                hours_until = time_until.seconds // 3600
                deadline_info += f"\n⏳ До начала: {hours_until} ч."
        elif "end_date" in current_stage_info:
            # Для текущих этапов показываем дедлайн или результаты в зависимости от статуса заявки
            end_date = datetime.fromisoformat(current_stage_info["end_date"])
            
            if application_submitted and "results_date" in current_stage_info:
                # Если заявка подана, показываем когда придут результаты
                results_date = datetime.fromisoformat(current_stage_info["results_date"])
                deadline_info = f"Готово! Твоя заявка отправлена. Результаты придут: <b>{results_date.strftime('%d.%m.%Y, %H:%M')}</b>"
            else:
                # Если заявка не подана, показываем дедлайн
                deadline_info = f"Подай заявку до <b>{end_date.strftime('%d.%m.%Y, %H:%M')}</b>, чтобы перейти к следующему этапу"
            
            # Рассчитываем оставшееся время
            """ Убрал "Осталоь ... дн" так как динамическая информация в статическом сообщении
            time_left = end_date - now
            if time_left.days > 7:
                deadline_info += f"\n⏳ Осталось: {time_left.days} дн."
            elif time_left.days > 0:
                deadline_info += f"\n🔥 <b>Осталось: {time_left.days} дн.</b>"
            elif time_left.seconds > 3600:
                hours_left = time_left.seconds // 3600
                deadline_info += f"\n🔥 <b>Осталось: {hours_left} ч.</b>"
            elif time_left.seconds > 0:
                deadline_info += f"\n🚨 <b>Осталось: менее часа!</b>"
            else:
                deadline_info += f"\n❌ <b>Дедлайн истек</b>"
            """
    
    # Добавляем информацию о следующем этапе
    next_stage_text = ""
    if next_stage_info and current_stage_info.get("status") != "upcoming":
        next_start = datetime.fromisoformat(next_stage_info["start_date"])
        next_stage_text = f"\n\n📋 <b>Следующий этап:</b> {next_stage_info['name']}\n🚀 <b>Начало:</b> {next_start.strftime('%d.%m.%Y, %H:%M')}"
    
    return {
        "current_stage": current_stage or "completed",
        "stage_name": current_stage_info["name"],
        "stage_description": current_stage_info.get("description", "") + next_stage_text,
        "stage_status": current_stage_info.get("status", "active"),
        "deadline_info": deadline_info
    }


async def get_application_status(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """Получаем статус заявки пользователя"""
    event_from_user: User = dialog_manager.event.from_user
    
    # Получаем объект DB из middleware_data
    db: DB = dialog_manager.middleware_data.get("db")
    
    if not db:
        return {
            "application_status": "not_submitted",
            "status_text": "Заявка не подана",
            "can_apply": True
        }
    
    try:
        # Ensure application row exists for form fields (no status stored here)
        await db.applications.create_application(user_id=event_from_user.id)
        user_record = await db.users.get_user_record(user_id=event_from_user.id)
        application_status = (user_record.submission_status if user_record else "not_submitted")
        status_text = {
            "not_submitted": "Заявка не подана",
            "submitted": "Заявка подана"
        }.get(application_status, "Неизвестный статус")
    except Exception as e:
        # В случае ошибки возвращаем значения по умолчанию
        application_status = "not_submitted"
        status_text = "Заявка не подана"
    
    return {
        "application_status": application_status,
        "status_text": status_text,
        "can_apply": application_status == "not_submitted"
    }


async def get_support_contacts(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """Получаем контакты поддержки"""
    config: Config = dialog_manager.middleware_data.get("config")
    
    if not config:
        return {
            "general_support": "Недоступно",
            "technical_support": "Недоступно",
            "hr_support": "Недоступно"
        }
    
    return {
        "general_support": config.selection.support_contacts["general"],
        "technical_support": config.selection.support_contacts["technical"],
        "hr_support": config.selection.support_contacts["hr"]
    }


async def get_main_menu_media(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """Получаем медиа для главного меню"""
    file_id = get_file_id_for_path("main_menu/main_menu.jpg")
    
    if file_id:
        # Используем file_id для быстрой отправки
        media = MediaAttachment(
            type=ContentType.PHOTO,
            file_id=MediaId(file_id)
        )
    else:
        # Fallback на путь к файлу
        media = MediaAttachment(
            type=ContentType.PHOTO,
            path="app/bot/assets/images/main_menu/main_menu.jpg"
        )
    
    return {
        "media": media
    }
