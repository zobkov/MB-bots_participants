import logging
from typing import Dict, List, Any
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Column, Back, Select, Group, Cancel
from aiogram_dialog.widgets.text import Const, Format
from aiogram.types import CallbackQuery

from app.bot.states.timetable import TimetableSG
from config.config import Config, Event

logger = logging.getLogger(__name__)


async def get_days_data(dialog_manager: DialogManager, **kwargs):
    """Получение данных для списка дней"""
    try:
        config: Config = kwargs["config"]
        
        # Получаем дни с мероприятиями
        days_with_events = config.get_days_with_events()
        
        days_data = []
        for day in days_with_events:
            days_data.append({
                "day": day,
                "day_name": f"День {day}"
            })
        
        logger.info(f"Loaded {len(days_data)} days with events")
        return {
            "days": days_data
        }
    except Exception as e:
        logger.error(f"Error getting days data: {e}")
        return {
            "days": []
        }


async def get_day_events_data(dialog_manager: DialogManager, **kwargs):
    """Получение данных для списка событий дня"""
    try:
        config: Config = kwargs["config"]
        
        # Получаем выбранный день из контекста диалога
        selected_day = dialog_manager.dialog_data.get("selected_day", 0)
        
        # Получаем события для этого дня
        day_events = config.get_day_events(selected_day)
        
        # Формируем текст расписания
        schedule_text = f"<b>Расписание - День {selected_day}</b>\n\n"
        
        events_data = []
        for event in day_events:
            schedule_text += f"{event.start_time}-{event.end_time} – <b>{event.title}</b> ({event.location})\n\n"
            events_data.append({
                "id": hash(f"{event.title}_{event.start_date}_{event.start_time}"),  # Уникальный ID
                "title": event.title,
                "event": event  # Сохраняем полный объект события
            })
        
        logger.info(f"Loaded {len(events_data)} events for day {selected_day}")
        return {
            "schedule_text": schedule_text,
            "events": events_data,
            "selected_day": selected_day
        }
    except Exception as e:
        logger.error(f"Error getting day events data: {e}")
        return {
            "schedule_text": "Ошибка загрузки расписания",
            "events": [],
            "selected_day": 0
        }


async def get_event_detail_data(dialog_manager: DialogManager, **kwargs):
    """Получение данных для детального просмотра события"""
    try:
        config: Config = kwargs["config"]
        
        # Получаем ID выбранного события
        selected_event_id = dialog_manager.dialog_data.get("selected_event_id")
        selected_day = dialog_manager.dialog_data.get("selected_day", 0)
        
        # Находим событие по ID
        day_events = config.get_day_events(selected_day)
        selected_event = None
        
        for event in day_events:
            event_id = hash(f"{event.title}_{event.start_date}_{event.start_time}")
            if event_id == selected_event_id:
                selected_event = event
                break
        
        if not selected_event:
            logger.warning(f"Event with ID {selected_event_id} not found for day {selected_day}")
            return {"event_detail": "Мероприятие не найдено"}
        
        # Формируем текст детального описания
        detail_text = f"<b>{selected_event.title}</b>\n"
        detail_text += f"<i>{selected_event.location}</i>\n\n"
        detail_text += f"{selected_event.description}\n\n"
        detail_text += f"{selected_event.start_time} – {selected_event.end_time}"
        
        logger.info(f"Loaded event detail for: {selected_event.title}")
        return {
            "event_detail": detail_text
        }
    except Exception as e:
        logger.error(f"Error getting event detail data: {e}")
        return {
            "event_detail": "Ошибка загрузки мероприятия"
        }


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


timetable_dialog = Dialog(
    # Окно со списком дней
    Window(
        Const("Расписание конференции"),
        Group(
            Select(
                Format("{item[day_name]}"),
                id="day_select",
                items="days",
                item_id_getter=lambda item: item["day"],
                on_click=on_day_selected
            ),
            width=1
        ),
        Cancel(Const("⬅️ Назад"),id="timetable_to_menu"),
        state=TimetableSG.days_list,
        getter=get_days_data,
    ),
    
    # Окно с событиями выбранного дня
    Window(
        Format("{schedule_text}"),
        Group(
            Select(
                Format("{item[title]}"),
                id="event_select",
                items="events",
                item_id_getter=lambda item: item["id"],
                on_click=on_event_selected
            ),
            width=1
        ),
        Back(Const("⬅️ Назад"), id="back_to_days"),
        state=TimetableSG.day_events,
        getter=get_day_events_data,
    ),
    
    # Окно с детальной информацией о событии
    Window(
        Format("{event_detail}"),
        Back(Const("⬅️ Назад"), id="back_to_events"),
        state=TimetableSG.event_detail,
        getter=get_event_detail_data,
        parse_mode="HTML"
    ),
)
