import logging
from datetime import datetime
from typing import Optional

from aiogram.types import CallbackQuery, Message, User as TelegramUser
from aiogram_dialog import DialogManager

from app.infrastructure.database.database import (
    DatabaseManager,
    EventRegistrationStatus,
)
from app.infrastructure.database.redis_manager import RedisManager
from app.infrastructure.google_sheets import GoogleSheetsManager
from .states import TimetableSG
from .vr_lab import (
    VR_LAB_GROUP_ID,
    is_vr_lab_event,
    ensure_room,
)

logger = logging.getLogger(__name__)

COACH_FORM_KEY = "coach_form"


async def on_day_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str):
    """Handle day selection."""
    try:
        selected_day = int(item_id)
        dialog_manager.dialog_data["selected_day"] = selected_day
        logger.info("Timetable day selected: %s", selected_day)
        await dialog_manager.switch_to(TimetableSG.day_events)
    except Exception as exc:
        logger.exception("Failed to handle day selection", exc_info=exc)
        await callback.answer("Ошибка при выборе дня", show_alert=True)


async def on_schedule_item_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str):
    """Handle selection of either simple event or group entry."""
    try:
        if item_id.startswith("group:"):
            group_id = item_id.split(":", 1)[1]
            dialog_manager.dialog_data["selected_group_id"] = group_id
            logger.debug("Parallel group selected: %s", group_id)
            await dialog_manager.switch_to(TimetableSG.group_events)
            return

        if item_id.startswith("event:"):
            event_id = item_id.split(":", 1)[1]
            dialog_manager.dialog_data["selected_event_id"] = event_id

            event_groups = dialog_manager.dialog_data.get("event_to_group", {})
            group_id: Optional[str] = event_groups.get(event_id)
            if group_id:
                dialog_manager.dialog_data["selected_group_id"] = group_id

            event_map = dialog_manager.dialog_data.get("event_map", {})
            event_payload = event_map.get(event_id)
            if event_payload and is_vr_lab_event(event_payload):
                dialog_manager.dialog_data["selected_group_id"] = VR_LAB_GROUP_ID
                dialog_manager.dialog_data["vr_lab_event_payload"] = event_payload
                dialog_manager.dialog_data.pop("vr_lab_selected_room", None)
                await dialog_manager.switch_to(TimetableSG.vr_lab_rooms)
                return

            logger.debug("Simple event selected: %s", event_id)
            await dialog_manager.switch_to(TimetableSG.event_detail)
            return

        logger.warning("Unknown timetable item selected: %s", item_id)
        await callback.answer("Неизвестный элемент расписания", show_alert=True)
    except Exception as exc:
        logger.exception("Failed to handle schedule selection", exc_info=exc)
        await callback.answer("Ошибка при обработке расписания", show_alert=True)


async def on_group_event_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str):
    """Handle event selection inside a parallel group."""
    try:
        if not item_id.startswith("event:"):
            await callback.answer("Неверный идентификатор мероприятия", show_alert=True)
            return

        event_id = item_id.split(":", 1)[1]
        dialog_manager.dialog_data["selected_event_id"] = event_id
        logger.debug("Group event selected: %s", event_id)
        await dialog_manager.switch_to(TimetableSG.event_detail)
    except Exception as exc:
        logger.exception("Failed to handle group event selection", exc_info=exc)
        await callback.answer("Ошибка выбора мероприятия", show_alert=True)


