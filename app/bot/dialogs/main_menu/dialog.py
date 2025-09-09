from aiogram_dialog import Dialog, Window, DialogManager, StartMode, LaunchMode
from aiogram_dialog.widgets.kbd import Button, Column
from aiogram_dialog.widgets.text import Const

from app.bot.states.main_menu import MainMenuSG
from app.bot.states.timetable import TimetableSG
from app.bot.states.other import NavigationSG, FaqSG, RegistrationSG


async def go_to_timetable(callback, widget, manager: DialogManager):
    """Переход в расписание"""
    await manager.start(TimetableSG.days_list)


async def go_to_registration(callback, widget, manager: DialogManager):
    """Переход в регистрацию на сессии"""
    await manager.start(RegistrationSG.main)


async def go_to_navigation(callback, widget, manager: DialogManager):
    """Переход в навигацию"""
    await manager.start(NavigationSG.main)


async def go_to_faq(callback, widget, manager: DialogManager):
    """Переход в FAQ"""
    await manager.start(FaqSG.main)


main_menu_dialog = Dialog(
    Window(
        Const("Главное меню"),
        Column(
            Button(
                Const("Расписание"),
                id="timetable",
                on_click=go_to_timetable
            ),
            Button(
                Const("Регистрация на сессии"),
                id="registration",
                on_click=go_to_registration
            ),
            Button(
                Const("Навигация"),
                id="navigation",
                on_click=go_to_navigation
            ),
            Button(
                Const("FAQ"),
                id="faq",
                on_click=go_to_faq
            ),
        ),
        state=MainMenuSG.main_menu,
    ),
    launch_mode=LaunchMode.SINGLE_TOP,
)
