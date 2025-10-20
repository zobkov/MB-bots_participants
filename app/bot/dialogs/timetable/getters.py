import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram.enums import ContentType

from app.infrastructure.database import DatabaseManager, RedisManager
from config.config import Config
from .vr_lab import (
    VR_LAB_GROUP_ID,
    VR_LAB_ROOMS,
    VR_LAB_SLOT_TIMES,
    TOTAL_SLOTS_PER_ROOM,
    build_slot_event_id,
    count_room_taken_slots,
    is_vr_lab_event,
    parse_slot_event_id,
    ensure_room,
)
from .utils import (
    ScheduleItem,
    build_day_schedule,
    distribute_capacity,
    format_event_summary,
    serialize_event,
)

logger = logging.getLogger(__name__)

TOTAL_PARALLEL_CAPACITY = 115
COACH_FORM_KEY = "coach_form"
COACH_EXISTING_NOTE = (
    "\n✅ <b>Мы получили твою запись!</b> Время твоей сессии будет назначено после завершения конференции. "
    "Не пропусти сообщение!\n\nТы также можешь еще раз заполнить анкету если хочешь поменять что-то."
)


async def get_coach_intro_data(dialog_manager: DialogManager, **kwargs):
    base_text = (
        "<b>Коучинговые сессии-профилирование со специалистами из международной лаборатории лидерства "
        "LeaderMakers</b>\n\n"
        "На сессии вы сможете разобрать свой запрос, получить персональный отчет о ваших сильных сторонах "
        "и создать четкий план для раскрытия лидерского потенциала."
    )

    try:
        db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
        user_id = dialog_manager.dialog_data.get("coach_user_id")
        if user_id is not None:
            existing_entry = await db_manager.get_last_coach_session_request(user_id)
        else:
            existing_entry = None
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to prepare coach intro data", exc_info=exc)
        existing_entry = None

    if existing_entry:
        return {"coach_intro_text": f"{base_text}\n\n{COACH_EXISTING_NOTE}"}

    return {"coach_intro_text": base_text}


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

        vr_lab_booking: Optional[Tuple[str, str]] = None
        if user_id is not None:
            vr_registration = await db_manager.get_user_event_registration(user_id, VR_LAB_GROUP_ID)
            if vr_registration:
                parsed_slot = parse_slot_event_id(vr_registration.event_id)
                if parsed_slot:
                    vr_lab_booking = parsed_slot

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
            vr_lab_booking,
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


