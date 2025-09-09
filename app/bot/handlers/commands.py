from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from app.bot.states.start import StartSG

router = Router()


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
