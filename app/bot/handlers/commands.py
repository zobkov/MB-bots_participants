from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
import logging

from app.bot.states.start import StartSG

router = Router()
logger = logging.getLogger(__name__)


from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
import logging

from app.bot.states.start import StartSG
from app.infrastructure.database import DatabaseManager

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start_command(message: Message, dialog_manager: DialogManager):
    """Обработчик команды /start"""
    # Получаем менеджер базы данных из middleware
    db_manager: DatabaseManager = dialog_manager.middleware_data["db_manager"]
    
    user = message.from_user
    user_id = user.id
    username = user.username
    
    # Определяем видимое имя пользователя
    if user.first_name and user.last_name:
        visible_name = f"{user.first_name} {user.last_name}"
    elif user.first_name:
        visible_name = user.first_name
    elif user.last_name:
        visible_name = user.last_name
    elif username:
        visible_name = f"@{username}"
    else:
        visible_name = f"User {user_id}"
    
    # Проверяем, существует ли пользователь в базе
    existing_user = await db_manager.get_user(user_id)
    
    if not existing_user:
        # Создаем нового пользователя
        await db_manager.create_user(user_id, username, visible_name)
        logger.info(f"Created new user: {user_id} ({visible_name})")
    else:
        logger.info(f"Existing user started bot: {user_id} ({visible_name})")
    
    #await dialog_manager.start(StartSG.welcome, mode=StartMode.RESET_STACK)
    from app.bot.states.main_menu import MainMenuSG
    await dialog_manager.start(MainMenuSG.main_menu, mode=StartMode.RESET_STACK)


@router.message(Command("menu"))
async def menu_command(message: Message, dialog_manager: DialogManager):
    """Обработчик команды /menu"""
    from app.bot.states.main_menu import MainMenuSG
    await dialog_manager.start(MainMenuSG.main_menu, mode=StartMode.RESET_STACK)


@router.message(Command("help"))
async def help_command(message: Message):
    """Обработчик команды /help"""
    from config.config import load_config
    config = load_config()
    
    is_admin = message.from_user.id in config.logging.admin_ids
    
    help_text = (
        "🤖 <b>Бот конференции Менеджмент Будущего 2025</b>\n\n"
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/menu - Главное меню\n"
        "/help - Показать это сообщение\n\n"
        "Функции бота:\n"
        "📅 Расписание мероприятий\n"
        "📝 Регистрация на дебаты\n"
        "🗺 Навигация по площадке\n"
        "❓ Часто задаваемые вопросы\n"
    )
    
    if is_admin:
        help_text += (
            "\n<b>🔧 Административные команды:</b>\n"
            "/debate_stats - Статистика регистрации на дебаты\n"
            "/detailed_stats - Детальная статистика с именами\n"
            "/user_info <user_id> - Информация о пользователе\n"
            "/reset_user_registration <user_id> - Сбросить регистрацию пользователя\n"
            "/sync_debate_cache - Синхронизировать кеш с БД\n"
            "/sync_debates_google - Синхронизировать данные с Google Таблицами\n\n"
            "<b>🧪 Команды для тестирования:</b>\n"
            "/test_error - Тестовая ошибка\n"
            "/test_warning - Тестовые предупреждения\n"
            "/test_critical - Тестовая критическая ошибка\n"
            "/test_exception - Тестовое исключение\n"
        )
    
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("test_error"))
async def test_error_command(message: Message):
    """Команда для тестирования ERROR уведомлений админам"""
    # Проверяем права доступа (только для админов)
    from config.config import load_config
    config = load_config()
    
    if message.from_user.id not in config.logging.admin_ids:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    logger.error(f"Тестовая ошибка от админа {message.from_user.id}")
    await message.answer("✅ ERROR уведомление отправлено")


@router.message(Command("test_warning"))
async def test_warning_command(message: Message):
    """Команда для тестирования WARNING уведомлений админам"""
    # Проверяем права доступа (только для админов)
    from config.config import load_config
    config = load_config()
    
    if message.from_user.id not in config.logging.admin_ids:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    # Генерируем 6 WARNING для тестирования порога
    for i in range(6):
        logger.warning(f"Тестовое предупреждение #{i+1} от админа {message.from_user.id}")
    
    await message.answer("✅ 6 WARNING отправлено (должно вызвать уведомление)")


