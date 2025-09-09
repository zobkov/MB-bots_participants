from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager

from app.bot.states.first_stage import FirstStageSG
from app.bot.states.main_menu import MainMenuSG


async def on_current_stage_clicked(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Обработчик нажатия на кнопку 'Текущий этап отбора'"""
    # Переходим к диалогу с информацией о текущем этапе
    await dialog_manager.start(state=FirstStageSG.stage_info)


async def on_support_clicked(callback: CallbackQuery, button, dialog_manager: DialogManager):
    """Обработчик нажатия на кнопку 'Поддержка'"""
    # Переходим к окну поддержки
    await dialog_manager.switch_to(state=MainMenuSG.support)
