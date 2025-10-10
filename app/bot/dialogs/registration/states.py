from aiogram.fsm.state import State, StatesGroup


class RegistrationSG(StatesGroup):
    main = State()
    confirm = State()
    cancel_confirm = State()