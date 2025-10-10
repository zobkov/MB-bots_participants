from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel, Button, Row, Back
from aiogram_dialog.widgets.text import Const, Format

from .states import RegistrationSG
from .handlers import on_case_selected, on_confirm_registration, on_cancel_registration, on_unregister_request, on_confirm_unregister, on_cancel_unregister
from .getters import get_debate_registration_data, get_confirmation_data, get_unregister_confirmation_data


registration_dialog = Dialog(
    Window(
        Format("<b>Запись на дебаты</b>\n\n{cases_text}\n\n{user_status}"),
        Row(
            Button(
                Format("{vtb_button_text}"),
                id="case_1",
                on_click=on_case_selected,
            ),
            Button(
                Format("{alabuga_button_text}"),
                id="case_2", 
                on_click=on_case_selected,
            ),
            Button(
                Format("{b1_button_text}"),
                id="case_3",
                on_click=on_case_selected,
            ),
        ),
        Row(
            Button(
                Format("{severstal_button_text}"),
                id="case_4",
                on_click=on_case_selected,
            ),
            Button(
                Format("{alpha_button_text}"),
                id="case_5",
                on_click=on_case_selected,
            ),
        ),
        Button(
            Const("❌ Отменить регистрацию"),
            id="unregister",
            on_click=on_unregister_request,
            when="is_registered"
        ),
        Cancel(Const("Назад"), id="registration_back"),
        state=RegistrationSG.main,
        getter=get_debate_registration_data,
    ),
    Window(
        Format("<b>Подтверждение регистрации</b>\n\nВы хотите зарегистрироваться на кейс <b>{case_name}</b>?"),
        Row(
            Button(
                Const("✅ Подтвердить"),
                id="confirm",
                on_click=on_confirm_registration,
            ),
            Button(
                Const("❌ Отмена"),
                id="cancel",
                on_click=on_cancel_registration,
            ),
        ),
        state=RegistrationSG.confirm,
        getter=get_confirmation_data,
    ),
    Window(
        Format("<b>⚠️ Отмена регистрации</b>\n\nВы уверены, что хотите отменить регистрацию на кейс <b>{current_case_name}</b>?\n\n<i>Внимание: места на данный кейс могут быстро закончиться, и повторная регистрация может оказаться невозможной!</i>"),
        Row(
            Button(
                Const("✅ Да, отменить"),
                id="confirm_unregister",
                on_click=on_confirm_unregister,
            ),
            Button(
                Const("❌ Нет, оставить"),
                id="cancel_unregister",
                on_click=on_cancel_unregister,
            ),
        ),
        state=RegistrationSG.cancel_confirm,
        getter=get_unregister_confirmation_data,
    ),
)