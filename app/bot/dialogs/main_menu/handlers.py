from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager

from app.bot.states.timetable import TimetableSG
from app.bot.states.other import NavigationSG, FaqSG, RegistrationSG


async def go_to_timetable(callback: CallbackQuery, widget, manager: DialogManager):
    """Переход в расписание"""
    await manager.start(TimetableSG.days_list)
    callback.answer("Расписание пока закрыто", show_alert=False)


async def go_to_registration(callback: CallbackQuery, widget, manager: DialogManager):
    """Переход в регистрацию на сессии"""
    #await manager.start(RegistrationSG.main)


async def go_to_navigation(callback: CallbackQuery, widget, manager: DialogManager):
    """Переход в навигацию"""
    #await manager.start(NavigationSG.main)
    callback.answer("Навигация пока закрыта", show_alert=True)


async def go_to_faq(callback: CallbackQuery, widget, manager: DialogManager):
    """Переход в FAQ"""
    #await manager.start(FaqSG.main)
    callback.answer("FAQ пока закрыт", show_alert=True)