from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.text import Const

from .states import NavigationSG


navigation_dialog = Dialog(
    Window(
        Const("Навигация по площадке\n\nРаздел находится в разработке."),
        Cancel(Const("Назад"), id="navigation_back"),
        state=NavigationSG.main,
    ),
)