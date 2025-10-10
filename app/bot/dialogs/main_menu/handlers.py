from aiogram_dialog import DialogManager

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