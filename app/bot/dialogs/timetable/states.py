from aiogram.fsm.state import State, StatesGroup


class TimetableSG(StatesGroup):
    days_list = State()
    day_events = State()
    group_events = State()
    event_detail = State()
    vr_lab_rooms = State()
    vr_lab_slots = State()
    coach_intro = State()
    coach_full_name = State()
    coach_age = State()
    coach_university = State()
    coach_email = State()
    coach_phone = State()
    coach_request = State()
    coach_summary = State()
    coach_success = State()