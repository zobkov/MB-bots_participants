import logging
from aiogram_dialog import DialogManager
from aiogram.types import CallbackQuery

from .states import TimetableSG

logger = logging.getLogger(__name__)


async def on_day_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str):
    """Обработчик выбора дня"""
    try:
        selected_day = int(item_id)
        dialog_manager.dialog_data["selected_day"] = selected_day
        logger.info(f"Day selected: {selected_day}")
        await dialog_manager.switch_to(TimetableSG.day_events)
    except Exception as e:
        logger.error(f"Error selecting day: {e}")
        await callback.answer("Ошибка при выборе дня", show_alert=True)


async def on_event_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str):
    """Обработчик выбора события"""
    try:
        selected_event_id = int(item_id)
        dialog_manager.dialog_data["selected_event_id"] = selected_event_id
        logger.info(f"Event selected: {selected_event_id}")
        await dialog_manager.switch_to(TimetableSG.event_detail)
    except Exception as e:
        logger.error(f"Error selecting event: {e}")
        await callback.answer("Ошибка при выборе события", show_alert=True)