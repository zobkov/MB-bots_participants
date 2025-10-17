"""Handlers for registration dialog"""

import logging
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from app.infrastructure.database import DatabaseManager, RedisManager
from .states import RegistrationSG
from .utils import GENERIC_REGISTRATION_ERROR_MESSAGE

logger = logging.getLogger(__name__)


async def on_case_selected(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Handler for case selection button"""
    # Извлекаем номер кейса из ID кнопки (case_1 -> 1)
    case_num = int(button.widget_id.split('_')[1])
    
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    
    user_id = callback.from_user.id
    
    # Check if there are available slots first - if not, ignore the action
    if not await redis_manager.can_register_for_case(case_num):
        # Silently ignore the action for locked cases
        await callback.answer()
        return
    
    # Check if user is already registered
    existing_registration = await db_manager.check_user_already_registered(user_id)
    if existing_registration:
        if existing_registration == case_num:
            await callback.answer(
                f"Вы уже зарегистрированы на этот кейс!",
                show_alert=True
            )
        else:
            old_case_name = await redis_manager.get_case_name(existing_registration)
            new_case_name = await redis_manager.get_case_name(case_num)
            await callback.answer(
                f"Вы уже зарегистрированы на кейс {old_case_name}. Сначала отмените текущую регистрацию, чтобы записаться на {new_case_name}.",
                show_alert=True
            )
        return
    
    # Store selected case and move to confirmation
    dialog_manager.dialog_data["selected_case"] = case_num
    await dialog_manager.switch_to(RegistrationSG.confirm)


async def on_confirm_registration(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Handler for registration confirmation"""
    case_number = dialog_manager.dialog_data.get("selected_case")
    if not case_number:
        await callback.answer("Ошибка: кейс не выбран", show_alert=True)
        return
    
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    
    user_id = callback.from_user.id
    
    # Double-check availability to prevent race conditions
    if not await redis_manager.can_register_for_case(case_number):
        await callback.answer(
            "К сожалению, места на этот кейс закончились!",
            show_alert=True
        )
        await dialog_manager.switch_to(RegistrationSG.main)
        return
    
    # Check if user is already registered (double check)
    existing_registration = await db_manager.check_user_already_registered(user_id)
    if existing_registration:
        await callback.answer(
            f"Вы уже зарегистрированы на кейс {await redis_manager.get_case_name(existing_registration)}!",
            show_alert=True
        )
        await dialog_manager.switch_to(RegistrationSG.main)
        return
    
    try:
        # Update database
        success = await db_manager.update_user_debate_registration(user_id, case_number)
        if not success:
            await callback.answer(GENERIC_REGISTRATION_ERROR_MESSAGE, show_alert=True)
            return
        
        # Update Redis cache
        await redis_manager.increment_debate_count(case_number)
        
        case_name = await redis_manager.get_case_name(case_number)
        await callback.answer(
            f"Вы успешно зарегистрированы на кейс {case_name}!",
            show_alert=True
        )
        
        logger.info(f"User {user_id} registered for debate case {case_number} ({case_name})")
        
        # Уведомляем админов о новой регистрации
        try:
            from config.config import load_config
            config = load_config()
            
            if config.logging.admin_ids:
                bot = dialog_manager.middleware_data.get("bot")
                if bot:
                    user_info = callback.from_user
                    username = f"@{user_info.username}" if user_info.username else "—"
                    visible_name = f"{user_info.first_name} {user_info.last_name}".strip() or f"User {user_id}"
                    
                    admin_message = (
                        f"📝 <b>Новая регистрация на дебаты</b>\n\n"
                        f"<b>Пользователь:</b> {visible_name} ({username})\n"
                        f"<b>ID:</b> {user_id}\n"
                        f"<b>Кейс:</b> {case_name}\n"
                        f"<b>Время:</b> {callback.message.date.strftime('%H:%M:%S')}"
                    )
                    
                    for admin_id in config.logging.admin_ids:
                        try:
                            await bot.send_message(admin_id, admin_message, parse_mode="HTML")
                        except Exception:
                            pass  # Игнорируем ошибки отправки админам
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
        
        # Return to main registration screen
        await dialog_manager.switch_to(RegistrationSG.main)
        
    except Exception as e:
        logger.error(f"Error registering user {user_id} for case {case_number}: {e}")
        await callback.answer(GENERIC_REGISTRATION_ERROR_MESSAGE, show_alert=True)


async def on_cancel_registration(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Handler for registration cancellation"""
    await dialog_manager.switch_to(RegistrationSG.main)


async def on_unregister_request(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Handler for unregister request button"""
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    
    user_id = callback.from_user.id
    
    # Check if user is actually registered
    existing_registration = await db_manager.check_user_already_registered(user_id)
    if not existing_registration:
        await callback.answer("Вы не зарегистрированы на дебаты", show_alert=True)
        return
    
    # Move to unregister confirmation
    await dialog_manager.switch_to(RegistrationSG.cancel_confirm)


async def on_confirm_unregister(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Handler for confirming unregistration"""
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    redis_manager: RedisManager = dialog_manager.middleware_data["redis_manager"]
    
    user_id = callback.from_user.id
    
    try:
        # Check current registration
        existing_registration = await db_manager.check_user_already_registered(user_id)
        if not existing_registration:
            await callback.answer("Вы не зарегистрированы на дебаты", show_alert=True)
            await dialog_manager.switch_to(RegistrationSG.main)
            return
        
        old_case_name = await redis_manager.get_case_name(existing_registration)
        
        # Remove registration from database
        success = await db_manager.update_user_debate_registration(user_id, None)
        if not success:
            await callback.answer(GENERIC_REGISTRATION_ERROR_MESSAGE, show_alert=True)
            return
        
        # Sync Redis cache with database
        db_counts = await db_manager.get_debate_registrations_count()
        await redis_manager.sync_with_database(db_counts)
        
        await callback.answer(
            f"Регистрация на кейс {old_case_name} отменена",
            show_alert=True
        )
        
        logger.info(f"User {user_id} unregistered from debate case {existing_registration} ({old_case_name})")
        
        # Notify admins about unregistration
        try:
            from config.config import load_config
            config = load_config()
            
            if config.logging.admin_ids:
                bot = dialog_manager.middleware_data.get("bot")
                if bot:
                    user_info = callback.from_user
                    username = f"@{user_info.username}" if user_info.username else "—"
                    visible_name = f"{user_info.first_name} {user_info.last_name}".strip() or f"User {user_id}"
                    
                    admin_message = (
                        f"❌ <b>Отмена регистрации на дебаты</b>\n\n"
                        f"<b>Пользователь:</b> {visible_name} ({username})\n"
                        f"<b>ID:</b> {user_id}\n"
                        f"<b>Отменен кейс:</b> {old_case_name}\n"
                        f"<b>Время:</b> {callback.message.date.strftime('%H:%M:%S')}"
                    )
                    
                    for admin_id in config.logging.admin_ids:
                        try:
                            await bot.send_message(admin_id, admin_message, parse_mode="HTML")
                        except Exception:
                            pass  # Игнорируем ошибки отправки админам
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
        
        # Return to main registration screen
        await dialog_manager.switch_to(RegistrationSG.main)
        
    except Exception as e:
        logger.error(f"Error unregistering user {user_id}: {e}")
        await callback.answer(GENERIC_REGISTRATION_ERROR_MESSAGE, show_alert=True)


async def on_cancel_unregister(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    """Handler for cancelling unregistration (keeping registration)"""
    await dialog_manager.switch_to(RegistrationSG.main)