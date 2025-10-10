from aiogram_dialog import DialogManager, StartMode

from app.bot.states.main_menu import MainMenuSG


async def go_to_main_menu(callback, widget, manager: DialogManager):
    """Переход в главное меню"""
    await manager.start(MainMenuSG.main_menu, mode=StartMode.RESET_STACK)