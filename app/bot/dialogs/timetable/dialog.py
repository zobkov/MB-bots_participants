from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Column, Back, Select, Group, Cancel
from aiogram_dialog.widgets.text import Const, Format

from .states import TimetableSG
from .handlers import on_day_selected, on_event_selected
from .getters import get_days_data, get_day_events_data, get_event_detail_data


timetable_dialog = Dialog(
    # Окно со списком дней
    Window(
        Const("Расписание конференции"),
        Group(
            Select(
                Format("{item[day_name]}"),
                id="day_select",
                items="days",
                item_id_getter=lambda item: item["day"],
                on_click=on_day_selected
            ),
            width=1
        ),
        Cancel(Const("⬅️ Назад"),id="timetable_to_menu"),
        state=TimetableSG.days_list,
        getter=get_days_data,
    ),
    
    # Окно с событиями выбранного дня
    Window(
        Format("{schedule_text}"),
        Group(
            Select(
                Format("{item[title]}"),
                id="event_select",
                items="events",
                item_id_getter=lambda item: item["id"],
                on_click=on_event_selected
            ),
            width=1
        ),
        Back(Const("⬅️ Назад"), id="back_to_days"),
        state=TimetableSG.day_events,
        getter=get_day_events_data,
    ),
    
    # Окно с детальной информацией о событии
    Window(
        Format("{event_detail}"),
        Back(Const("⬅️ Назад"), id="back_to_events"),
        state=TimetableSG.event_detail,
        getter=get_event_detail_data,
        parse_mode="HTML"
    ),
)
