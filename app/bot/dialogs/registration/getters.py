"""Getters for registration dialog"""

from typing import Dict, Any
from aiogram_dialog import DialogManager
from app.infrastructure.database import RedisManager


async def get_debate_registration_data(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """Get data for debate registration window"""
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]
    
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
    
    return {
        "cases_text": "\n\n".join(cases_text),
        "remaining": remaining,
        "case_names": case_names,
        "vtb_button_text": vtb_text,
        "alabuga_button_text": alabuga_text,
        "b1_button_text": b1_text,
        "severstal_button_text": severstal_text,
        "alpha_button_text": alpha_text,
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