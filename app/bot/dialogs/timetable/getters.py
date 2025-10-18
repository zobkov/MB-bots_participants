import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram.enums import ContentType

from app.infrastructure.database import DatabaseManager, RedisManager
from config.config import Config
from .utils import (
    ScheduleItem,
    build_day_schedule,
    distribute_capacity,
    format_event_summary,
    serialize_event,
)

logger = logging.getLogger(__name__)

TOTAL_PARALLEL_CAPACITY = 115


async def get_days_data(dialog_manager: DialogManager, **kwargs):
    """Provide list of conference days."""
    try:
        config: Config = kwargs["config"]
        days_with_events = config.get_days_with_events()

        days_data = [
            {
                "day": day,
                "day_name": _format_day_label(config.start_date, day),
            }
            for day in days_with_events
        ]

        logger.info("Timetable days loaded: %s", len(days_data))
        return {"days": days_data}
    except Exception as exc:
        logger.exception("Failed to load timetable days", exc_info=exc)
        return {"days": []}


async def get_day_events_data(dialog_manager: DialogManager, **kwargs):
    """Provide schedule structure for selected day."""
    try:
        config: Config = kwargs["config"]
        db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
        event_obj = dialog_manager.event
        if event_obj and getattr(event_obj, "from_user", None):
            user_id = event_obj.from_user.id
        else:
            user_id = dialog_manager.dialog_data.get("current_user_id")
        dialog_manager.dialog_data["current_user_id"] = user_id
        selected_day = dialog_manager.dialog_data.get("selected_day", 0)

        day_events = config.get_day_events(selected_day)
        schedule_items, raw_group_map = build_day_schedule(day_events)

        serialized_events = {event.event_id: serialize_event(event) for event in day_events}
        event_map: Dict[str, Dict[str, Any]] = serialized_events
        event_to_group: Dict[str, Optional[str]] = {}
        group_capacities: Dict[str, Dict[str, int]] = {}
        group_map: Dict[str, List[Dict[str, Any]]] = {}
        user_group_registrations: Dict[str, str] = {}

        for event_id, payload in serialized_events.items():
            group_id = payload["group_id"] if payload.get("registration_required") else None
            event_to_group[event_id] = group_id

        for group_id, events in raw_group_map.items():
            group_capacities[group_id] = distribute_capacity(TOTAL_PARALLEL_CAPACITY, events)
            group_map[group_id] = [serialized_events[event.event_id] for event in events]
            if user_id is not None:
                registration = await db_manager.get_user_event_registration(user_id, group_id)
                if registration:
                    user_group_registrations[group_id] = registration.event_id

        dialog_manager.dialog_data["event_map"] = event_map
        dialog_manager.dialog_data["event_to_group"] = event_to_group
        dialog_manager.dialog_data["group_map"] = group_map
        dialog_manager.dialog_data["group_capacities"] = group_capacities
        dialog_manager.dialog_data["user_group_registrations"] = user_group_registrations

        schedule_text = _compose_schedule_text(
            config.start_date,
            selected_day,
            schedule_items,
            event_map,
            group_map,
            user_group_registrations,
        )

        events_payload = [
            {
                "id": item.item_id,
                "label": item.label,
            }
            for item in schedule_items
        ]

        logger.info("Loaded %s schedule items for day %s", len(events_payload), selected_day)
        day_key = str(selected_day)
        day_media_id: Optional[MediaAttachment] = None
        timetable_media = config.timetable_media
        if timetable_media:
            file_id = timetable_media.get(day_key)
            if file_id is None:
                fallback_key: Optional[str]
                try:
                    fallback_key = f"{int(day_key)}.png"
                except ValueError:
                    fallback_key = None

                if fallback_key == "0.png":
                    fallback_key = "1.png"

                if fallback_key:
                    file_id = timetable_media.get(fallback_key)

            if file_id is None:
                ordered_filenames = sorted(
                    name
                    for name in timetable_media.keys()
                    if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                )
                try:
                    index = int(day_key)
                except (ValueError, TypeError):
                    index = None
                if index is not None and 0 <= index < len(ordered_filenames):
                    file_id = timetable_media.get(ordered_filenames[index])

            if file_id:
                day_media_id = MediaAttachment(ContentType.PHOTO, file_id=MediaId(file_id))

        return {
            "schedule_text": schedule_text,
            "events": events_payload,
            "selected_day": selected_day,
            "day_photo": day_media_id,
        }
    except Exception as exc:
        logger.exception("Failed to load day timetable", exc_info=exc)
        return {
            "schedule_text": "Ошибка загрузки расписания",
            "events": [],
            "selected_day": 0,
        }


