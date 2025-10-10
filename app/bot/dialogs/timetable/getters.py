import logging
from typing import Dict, List, Any
from aiogram_dialog import DialogManager

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