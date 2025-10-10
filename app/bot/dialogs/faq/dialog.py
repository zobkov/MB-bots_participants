from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.text import Const

from .states import FaqSG


faq_dialog = Dialog(
    Window(
        Const("Часто задаваемые вопросы\n\nРаздел находится в разработке."),
        Cancel(Const("Назад"), id="faq_back"),
        state=FaqSG.main,
    ),
)