async def get_group_events_data(dialog_manager: DialogManager, **kwargs):
    """Provide data for parallel events group window."""
    config: Config = kwargs["config"]
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]

    group_id = dialog_manager.dialog_data.get("selected_group_id")
    if not group_id:
        return {"group_header": "Группа мероприятий не найдена", "group_events": []}

    group_map: Dict[str, List[Dict[str, Any]]] = dialog_manager.dialog_data.get("group_map", {})
    events = group_map.get(group_id)

    if not events:
        return {"group_header": "В выбранной группе нет мероприятий", "group_events": []}

    capacities = dialog_manager.dialog_data.get("group_capacities", {}).get(group_id, {})
    user_group_registrations: Dict[str, str] = dialog_manager.dialog_data.get("user_group_registrations", {})
    current_event_id = user_group_registrations.get(group_id)

    counts = await redis_manager.get_event_group_counts(group_id)
    if counts is None:
        counts = await db_manager.get_event_counts_for_group(group_id)
        await redis_manager.set_event_group_counts(group_id, counts)

    user_id = dialog_manager.dialog_data.get("current_user_id")
    if current_event_id is None and user_id is not None:
        registration = await db_manager.get_user_event_registration(user_id, group_id)
        if registration:
            current_event_id = registration.event_id
            user_group_registrations[group_id] = current_event_id
            dialog_manager.dialog_data["user_group_registrations"] = user_group_registrations

    sorted_events = sorted(events, key=lambda e: e.get("title", ""))
    events_payload = []
    availability_lines: List[str] = []
    for event in sorted_events:
        event_id = event["event_id"]
        capacity = capacities.get(event_id, 0)
        taken = counts.get(event_id, 0)
        remaining = max(0, capacity - taken)
        is_current = current_event_id == event_id
        locked = bool(current_event_id and current_event_id != event_id)
        if is_current:
            prefix = "✅ "
            info_line = f"Вы зарегистрированы · Осталось мест: {remaining}/{capacity}"
        elif locked:
            prefix = "🔒 "
            info_line = "Недоступно: отмените текущую регистрацию"
        else:
            prefix = "🔒 " if remaining <= 0 else ""
            info_line = f" | Осталось мест: {remaining}/{capacity}"

        label = f"{prefix}{event['title']}\n{info_line}"
        events_payload.append({
            "id": f"event:{event_id}",
            "label": label,
            "locked": locked,
        })
        location = event.get("location") or ""
        location_suffix = f" ({location})" if location else ""
        availability_lines.append(
            f"\n• <b>{event['title']}</b>{location_suffix}\n  Осталось мест: {remaining}/{capacity}"
        )

    primary_event = sorted_events[0]
    day_label = _format_day_label(config.start_date, dialog_manager.dialog_data.get("selected_day", 0))
    titles_block = "\n".join(availability_lines)
    group_title = primary_event.get("group_title") or "Параллельные мероприятия"
    group_header = (
        f"<b>{day_label}</b>\n"
        f"{primary_event['start_time']} – {primary_event['end_time']}\n"
        f"<b>{group_title}</b>\n\n"
        f"Доступные варианты:\n{titles_block}\n\n"
        "Выберите мероприятие и зарегистрируйтесь на подходящий вариант."
    )

    return {
        "group_header": group_header,
        "group_events": events_payload,
    }


