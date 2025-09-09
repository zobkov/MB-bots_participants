from aiogram.fsm.state import State, StatesGroup


class NavigationSG(StatesGroup):
    main = State()


class FaqSG(StatesGroup):
    main = State()


class RegistrationSG(StatesGroup):
    main = State()