async def on_register_event(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    """Register user for selected event if slots are available."""
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]

    user_id = callback.from_user.id
    event_id = dialog_manager.dialog_data.get("selected_event_id")
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    if not event_id or not group_id:
        await callback.answer("Не удалось определить мероприятие", show_alert=True)
        logger.error("Missing event or group id for registration")
        return

    capacities = dialog_manager.dialog_data.get("group_capacities", {}).get(group_id, {})
    capacity = capacities.get(event_id)
    if capacity is None:
        await callback.answer("Лимит мероприятия не найден", show_alert=True)
        logger.error("Capacity not found for event %s in group %s", event_id, group_id)
        return

    try:
        status = await db_manager.register_user_for_event(user_id, event_id, group_id, capacity)

        if status in {EventRegistrationStatus.SUCCESS, EventRegistrationStatus.SWITCHED}:
            counts = await db_manager.get_event_counts_for_group(group_id)
            await redis_manager.set_event_group_counts(group_id, counts)
            message = "Вы зарегистрированы на мероприятие" if status == EventRegistrationStatus.SUCCESS else "Регистрация обновлена"
            await callback.answer(message, show_alert=False)
            await dialog_manager.switch_to(TimetableSG.event_detail)
        elif status == EventRegistrationStatus.ALREADY_REGISTERED_THIS:
            await callback.answer("Вы уже зарегистрированы на это мероприятие", show_alert=False)
        elif status == EventRegistrationStatus.GROUP_FULL:
            counts = await db_manager.get_event_counts_for_group(group_id)
            await redis_manager.set_event_group_counts(group_id, counts)
            await callback.answer("Свободных мест не осталось", show_alert=True)
            await dialog_manager.switch_to(TimetableSG.event_detail)
        elif status == EventRegistrationStatus.USER_NOT_FOUND:
            await callback.answer("Не удалось найти профиль пользователя", show_alert=True)
        else:
            await callback.answer("Не удалось выполнить регистрацию", show_alert=True)
    except Exception as exc:
        logger.exception("Failed to register user for event", exc_info=exc)
        await callback.answer("Ошибка регистрации", show_alert=True)


async def on_unregister_event(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    """Cancel user registration for the selected event."""
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]

    user_id = callback.from_user.id
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    if not group_id:
        await callback.answer("Не найдено событие для отмены", show_alert=True)
        return

    try:
        success = await db_manager.unregister_user_from_event(user_id, group_id)
        if success:
            counts = await db_manager.get_event_counts_for_group(group_id)
            await redis_manager.set_event_group_counts(group_id, counts)
            await callback.answer("Регистрация отменена", show_alert=False)
            await dialog_manager.switch_to(TimetableSG.event_detail)
        else:
            await callback.answer("Вы не зарегистрированы на это мероприятие", show_alert=False)
    except Exception as exc:
        logger.exception("Failed to unregister user", exc_info=exc)
        await callback.answer("Ошибка при отмене регистрации", show_alert=True)


async def on_back_to_day_events(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    """Return from event detail back to the appropriate window."""
    selected_event_id = dialog_manager.dialog_data.get("selected_event_id")
    event_map = dialog_manager.dialog_data.get("event_map", {})
    event = event_map.get(selected_event_id)
    group_id = dialog_manager.dialog_data.get("selected_group_id")

    dialog_manager.dialog_data.pop("selected_event_id", None)

    if group_id and event and event.get("registration_required"):
        await dialog_manager.switch_to(TimetableSG.group_events)
    else:
        dialog_manager.dialog_data.pop("selected_group_id", None)
        await dialog_manager.switch_to(TimetableSG.day_events)

    await callback.answer()


async def on_vr_room_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str):
    if not item_id.startswith("room:" ):
        await callback.answer("Не удалось определить аудиторию", show_alert=True)
        return

    room = item_id.split(":", 1)[1]
    try:
        ensure_room(room)
    except ValueError:
        await callback.answer("Неизвестная аудитория", show_alert=True)
        return
    dialog_manager.dialog_data["vr_lab_selected_room"] = room
    await dialog_manager.switch_to(TimetableSG.vr_lab_slots)
    await callback.answer()


async def on_vr_slot_selected(callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str):
    if not item_id.startswith("vr_lab:"):
        await callback.answer("Не удалось определить слот", show_alert=True)
        return

    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]

    user_id = callback.from_user.id
    event_id = item_id
    status = await db_manager.register_user_for_event(user_id, event_id, VR_LAB_GROUP_ID, capacity=1)

    if status in {EventRegistrationStatus.SUCCESS, EventRegistrationStatus.SWITCHED}:
        counts = await db_manager.get_event_counts_for_group(VR_LAB_GROUP_ID)
        await redis_manager.set_event_group_counts(VR_LAB_GROUP_ID, counts)
        dialog_manager.dialog_data["vr_lab_registration_event_id"] = event_id
        message = "Вы записались на слот" if status == EventRegistrationStatus.SUCCESS else "Запись обновлена"
        await callback.answer(message, show_alert=False)
        await dialog_manager.switch_to(TimetableSG.vr_lab_slots)
        return

    if status == EventRegistrationStatus.ALREADY_REGISTERED_THIS:
        await callback.answer("Вы уже записаны на этот слот", show_alert=False)
        await dialog_manager.switch_to(TimetableSG.vr_lab_slots)
        return

    if status == EventRegistrationStatus.GROUP_FULL:
        counts = await db_manager.get_event_counts_for_group(VR_LAB_GROUP_ID)
        await redis_manager.set_event_group_counts(VR_LAB_GROUP_ID, counts)
        await callback.answer("Этот слот уже занят", show_alert=True)
        await dialog_manager.switch_to(TimetableSG.vr_lab_slots)
        return

    if status == EventRegistrationStatus.USER_NOT_FOUND:
        await callback.answer("Сначала начните диалог с ботом через /start", show_alert=True)
        return

    await callback.answer("Не удалось оформить запись", show_alert=True)


