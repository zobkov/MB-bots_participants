from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Back, Select, Group, Cancel
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.media import DynamicMedia

from .states import TimetableSG
from .handlers import (
    on_day_selected,
    on_schedule_item_selected,
    on_group_event_selected,
    on_register_event,
    on_unregister_event,
    on_back_to_day_events,
    on_vr_room_selected,
    on_vr_slot_selected,
    on_vr_lab_unregister,
    on_vr_back_to_day,
    on_vr_back_to_rooms,
)
from .getters import (
    get_days_data,
    get_day_events_data,
    get_group_events_data,
    get_event_detail_data,
    get_vr_lab_rooms_data,
    get_vr_lab_slots_data,
)


timetable_dialog = Dialog(
    # Окно со списком дней
    Window(
        Const("Расписание конференции\n\n<b>ВНИМАНИЕ</b> \nНеобходимо зарегестрироваться на мероприятия, которые отмечены как параллельные"),
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
    DynamicMedia("day_photo"),
    Format("{schedule_text}"),
        Group(
            Select(
                Format("{item[label]}"),
                id="schedule_select",
                items="events",
                item_id_getter=lambda item: item["id"],
                on_click=on_schedule_item_selected,
            ),
            width=1
        ),
        Back(Const("⬅️ Назад"), id="back_to_days"),
        state=TimetableSG.day_events,
        getter=get_day_events_data,
    ),

    # Окно с параллельными событиями
    Window(
        Format("{group_header}"),
        Group(
            Select(
                Format("{item[label]}"),
                id="group_event_select",
                items="group_events",
                item_id_getter=lambda item: item["id"],
                on_click=on_group_event_selected,
            ),
            width=1,
        ),
        Back(Const("⬅️ Назад"), id="back_to_day_events"),
        state=TimetableSG.group_events,
        getter=get_group_events_data,
    ),

    Window(
        Format("{vr_lab_header}"),
        Group(
            Select(
                Format("{item[label]}"),
                id="vr_room_select",
                items="vr_rooms",
                item_id_getter=lambda item: item["id"],
                on_click=on_vr_room_selected,
            ),
            width=2,
        ),
        Group(
            Button(
                Const("Отменить запись"),
                id="vr_lab_unregister_rooms",
                on_click=on_vr_lab_unregister,
                when="show_unregister_button",
            ),
        ),
        Button(
            Const("⬅️ Назад"),
            id="vr_lab_back_to_day",
            on_click=on_vr_back_to_day,
        ),
        state=TimetableSG.vr_lab_rooms,
        getter=get_vr_lab_rooms_data,
        parse_mode="HTML",
    ),

    Window(
        Format("{vr_lab_slots_header}"),
        Group(
            Select(
                Format("{item[label]}"),
                id="vr_slot_select",
                items="vr_slots",
                item_id_getter=lambda item: item["id"],
                on_click=on_vr_slot_selected,
            ),
            width=2,
        ),
        Group(
            Button(
                Const("Отменить запись"),
                id="vr_lab_unregister_slots",
                on_click=on_vr_lab_unregister,
                when="show_unregister_button",
            ),
        ),
        Button(
            Const("⬅️ К аудиториям"),
            id="vr_lab_back_to_rooms",
            on_click=on_vr_back_to_rooms,
        ),
        state=TimetableSG.vr_lab_slots,
        getter=get_vr_lab_slots_data,
        parse_mode="HTML",
    ),
    
    # Окно с детальной информацией о событии
    Window(
        Format("{event_detail}"),
        Group(
            Button(
                Format("{register_button_text}"),
                id="register_event",
                on_click=on_register_event,
                when="show_register_button",
            ),
            Button(
                Const("Отменить регистрацию"),
                id="unregister_event",
                on_click=on_unregister_event,
                when="show_unregister_button",
            ),
        ),
        Button(
            Const("⬅️ Назад"),
            id="back_to_day",
            on_click=on_back_to_day_events,
        ),
        state=TimetableSG.event_detail,
        getter=get_event_detail_data,
        parse_mode="HTML"
    ),
)
