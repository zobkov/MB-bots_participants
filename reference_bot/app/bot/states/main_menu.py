from aiogram.fsm.state import State, StatesGroup


class MainMenuSG(StatesGroup):
    main_menu = State()
    current_stage_info = State()
    support = State()