@router.message(Command("test_critical"))
async def test_critical_command(message: Message):
    """Команда для тестирования CRITICAL уведомлений админам"""
    # Проверяем права доступа (только для админов)
    from config.config import load_config
    config = load_config()
    
    if message.from_user.id not in config.logging.admin_ids:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    logger.critical(f"Тестовая критическая ошибка от админа {message.from_user.id}")
    await message.answer("✅ CRITICAL уведомление отправлено")


@router.message(Command("test_exception"))
async def test_exception_command(message: Message):
    """Команда для тестирования обработки исключений"""
    # Проверяем права доступа (только для админов)
    from config.config import load_config
    config = load_config()
    
    if message.from_user.id not in config.logging.admin_ids:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    await message.answer("🧪 Генерирую исключение для тестирования...")
    # Это исключение будет поймано middleware и отправлено админам
    raise RuntimeError(f"Тестовое исключение от админа {message.from_user.id}")


@router.message(Command("debate_stats"))
async def debate_stats_command(message: Message, dialog_manager: DialogManager):
    """Команда для просмотра статистики регистрации на дебаты"""
    # Проверяем права доступа (только для админов)
    from config.config import load_config
    config = load_config()
    
    if message.from_user.id not in config.logging.admin_ids:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    # Получаем менеджеры из middleware
    db_manager = dialog_manager.middleware_data["db_manager"]
    redis_manager = dialog_manager.middleware_data["redis_manager"]
    
    try:
        # Получаем статистику
        db_counts = await db_manager.get_debate_registrations_count()
        remaining = await redis_manager.get_remaining_slots()
        
        # Формируем ответ
        stats_text = "<b>📊 Статистика регистрации на дебаты</b>\n\n"
        
        case_names = {
            1: "ВТБ",
            2: "Алабуга", 
            3: "Б1",
            4: "Северсталь",
            5: "Альфа"
        }
        
        for case_num in range(1, 6):
            name = case_names[case_num]
            registered = db_counts[case_num]
            remaining_count = remaining[case_num]
            
            stats_text += f"<b>{name}:</b> {registered} зарегистрировано, {remaining_count} свободно\n"
        
        # Общие лимиты
        stats_text += "\n<b>Общие лимиты:</b>\n"
        stats_text += f"ВТБ: {db_counts[1]}/32\n"
        stats_text += f"Алабуга + Б1: {db_counts[2] + db_counts[3]}/41\n"
        stats_text += f"Северсталь + Альфа: {db_counts[4] + db_counts[5]}/42\n"
        
        # Общая статистика
        total_registered = sum(db_counts.values())
        stats_text += f"\n<b>Всего зарегистрировано:</b> {total_registered}"
        
        await message.answer(stats_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error getting debate stats: {e}")
        await message.answer("❌ Ошибка при получении статистики")


@router.message(Command("reset_user_registration"))
async def reset_user_registration_command(message: Message, dialog_manager: DialogManager):
    """Команда для сброса регистрации конкретного пользователя"""
    # Проверяем права доступа (только для админов)
    from config.config import load_config
    config = load_config()
    
    if message.from_user.id not in config.logging.admin_ids:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    # Получаем user_id из команды
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer(
            "Использование: /reset_user_registration <user_id>\n"
            "Пример: /reset_user_registration 123456789"
        )
        return
    
    try:
        target_user_id = int(command_parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат user_id")
        return
    
    # Получаем менеджеры из middleware
    db_manager = dialog_manager.middleware_data["db_manager"]
    redis_manager = dialog_manager.middleware_data["redis_manager"]
    
    try:
        # Проверяем, есть ли пользователь и его регистрация
        user = await db_manager.get_user(target_user_id)
        if not user:
            await message.answer(f"❌ Пользователь {target_user_id} не найден")
            return
        
        if not user.debate_reg:
            await message.answer(f"ℹ️ Пользователь {target_user_id} не зарегистрирован на дебаты")
            return
        
        old_case = user.debate_reg
        case_name = await redis_manager.get_case_name(old_case)
        
        # Сбрасываем регистрацию в БД
        await db_manager.update_user_debate_registration(target_user_id, None)
        
        # Синхронизируем Redis с БД
        db_counts = await db_manager.get_debate_registrations_count()
        await redis_manager.sync_with_database(db_counts)
        
        await message.answer(
            f"✅ Регистрация пользователя {target_user_id} на кейс {case_name} сброшена",
            parse_mode="HTML"
        )
        
        logger.info(f"Admin {message.from_user.id} reset registration for user {target_user_id} from case {old_case}")
        
    except Exception as e:
        logger.error(f"Error resetting user registration: {e}")
        await message.answer("❌ Ошибка при сбросе регистрации")


@router.message(Command("sync_debate_cache"))
async def sync_debate_cache_command(message: Message, dialog_manager: DialogManager):
    """Команда для принудительной синхронизации Redis кеша с БД"""
    # Проверяем права доступа (только для админов)
    from config.config import load_config
    config = load_config()
    
    if message.from_user.id not in config.logging.admin_ids:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    # Получаем менеджеры из middleware
    db_manager = dialog_manager.middleware_data["db_manager"]
    redis_manager = dialog_manager.middleware_data["redis_manager"]
    
    try:
        # Синхронизируем Redis с БД
        db_counts = await db_manager.get_debate_registrations_count()
        await redis_manager.sync_with_database(db_counts)
        
        await message.answer(
            f"✅ Кеш синхронизирован с базой данных\n"
            f"Текущие данные: {db_counts}",
            parse_mode="HTML"
        )
        
        logger.info(f"Admin {message.from_user.id} manually synced debate cache")
        
    except Exception as e:
        logger.error(f"Error syncing debate cache: {e}")
        await message.answer("❌ Ошибка при синхронизации кеша")


@router.message(Command("detailed_stats"))
async def detailed_stats_command(message: Message, dialog_manager: DialogManager):
    """Команда для получения детальной статистики"""
    # Проверяем права доступа (только для админов)
    from config.config import load_config
    config = load_config()
    
    if message.from_user.id not in config.logging.admin_ids:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    # Получаем менеджеры из middleware
    db_manager = dialog_manager.middleware_data["db_manager"]
    redis_manager = dialog_manager.middleware_data["redis_manager"]
    
    try:
        # Получаем общую статистику
        total_users = await db_manager.get_total_users_count()
        registered_users = await db_manager.get_registered_users_count()
        db_counts = await db_manager.get_debate_registrations_count()
        
        # Формируем детальный ответ
        stats_text = "<b>📊 ДЕТАЛЬНАЯ СТАТИСТИКА</b>\n\n"
        
        # Общие цифры
        stats_text += f"<b>👥 Общие данные:</b>\n"
        stats_text += f"Всего пользователей: {total_users}\n"
        stats_text += f"Зарегистрированных на дебаты: {registered_users}\n"
        stats_text += f"Не зарегистрированных: {total_users - registered_users}\n\n"
        
        # По кейсам
        case_names = {
            1: "ВТБ",
            2: "Алабуга", 
            3: "Б1",
            4: "Северсталь",
            5: "Альфа"
        }
        
        stats_text += "<b>🎯 Регистрация по кейсам:</b>\n"
        for case_num in range(1, 6):
            name = case_names[case_num]
            count = db_counts[case_num]
            
            # Получаем список пользователей для этого кейса
            users_in_case = await db_manager.get_users_by_debate_case(case_num)
            
            stats_text += f"<b>{name}:</b> {count} чел.\n"
            
            if users_in_case:
                # Показываем первых 3 пользователей
                user_list = []
                for i, user in enumerate(users_in_case[:3]):
                    display_name = user.visible_name or f"User {user.id}"
                    user_list.append(f"  • {display_name}")
                
                stats_text += "\n".join(user_list)
                
                if len(users_in_case) > 3:
                    stats_text += f"\n  • ... и еще {len(users_in_case) - 3}"
                
                stats_text += "\n"
            
            stats_text += "\n"
        
        # Лимиты
        stats_text += "<b>📊 Использование лимитов:</b>\n"
        vtb_used = (db_counts[1] / 32) * 100
        alabuga_b1_used = ((db_counts[2] + db_counts[3]) / 41) * 100
        severstal_alpha_used = ((db_counts[4] + db_counts[5]) / 42) * 100
        
        stats_text += f"ВТБ: {db_counts[1]}/32 ({vtb_used:.1f}%)\n"
        stats_text += f"Алабуга+Б1: {db_counts[2] + db_counts[3]}/41 ({alabuga_b1_used:.1f}%)\n"
        stats_text += f"Северсталь+Альфа: {db_counts[4] + db_counts[5]}/42 ({severstal_alpha_used:.1f}%)\n"
        
        await message.answer(stats_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error getting detailed stats: {e}")
        await message.answer("❌ Ошибка при получении детальной статистики")


@router.message(Command("user_info"))
async def user_info_command(message: Message, dialog_manager: DialogManager):
    """Команда для получения информации о конкретном пользователе"""
    # Проверяем права доступа (только для админов)
    from config.config import load_config
    config = load_config()
    
    if message.from_user.id not in config.logging.admin_ids:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    # Получаем user_id из команды
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer(
            "Использование: /user_info <user_id>\n"
            "Пример: /user_info 123456789"
        )
        return
    
    try:
        target_user_id = int(command_parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат user_id")
        return
    
    # Получаем менеджеры из middleware
    db_manager = dialog_manager.middleware_data["db_manager"]
    redis_manager = dialog_manager.middleware_data["redis_manager"]
    
    try:
        # Получаем информацию о пользователе
        user = await db_manager.get_user(target_user_id)
        if not user:
            await message.answer(f"❌ Пользователь {target_user_id} не найден в базе данных")
            return
        
        # Формируем ответ
        info_text = f"<b>👤 Информация о пользователе</b>\n\n"
        info_text += f"<b>ID:</b> {user.id}\n"
        info_text += f"<b>Username:</b> @{user.username}\n" if user.username else "<b>Username:</b> —\n"
        info_text += f"<b>Visible Name:</b> {user.visible_name}\n"
        
        if user.debate_reg:
            case_name = await redis_manager.get_case_name(user.debate_reg)
            info_text += f"<b>Регистрация на дебаты:</b> Кейс {user.debate_reg} ({case_name})\n"
        else:
            info_text += f"<b>Регистрация на дебаты:</b> Не зарегистрирован\n"
        
        await message.answer(info_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        await message.answer("❌ Ошибка при получении информации о пользователе")


@router.message(Command("sync_debates_google"))
async def sync_debates_google_command(message: Message, dialog_manager: DialogManager):
    """Команда для синхронизации данных с Google Таблицами"""
    # Проверяем права доступа (только для админов)
    from config.config import load_config
    config = load_config()

    additional_admins = [1497469650,860487502,474503734]
    
    if message.from_user.id not in config.logging.admin_ids and message.from_user.id not in additional_admins:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    # Получаем менеджеры из middleware
    db_manager = dialog_manager.middleware_data["db_manager"]
    redis_manager = dialog_manager.middleware_data["redis_manager"]
    google_sheets_manager = dialog_manager.middleware_data["google_sheets_manager"]
    
    # Отправляем уведомление о начале синхронизации
    status_message = await message.answer("🔄 Начинаю синхронизацию с Google Таблицами...")
    
    try:
        # Получаем данные пользователей
        users_data = await db_manager.get_all_users_for_export()
        db_counts = await db_manager.get_debate_registrations_count()
        
        # Синхронизируем с Google Sheets
        success = await google_sheets_manager.sync_debate_data(users_data, db_counts)
        
        if success:
            # Обновляем сообщение о статусе
            success_text = (
                "✅ <b>Синхронизация завершена успешно!</b>\n\n"
                f"📊 Экспортировано пользователей: {len(users_data)}\n"
                f"📝 Лист MAIN обновлен\n\n"
                f"📋 Таблица содержит данные о регистрации всех пользователей"
            )
            
            await status_message.edit_text(success_text, parse_mode="HTML")
        else:
            await status_message.edit_text(
                "❌ <b>Ошибка синхронизации</b>\n\n"
                "Проверьте:\n"
                "• Файл google_credentials.json\n"
                "• ID таблицы в .env\n"
                "• Права доступа к таблице\n\n"
                "Подробности в логах бота.",
                parse_mode="HTML"
            )
        
        logger.info(f"Admin {message.from_user.id} requested Google Sheets sync, result: {success}")
        
    except Exception as e:
        logger.error(f"Error during Google Sheets sync: {e}")
        await status_message.edit_text(
            "❌ <b>Критическая ошибка синхронизации</b>\n\n"
            f"Подробности в логах: {str(e)[:100]}...",
            parse_mode="HTML"
        )