async def on_vr_lab_unregister(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]

    user_id = callback.from_user.id
    success = await db_manager.unregister_user_from_event(user_id, VR_LAB_GROUP_ID)
    if not success:
        await callback.answer("У вас нет активной записи", show_alert=False)
        return

    counts = await db_manager.get_event_counts_for_group(VR_LAB_GROUP_ID)
    await redis_manager.set_event_group_counts(VR_LAB_GROUP_ID, counts)
    dialog_manager.dialog_data.pop("vr_lab_registration_event_id", None)

    context = dialog_manager.current_context()
    target_state = context.state if context else TimetableSG.vr_lab_rooms
    if target_state == TimetableSG.vr_lab_slots:
        await dialog_manager.switch_to(TimetableSG.vr_lab_slots)
    else:
        await dialog_manager.switch_to(TimetableSG.vr_lab_rooms)

    await callback.answer("Запись отменена", show_alert=False)


async def on_vr_back_to_day(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    dialog_manager.dialog_data.pop("selected_event_id", None)
    dialog_manager.dialog_data.pop("selected_group_id", None)
    dialog_manager.dialog_data.pop("vr_lab_selected_room", None)
    dialog_manager.dialog_data.pop("vr_lab_event_payload", None)
    await dialog_manager.switch_to(TimetableSG.day_events)
    await callback.answer()


async def on_vr_back_to_rooms(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    await dialog_manager.switch_to(TimetableSG.vr_lab_rooms)
    await callback.answer()


def _coach_form(dialog_manager: DialogManager) -> dict:
    return dialog_manager.dialog_data.setdefault(COACH_FORM_KEY, {})


def _normalize_telegram_handle(username: Optional[str]) -> str:
    if not username:
        return ""

    handle = username.strip()
    if not handle:
        return ""

    return handle if handle.startswith("@") else f"@{handle}"


async def _ensure_telegram_from_context(
    dialog_manager: DialogManager,
    telegram_user: Optional[TelegramUser],
) -> str:
    form = _coach_form(dialog_manager)
    if form.get("telegram"):
        return form["telegram"]

    username = getattr(telegram_user, "username", None) if telegram_user else None
    handle = _normalize_telegram_handle(username)

    if not handle and telegram_user:
        db_manager: Optional[DatabaseManager] = dialog_manager.middleware_data.get("db_manager")
        if db_manager:
            db_user = await db_manager.get_user(telegram_user.id)
            if db_user and db_user.username:
                handle = _normalize_telegram_handle(db_user.username)

    form["telegram"] = handle or ""
    return form["telegram"]


async def on_open_coach_intro(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    dialog_manager.dialog_data.pop(COACH_FORM_KEY, None)
    dialog_manager.dialog_data["coach_user_id"] = callback.from_user.id
    await dialog_manager.switch_to(TimetableSG.coach_intro)
    await callback.answer()


async def on_coach_start_form(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    dialog_manager.dialog_data[COACH_FORM_KEY] = {}
    await _ensure_telegram_from_context(dialog_manager, callback.from_user)
    await dialog_manager.switch_to(TimetableSG.coach_full_name)
    await callback.answer()


async def on_coach_cancel(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    dialog_manager.dialog_data.pop(COACH_FORM_KEY, None)
    await dialog_manager.switch_to(TimetableSG.days_list)
    await callback.answer("Отправка отменена")


async def coach_full_name_entered(message: Message, widget, dialog_manager: DialogManager, value: str):
    text = value.strip()
    if len(text.split()) < 2:
        await message.answer("Пожалуйста, укажите ФИО полностью.")
        return

    _coach_form(dialog_manager)["full_name"] = text
    await dialog_manager.switch_to(TimetableSG.coach_age)


async def coach_age_entered(message: Message, widget, dialog_manager: DialogManager, value: str):
    text = value.strip()
    try:
        age = int(text)
    except ValueError:
        await message.answer("Возраст нужно указать цифрами.")
        return

    if age < 14 or age > 120:
        await message.answer("Укажите реальный возраст (14-120).")
        return

    _coach_form(dialog_manager)["age"] = age
    await dialog_manager.switch_to(TimetableSG.coach_university)


async def coach_university_entered(message: Message, widget, dialog_manager: DialogManager, value: str):
    text = value.strip()
    if not text:
        await message.answer("Название университета не может быть пустым.")
        return

    _coach_form(dialog_manager)["university"] = text
    await dialog_manager.switch_to(TimetableSG.coach_email)


async def coach_email_entered(message: Message, widget, dialog_manager: DialogManager, value: str):
    text = value.strip()
    if "@" not in text or "." not in text.split("@")[-1]:
        await message.answer("Похоже, email указан некорректно. Попробуйте снова.")
        return

    _coach_form(dialog_manager)["email"] = text
    await dialog_manager.switch_to(TimetableSG.coach_phone)


async def coach_phone_entered(message: Message, widget, dialog_manager: DialogManager, value: str):
    text = value.strip()
    if not text:
        await message.answer("Номер телефона не может быть пустым.")
        return

    _coach_form(dialog_manager)["phone"] = text
    await _ensure_telegram_from_context(dialog_manager, message.from_user)
    await dialog_manager.switch_to(TimetableSG.coach_request)


async def coach_request_entered(message: Message, widget, dialog_manager: DialogManager, value: str):
    text = value.strip()
    if not text:
        await message.answer("Расскажите коротко о запросе для коуч-сессии.")
        return

    _coach_form(dialog_manager)["request_text"] = text
    await dialog_manager.switch_to(TimetableSG.coach_summary)


async def on_coach_restart(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    await dialog_manager.switch_to(TimetableSG.coach_full_name)
    await callback.answer()


async def on_coach_confirm(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    await _ensure_telegram_from_context(dialog_manager, callback.from_user)
    form = dialog_manager.dialog_data.get(COACH_FORM_KEY)
    if not form:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    sheets_manager: GoogleSheetsManager = dialog_manager.middleware_data["google_sheets_manager"]

    try:
        entry = await db_manager.create_coach_session_request(
            user_id=callback.from_user.id,
            full_name=form.get("full_name", ""),
            age=form.get("age"),
            university=form.get("university", ""),
            email=form.get("email", ""),
            phone=form.get("phone", ""),
            telegram=form.get("telegram", ""),
            request_text=form.get("request_text", ""),
        )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        headers = [
            "Дата и время",
            "ФИО",
            "Возраст",
            "Университет",
            "Email",
            "Телефон",
            "Telegram",
            "Запрос",
            "Telegram ID",
            "Запись ID",
        ]
        row = [
            timestamp,
            entry.full_name,
            entry.age or "",
            entry.university,
            entry.email,
            entry.phone,
            entry.telegram,
            entry.request_text,
            str(callback.from_user.id),
            entry.id,
        ]

        success = await sheets_manager.append_coach_session_entry(headers, row)
        if not success:
            logger.warning("Coach session entry stored but failed to append to Google Sheets")

        dialog_manager.dialog_data["coach_entry_id"] = entry.id
        await dialog_manager.switch_to(TimetableSG.coach_success)
        await callback.answer("Анкета отправлена")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to submit coach session request", exc_info=exc)
        await callback.answer("Не удалось сохранить данные", show_alert=True)


async def on_coach_finish(callback: CallbackQuery, widget, dialog_manager: DialogManager):
    dialog_manager.dialog_data.pop(COACH_FORM_KEY, None)
    dialog_manager.dialog_data.pop("coach_entry_id", None)
    await dialog_manager.switch_to(TimetableSG.days_list)
    await callback.answer()