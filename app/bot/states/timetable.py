from aiogram.fsm.state import State, StatesGroup


class TimetableSG(StatesGroup):
    days_list = State()
    day_events = State()
    event_detail = State()
