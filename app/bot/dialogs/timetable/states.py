from aiogram.fsm.state import State, StatesGroup


class TimetableSG(StatesGroup):
    days_list = State()
    day_events = State()
    group_events = State()
    event_detail = State()
    vr_lab_rooms = State()
    vr_lab_slots = State()