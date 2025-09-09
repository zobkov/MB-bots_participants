from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.text import Const

from app.bot.states.other import NavigationSG, FaqSG, RegistrationSG


navigation_dialog = Dialog(
    Window(
        Const("Навигация по площадке\n\nРаздел находится в разработке."),
        Cancel(Const("Назад"), id="navigation_back"),
        state=NavigationSG.main,
    ),
)


faq_dialog = Dialog(
    Window(
        Const("Часто задаваемые вопросы\n\nРаздел находится в разработке."),
        Cancel(Const("Назад"), id="faq_back"),
        state=FaqSG.main,
    ),
)


registration_dialog = Dialog(
    Window(
        Const("Регистрация на сессии\n\nРаздел находится в разработке."),
        Cancel(Const("Назад"), id="registration_back"),
        state=RegistrationSG.main,
    ),
)
