import logging
from typing import Optional

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager

from app.infrastructure.database.database import (
    DatabaseManager,
    EventRegistrationStatus,
)
from app.infrastructure.database.redis_manager import RedisManager
from .states import TimetableSG

logger = logging.getLogger(__name__)


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