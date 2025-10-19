from aiogram_dialog import Dialog, Window, LaunchMode
from aiogram_dialog.widgets.kbd import Button, Column
from aiogram_dialog.widgets.text import Const

from .states import MainMenuSG
from .handlers import go_to_timetable, go_to_registration, go_to_navigation, go_to_faq


main_menu_dialog = Dialog(
    Window(
        Const("<b>Менеджмент Будущего 2025</b>\n<i>Главное меню участника конференции</i>\n\nДоступна запись на <b>дебаты</b>"),
        Column(
            Button(
                Const("Расписание и регистрация"),
                id="timetable",
                on_click=go_to_timetable
            ),
            Button(
                Const("🔒 Регистрация на дебаты"),
                id="registration",
                on_click=go_to_registration
            ),
            Button(
                Const("🔒 Навигация"),
                id="navigation",
                on_click=go_to_navigation
            ),
            Button(
                Const("🔒 FAQ"),
                id="faq",
                on_click=go_to_faq
            ),
        ),
        state=MainMenuSG.main_menu,
    ),
    launch_mode=LaunchMode.SINGLE_TOP,
)