async def get_vr_lab_rooms_data(dialog_manager: DialogManager, **kwargs):
    config: Config = kwargs["config"]
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]

    event_payload = dialog_manager.dialog_data.get("vr_lab_event_payload")
    if not event_payload:
        selected_event_id = dialog_manager.dialog_data.get("selected_event_id")
        fallback_event = dialog_manager.dialog_data.get("event_map", {}).get(selected_event_id or "")
        if fallback_event and is_vr_lab_event(fallback_event):
            event_payload = fallback_event
        else:
            return {
                "vr_lab_header": "VR-lab не найдена",
                "vr_rooms": [],
                "show_unregister_button": False,
            }

    user_id = dialog_manager.dialog_data.get("current_user_id")
    counts = await redis_manager.get_event_group_counts(VR_LAB_GROUP_ID)
    if counts is None:
        counts = await db_manager.get_event_counts_for_group(VR_LAB_GROUP_ID)
        await redis_manager.set_event_group_counts(VR_LAB_GROUP_ID, counts)

    registration_event_id = dialog_manager.dialog_data.get("vr_lab_registration_event_id")
    registration_room = None
    registration_slot = None

    if user_id is not None:
        registration = await db_manager.get_user_event_registration(user_id, VR_LAB_GROUP_ID)
        if registration:
            registration_event_id = registration.event_id

    if registration_event_id:
        parsed = parse_slot_event_id(registration_event_id)
        if parsed:
            registration_room, registration_slot = parsed
            dialog_manager.dialog_data["vr_lab_registration_event_id"] = registration_event_id

    if registration_room and not dialog_manager.dialog_data.get("vr_lab_selected_room"):
        dialog_manager.dialog_data["vr_lab_selected_room"] = registration_room

    rooms_payload: List[Dict[str, Any]] = []
    availability_lines: List[str] = []
    for room in VR_LAB_ROOMS:
        taken = count_room_taken_slots(room, counts)
        remaining = max(0, TOTAL_SLOTS_PER_ROOM - taken)
        prefix = ""
        if room == registration_room:
            prefix = "✅ "
            status_line = f" | Твой слот · Свободно: {remaining}/{TOTAL_SLOTS_PER_ROOM}"
        elif remaining == 0:
            prefix = "🔒 "
            status_line = f" | Свободных слотов нет"
        else:
            status_line = f" | Свободно: {remaining}/{TOTAL_SLOTS_PER_ROOM}"

        rooms_payload.append(
            {
                "id": f"room:{room}",
                "label": f"{prefix}Ауд. {room}\n{status_line}",
            }
        )
        availability_lines.append(
            f"• Ауд. {room}: {remaining}/{TOTAL_SLOTS_PER_ROOM} свободно"
        )

    day_label = _format_day_label(config.start_date, dialog_manager.dialog_data.get("selected_day", 0))

    header_lines = [
        f"<b>{day_label}</b>",
        f"{event_payload['start_time']} – {event_payload['end_time']} · <b>{event_payload['title']}</b>",
    ]
    if event_payload.get("location"):
        header_lines.append(f"{event_payload['location']}")

    header_lines.append("")
    header_lines.append("Выбери аудиторию VR-lab. В каждой аудитории слоты по 15 минут на одного участника.")
    header_lines.append("")
    header_lines.append("<b>Доступность:</b>")
    header_lines.extend(availability_lines)

    if registration_room and registration_slot:
        header_lines.append("")
        header_lines.append(
            f"📝 Вы записаны: ауд. {registration_room}, {registration_slot}"
        )

    return {
        "vr_lab_header": "\n".join(header_lines),
        "vr_rooms": rooms_payload,
        "show_unregister_button": bool(registration_event_id),
    }


