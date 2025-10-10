from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel, Button, Row, Back
from aiogram_dialog.widgets.text import Const, Format

from .states import RegistrationSG
from .handlers import on_case_selected, on_confirm_registration, on_cancel_registration
from .getters import get_debate_registration_data, get_confirmation_data


registration_dialog = Dialog(
    Window(
        Format("<b>Запись на дебаты</b>\n\n{cases_text}"),
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
)