from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.text import Const

from .states import StartSG
from .handlers import go_to_main_menu


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