async def get_vr_lab_slots_data(dialog_manager: DialogManager, **kwargs):
    config: Config = kwargs["config"]
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]

    event_payload = dialog_manager.dialog_data.get("vr_lab_event_payload")
    if not event_payload:
        selected_event_id = dialog_manager.dialog_data.get("selected_event_id")
        fallback_event = dialog_manager.dialog_data.get("event_map", {}).get(selected_event_id or "")
        if fallback_event and is_vr_lab_event(fallback_event):
            event_payload = fallback_event
        else:
            return {
                "vr_lab_slots_header": "VR-lab не найдена",
                "vr_slots": [],
                "show_unregister_button": False,
            }

    user_id = dialog_manager.dialog_data.get("current_user_id")
    counts = await redis_manager.get_event_group_counts(VR_LAB_GROUP_ID)
    if counts is None:
        counts = await db_manager.get_event_counts_for_group(VR_LAB_GROUP_ID)
        await redis_manager.set_event_group_counts(VR_LAB_GROUP_ID, counts)

    registration_event_id = dialog_manager.dialog_data.get("vr_lab_registration_event_id")
    registration_room = None
    registration_slot = None

    if user_id is not None:
        registration = await db_manager.get_user_event_registration(user_id, VR_LAB_GROUP_ID)
        if registration:
            registration_event_id = registration.event_id

    if registration_event_id:
        parsed = parse_slot_event_id(registration_event_id)
        if parsed:
            registration_room, registration_slot = parsed
            dialog_manager.dialog_data["vr_lab_registration_event_id"] = registration_event_id

    selected_room = dialog_manager.dialog_data.get("vr_lab_selected_room")
    if not selected_room:
        if registration_room:
            selected_room = registration_room
        else:
            selected_room = VR_LAB_ROOMS[0]
        dialog_manager.dialog_data["vr_lab_selected_room"] = selected_room

    try:
        ensure_room(selected_room)
    except ValueError:
        selected_room = VR_LAB_ROOMS[0]
        dialog_manager.dialog_data["vr_lab_selected_room"] = selected_room

    slots_payload: List[Dict[str, Any]] = []
    for slot_time in VR_LAB_SLOT_TIMES:
        event_id = build_slot_event_id(selected_room, slot_time)
        taken = counts.get(event_id, 0)
        remaining = max(0, 1 - taken)
        is_current = registration_event_id == event_id
        locked = taken >= 1 and not is_current

        if is_current:
            prefix = "✅ "
            status_line = " Вы записаны"
        elif locked:
            prefix = "🔒 "
            status_line = " Слот занят"
        else:
            prefix = ""
            status_line = " Свободно"

        slots_payload.append(
            {
                "id": event_id,
                "label": f"{prefix}{slot_time}\n{status_line}",
            }
        )

    day_label = _format_day_label(config.start_date, dialog_manager.dialog_data.get("selected_day", 0))
    room_line = f"Аудитория {selected_room}"

    header_lines = [
        f"<b>{day_label}</b>",
        f"{event_payload['title']}",
        room_line,
        "",
        "Выбери подходящий слот (15 минут). Каждый слот доступен только одному участнику.",
    ]

    if registration_room and registration_slot:
        header_lines.append("")
        header_lines.append(
            f"📝 Текущая запись: ауд. {registration_room}, {registration_slot}"
        )

    return {
        "vr_lab_slots_header": "\n".join(header_lines),
        "vr_slots": slots_payload,
        "show_unregister_button": bool(registration_event_id),
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

    sorted_events = sorted(events, key=lambda e: e.get("short_title") or e.get("title", ""))
    events_payload = []
    availability_lines: List[str] = []
    for event in sorted_events:
        event_id = event["event_id"]
        capacity = capacities.get(event_id, 0)
        taken = counts.get(event_id, 0)
        remaining = max(0, capacity - taken)
        is_current = current_event_id == event_id
        locked = bool(current_event_id and current_event_id != event_id)
        display_name = event.get("short_title") or event.get("title", "")
        full_title = event.get("title", "")

        if is_current:
            prefix = "✅ "
            info_line = f"Вы зарегистрированы · Осталось мест: {remaining}/{capacity}"
        elif locked:
            prefix = "🔒 "
            info_line = "Недоступно: отмените текущую регистрацию"
        else:
            prefix = "🔒 " if remaining <= 0 else ""
            info_line = f" | Осталось мест: {remaining}/{capacity}"

        label = f"{prefix}{display_name}\n{info_line}"
        events_payload.append({
            "id": f"event:{event_id}",
            "label": label,
            "locked": locked,
        })
        location = event.get("location") or ""
        location_suffix = f" ({location})" if location else ""
        availability_lines.append(
            f"\n• <b>{full_title}</b>{location_suffix}\n  Осталось мест: {remaining}/{capacity}"
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
        "Выбери мероприятие и зарегистрируйся на подходящий вариант."
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
    vr_lab_booking: Optional[Tuple[str, str]],
) -> str:
    header = f"<b>Расписание – {_format_day_label(start_date, day)}</b>\n"
    lines: List[str] = [header, ""]

    for item in schedule_items:
        if item.type == "simple":
            event_id = item.item_id.split(":", 1)[1]
            event = event_map.get(event_id)
            if not event:
                continue
            if is_vr_lab_event(event):
                if vr_lab_booking:
                    room, slot = vr_lab_booking
                    location = f" <i>— Твой слот: ауд. {room}, {slot}</i>"
                elif event.get("location"):
                    location = f" ({event.get('location', '')})"
                else:
                    location = ""
            else:
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


async def get_coach_summary_data(dialog_manager: DialogManager, **kwargs):
    form: Dict[str, Any] = dialog_manager.dialog_data.get(COACH_FORM_KEY, {})

    telegram_value = (form.get("telegram") or "").strip()
    if telegram_value:
        telegram_line = f"<b>Telegram:</b> {telegram_value}"
    else:
        telegram_line = "<b>Telegram:</b> — (не найдено в телеграм-профиле)"

    summary_lines = [
        "<b>Проверь данные анкеты:</b>",
        "",
        f"<b>ФИО:</b> {form.get('full_name', '—')}",
        f"<b>Возраст:</b> {form.get('age', '—')}",
        f"<b>Университет:</b> {form.get('university', '—')}",
        f"<b>Email:</b> {form.get('email', '—')}",
        f"<b>Телефон:</b> {form.get('phone', '—')}",
        telegram_line,
        "",
        "<b>Запрос на коуч-сессию:</b>",
        form.get("request_text", "—"),
    ]

    return {"coach_summary": "\n".join(summary_lines)}