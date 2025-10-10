"""Getters for registration dialog"""

from typing import Dict, Any
from aiogram_dialog import DialogManager
from app.infrastructure.database import RedisManager, DatabaseManager


async def get_debate_registration_data(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """Get data for debate registration window"""
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    
    # Get user info
    user_id = dialog_manager.event.from_user.id
    user_registration = await db_manager.check_user_already_registered(user_id)
    
    # Get remaining slots for each case
    remaining = await redis_manager.get_remaining_slots()
    
    # Get case names
    case_names = {
        1: "ВТБ",
        2: "Алабуга", 
        3: "Б1",
        4: "Северсталь",
        5: "Альфа"
    }
    
    # Format text for each case
    cases_text = []
    for case_num in range(1, 6):
        name = case_names[case_num]
        remaining_count = remaining[case_num]
        cases_text.append(f"— Кейс {name}\n<i>Осталось мест: {remaining_count}</i>")
    
    # Format button texts with lock emoji for unavailable cases
    vtb_text = "ВТБ" if remaining[1] > 0 else "🔒 ВТБ"
    alabuga_text = "Алабуга" if remaining[2] > 0 else "🔒 Алабуга"
    b1_text = "Б1" if remaining[3] > 0 else "🔒 Б1"
    severstal_text = "Северсталь" if remaining[4] > 0 else "🔒 Северсталь"
    alpha_text = "Альфа" if remaining[5] > 0 else "🔒 Альфа"
    
    # User status text
    user_status = ""
    is_registered = False
    if user_registration:
        is_registered = True
        current_case_name = case_names.get(user_registration, "Unknown")
        user_status = f"📝 <b>Вы зарегистрированы на кейс: {current_case_name}</b>"
    else:
        user_status = "ℹ️ <i>Вы еще не зарегистрированы на дебаты</i>"
    
    return {
        "cases_text": "\n\n".join(cases_text),
        "remaining": remaining,
        "case_names": case_names,
        "vtb_button_text": vtb_text,
        "alabuga_button_text": alabuga_text,
        "b1_button_text": b1_text,
        "severstal_button_text": severstal_text,
        "alpha_button_text": alpha_text,
        "user_status": user_status,
        "is_registered": is_registered,
    }


async def get_confirmation_data(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """Get data for confirmation window"""
    case_number = dialog_manager.dialog_data.get("selected_case")
    
    case_names = {
        1: "ВТБ",
        2: "Алабуга", 
        3: "Б1", 
        4: "Северсталь",
        5: "Альфа"
    }
    
    case_name = case_names.get(case_number, "Unknown")
    
    return {
        "case_name": case_name,
        "case_number": case_number
    }


async def get_unregister_confirmation_data(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """Get data for unregister confirmation window"""
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]
    
    user_id = dialog_manager.event.from_user.id
    user_registration = await db_manager.check_user_already_registered(user_id)
    
    current_case_name = "Unknown"
    if user_registration:
        current_case_name = await redis_manager.get_case_name(user_registration)
    
    return {
        "current_case_name": current_case_name,
        "current_case_number": user_registration
    }