from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.text import Const

from .states import RegistrationSG


registration_dialog = Dialog(
    Window(
        Const("Регистрация на сессии\n\nРаздел находится в разработке."),
        Cancel(Const("Назад"), id="registration_back"),
        state=RegistrationSG.main,
    ),
)