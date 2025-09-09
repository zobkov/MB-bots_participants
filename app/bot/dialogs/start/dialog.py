from aiogram_dialog import Dialog, Window, DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Const

from app.bot.states.start import StartSG
from app.bot.states.main_menu import MainMenuSG


async def go_to_main_menu(callback, widget, manager: DialogManager):
    """Переход в главное меню"""
    await manager.start(MainMenuSG.main_menu, mode=StartMode.RESET_STACK)


start_dialog = Dialog(
    Window(
        Const(
            "Привет! Добро пожаловать на конференцию Менеджмент Будущего 2025! "
            "Поздравляем с попаданием в топ-100"
        ),
        Button(
            Const("В главное меню"),
            id="to_main_menu",
            on_click=go_to_main_menu
        ),
        state=StartSG.welcome,
    ),
)
