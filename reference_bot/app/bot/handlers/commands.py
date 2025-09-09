from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command, CommandStart, StateFilter

from aiogram_dialog import DialogManager, StartMode

from app.bot.states.start import StartSG
from app.bot.states.main_menu import MainMenuSG
from app.bot.states.first_stage import FirstStageSG
from app.bot.states.job_selection import JobSelectionSG

from app.bot.assets.media_groups.media_groups import build_start_media_group

router = Router()


@router.message(CommandStart())
async def process_command_start(message: Message, dialog_manager: DialogManager):
    media_group = build_start_media_group()
    await message.bot.send_media_group(chat_id=message.chat.id, media=media_group)
    await dialog_manager.start(state=StartSG.start, mode=StartMode.RESET_STACK)

@router.message(Command(commands=['menu']))
async def process_command_menu(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(state=MainMenuSG.main_menu, mode=StartMode.RESET_STACK)

@router.message(Command(commands=['test']))
async def process_command_test(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(state=JobSelectionSG.select_department, mode=StartMode.RESET_STACK)