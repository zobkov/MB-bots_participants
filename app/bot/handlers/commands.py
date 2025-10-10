from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
import logging

from app.bot.states.start import StartSG

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start_command(message: Message, dialog_manager: DialogManager):
    """Обработчик команды /start"""
    await dialog_manager.start(StartSG.welcome, mode=StartMode.RESET_STACK)


@router.message(Command("menu"))
async def menu_command(message: Message, dialog_manager: DialogManager):
    """Обработчик команды /menu"""
    from app.bot.states.main_menu import MainMenuSG
    await dialog_manager.start(MainMenuSG.main_menu, mode=StartMode.RESET_STACK)


@router.message(Command("help"))
async def help_command(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "🤖 <b>Бот конференции Менеджмент Будущего 2025</b>\n\n"
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/menu - Главное меню\n"
        "/help - Показать это сообщение\n\n"
        "Функции бота:\n"
        "📅 Расписание мероприятий\n"
        "📝 Регистрация на сессии\n"
        "🗺 Навигация по площадке\n"
        "❓ Часто задаваемые вопросы\n"
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