async def get_event_detail_data(dialog_manager: DialogManager, **kwargs):
    """Provide detailed information about selected event with registration context."""
    config: Config = kwargs["config"]
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]

    event_id = dialog_manager.dialog_data.get("selected_event_id")
    if not event_id:
        return {"event_detail": "Мероприятие не выбрано"}

    event_map: Dict[str, Dict[str, Any]] = dialog_manager.dialog_data.get("event_map", {})
    event = event_map.get(event_id)

    if not event:
        # Rebuild cache if missing (possible after invalidation)
        selected_day = dialog_manager.dialog_data.get("selected_day", 0)
        day_events = config.get_day_events(selected_day)
        for item in day_events:
            event_map[item.event_id] = serialize_event(item)
        dialog_manager.dialog_data["event_map"] = event_map
        event = event_map.get(event_id)

    if not event:
        logger.warning("Event %s not found in timetable cache", event_id)
        return {"event_detail": "Мероприятие не найдено"}

    detail_lines = [
        format_event_summary(
            event["title"],
            event.get("location", ""),
            f"{event['start_time']} – {event['end_time']}",
        )
    ]
    if event.get("description"):
        detail_lines.append("")
        detail_lines.append(event["description"])

    group_id = event.get("group_id") if event.get("registration_required") else None
    register_button_text = "Зарегистрироваться"
    show_register_button = bool(event.get("registration_required"))
    show_unregister_button = False

    if event.get("registration_required") and group_id:
        capacities = dialog_manager.dialog_data.get("group_capacities", {}).get(group_id, {})
        counts = await redis_manager.get_event_group_counts(group_id)
        if counts is None:
            counts = await db_manager.get_event_counts_for_group(group_id)
            await redis_manager.set_event_group_counts(group_id, counts)

        capacity = capacities.get(event_id, 0)
        taken = counts.get(event_id, 0)
        remaining = max(0, capacity - taken)

        detail_lines.append("")
        detail_lines.append(f"Осталось мест: {remaining}/{capacity}")

        user_id = dialog_manager.event.from_user.id
        current_registration = await db_manager.get_user_event_registration(user_id, group_id)

        if current_registration and current_registration.event_id == event_id:
            show_register_button = False
            show_unregister_button = True
            detail_lines.append("")
            detail_lines.append("📝 Вы зарегистрированы на это мероприятие.")
        elif current_registration:
            show_unregister_button = True
            other_event = event_map.get(current_registration.event_id)
            if other_event:
                detail_lines.append("")
                detail_lines.append(
                    f"ℹ️ Сейчас вы записаны на: <b>{other_event['title']}</b>."
                )
            else:
                detail_lines.append("")
                detail_lines.append("ℹ️ У вас есть активная регистрация на другой вариант.")

        if remaining <= 0 and show_register_button:
            register_button_text = "🔒 Регистрация закрыта"

    event_detail = "\n".join(detail_lines)

    return {
        "event_detail": event_detail,
        "register_button_text": register_button_text,
        "show_register_button": show_register_button,
        "show_unregister_button": show_unregister_button,
    }


def _format_day_label(start_date: datetime, day_offset: int) -> str:
    target_date = start_date + timedelta(days=day_offset)
    weekday_names = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }
    weekday = weekday_names.get(target_date.weekday(), target_date.strftime("%A"))
    return target_date.strftime("%d.%m (") + weekday + ")"


def _compose_schedule_text(
    start_date: datetime,
    day: int,
    schedule_items: List[ScheduleItem],
    event_map: Dict[str, Dict[str, Any]],
    group_map: Dict[str, List[Dict[str, Any]]],
    user_group_registrations: Dict[str, str],
) -> str:
    header = f"<b>Расписание – {_format_day_label(start_date, day)}</b>\n"
    lines: List[str] = [header, ""]

    for item in schedule_items:
        if item.type == "simple":
            event_id = item.item_id.split(":", 1)[1]
            event = event_map.get(event_id)
            if not event:
                continue
            location = f" ({event.get('location', '')})" if event.get("location") else ""
            lines.append(
                f"{event['start_time']} – {event['end_time']} · <b>{event['title']}</b>{location}"
            )
        else:
            group_id = item.group_id
            events = group_map.get(group_id, [])
            if not events:
                continue
            registered_event_id = user_group_registrations.get(group_id)
            if registered_event_id and registered_event_id in event_map:
                selected_event = event_map[registered_event_id]
                location = f" ({selected_event.get('location', '')})" if selected_event.get("location") else ""
                lines.append(
                    f"{selected_event['start_time']} – {selected_event['end_time']} · <b>{selected_event['title']}</b>{location}"
                )
            else:
                titles = "\n• ".join(event.get("title", "") for event in events)
                group_title = events[0].get("group_title") or "Параллельные мероприятия"
                lines.append(
                    f"{events[0]['start_time']} – {events[0]['end_time']} · <b>{group_title}</b>:\n• {titles}"
                )
        lines.append("")

    return "\n".join(lines).strip()