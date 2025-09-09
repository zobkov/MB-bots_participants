from aiogram_dialog.widgets.kbd import Button, Radio, Column, Next, Back, Multiselect, Row
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram.enums import ContentType

from app.bot.states.first_stage import FirstStageSG
from .getters import (
    get_stage_info, get_how_found_options, get_departments, get_departments_for_previous,
    get_positions_for_department, get_course_options, get_form_summary,
    get_edit_menu_data, get_edit_how_found_options, get_first_stage_media
)
from .handlers import (
    on_full_name_input, on_university_input, on_phone_input, on_email_input,
    on_how_found_state_changed, on_how_found_continue, on_previous_department_selected,
    on_job_selection_result, on_yes_previous_kbk, on_no_previous_kbk,
    on_experience_input, on_motivation_input, on_resume_uploaded, on_skip_resume,
    on_apply_clicked, on_submit_application, on_back_to_menu, go_to_menu,
    on_edit_full_name_input, on_edit_university_input, on_edit_phone_input, on_edit_email_input,
    on_edit_experience_input, on_edit_motivation_input, on_edit_resume_uploaded, on_skip_edit_resume,
    on_edit_department_selected, on_edit_position_selected, on_back_to_confirmation,
    on_edit_clicked, on_confirm_application, on_edit_field_clicked,
    on_edit_how_found_state_changed, on_edit_how_found_continue, on_edit_previous_department_selected
)

first_stage_dialog = Dialog(
    # Информация о первом этапе
    Window(
        DynamicMedia(
            "media"
        ),
        Format("📋 <b>{stage_name}</b>\n\n"
               "На этом этапе мы хотим поближе с тобой познакомиться. Нам интересно, чем ты увлекаешься и в каких проектах участвовал.\n\n" \
               "Не знаешь, какая позиция тебе больше подходит? Не переживай, чуть позже мы расскажем о каждом отделе и доступных вакансиях, чтобы тебе было проще сделать выбор.\n\n"
               "<b>{application_status_text}</b>"),
        Button(
            Const("📝 Подать заявку"),
            id="apply",
            on_click=on_apply_clicked,
            when="can_apply"
        ),
        Button(Const("🏠 В главное меню"), id="go_to_menu", on_click=go_to_menu),
        state=FirstStageSG.stage_info,
        getter=[get_stage_info, get_first_stage_media]
    ),

    # ФИО
    Window(
        Const("Напиши свою фамилию, имя и отчество полностью."),
        MessageInput(
            func=on_full_name_input,
            content_types=[ContentType.TEXT]
        ),
        state=FirstStageSG.full_name
    ),
    
    # Учебное заведение
    Window(
        Const("Где ты учишься? Укажи университет, факультет, курс, год выпуска.\n\nНапример: СПбГУ, ВШМ, 2 курс, 2027."),
        MessageInput(
            func=on_university_input,
            content_types=[ContentType.TEXT]
        ),
        state=FirstStageSG.university
    ),

    # Телефон
    Window(
        Const("Напиши номер телефона в формате <b>+7XXXXXXXXXX</b>, чтобы мы могли связаться с тобой."),
        MessageInput(
            func=on_phone_input,
            content_types=[ContentType.TEXT]
        ),
        state=FirstStageSG.phone
    ),
    
    # Email
    Window(
        Const("Укажи действующий e-mail. Не волнуйся, мы не отправляем спам"),
        MessageInput(
            func=on_email_input,
            content_types=[ContentType.TEXT]
        ),
        state=FirstStageSG.email
    ),
    
    # Откуда узнали о КБК (множественный выбор)
    Window(
        Const("Откуда ты узнал о КБК?\nМожно выбрать несколько вариантов:"),
        Column(
            Multiselect(
                Format("✅ {item[text]}"),  # checked_text
                Format("☐ {item[text]}"),   # unchecked_text
                id="how_found_multiselect",
                item_id_getter=lambda item: item["id"],
                items="how_found_options",
                min_selected=1,
                on_state_changed=on_how_found_state_changed
            ),
        ),
        Button(
            Const("➡️ Далее"),
            id="continue_how_found",
            on_click=on_how_found_continue, 
            when="has_selections"
        ),
        state=FirstStageSG.how_found_kbk,
        getter=get_how_found_options
    ),
    
    # Отдел предыдущего участия (если выбрано "Ранее участвовал в КБК")
    Window(
        Const("Респект, коллега! В каком отделе ты работал?"),
        Column(
            Radio(
                Format("🔘 {item[text]}"),
                Format("⚪ {item[text]}"),
                id="previous_dept_radio",
                item_id_getter=lambda item: item["id"],
                items="departments",
                on_click=on_previous_department_selected 
            ),
        ),
        state=FirstStageSG.previous_department,
        getter=get_departments_for_previous
    ),
    

    # Выбор отдела
    # в отдельном диалоге


    # Опыт
    Window(
        Const("Опиши проекты, в которых участвовал: какие задачи выполнял, каких результатов добился. Если опыта нет, расскажи о случаях, когда проявлял инициативу или брал на себя ответственность."),
        MessageInput(
            func=on_experience_input,
            content_types=[ContentType.TEXT]
        ),
        state=FirstStageSG.experience
    ),
    
    # Мотивация
    Window(
        Const("Почему ты хочешь быть в команде КБК? Чего хочешь достичь? Расскажи о мотивации честно и своими словами."),
        MessageInput(
            func=on_motivation_input,
            content_types=[ContentType.TEXT]
        ),
        state=FirstStageSG.motivation
    ),
    
    # Загрузка резюме
    Window(
        Const("Прикрепи своё актуальное резюме (PDF, DOC, DOCX, изображения или любые другие файлы). Это поможет нам больше узнать про твои навыки и опыт."
              "\n\n⚠️ Максимальный размер файла: 15 МБ"
              "\n\nТы можешь написать ссылку к своему резюме или портфолио, если тебе так удобнее."
              "\n\nТы также можешь не отправлять резюме. Но это будет минусом при рассмотрении твоей анкеты."),
        MessageInput(
            func=on_resume_uploaded,
            content_types=[ContentType.DOCUMENT, ContentType.PHOTO, ContentType.TEXT]
        ),
        Button(
            Const("⏭️ Пропустить отправку резюме"),
            id="skip_resume",
            on_click=on_skip_resume
        ),
        state=FirstStageSG.resume_upload
    ),

    # Подтверждение
    Window(
        Format("✅ <b>Проверь, что все данные заполнены верно. Если что-то нужно исправить — выбери пункт, в котором допустил ошибку, и обнови ответ.</b>\n\n"
               "👤 <b>ФИО:</b> {full_name}\n"
               "🏫 <b>Учебное заведение:</b> {university}\n"
               "📱 <b>Телефон:</b> {phone}\n"
               "📧 <b>Email:</b> {email}\n"
               "📢 <b>Откуда узнали:</b> {how_found_text}{previous_dept_text}\n"
               "💼 <b>Опыт:</b> {experience}\n"
               "💭 <b>Мотивация:</b> {motivation}\n"
               "📄 <b>Резюме:</b> {resume_status}\n"
               "\n<b>Приоритеты вакансий:</b>\n{priorities_summary}"),
        Row(
            Button(
                Const("📝 Изменить"),
                id="edit",
                on_click=on_edit_clicked
            ),
            Button(
                Const("✅ Подтвердить и отправить"),
                id="confirm",
                on_click=on_confirm_application
            )
        ),
        state=FirstStageSG.confirmation,
        getter=get_form_summary
    ),
    
    # Меню редактирования
    Window(
        Const("📝 Что ты хочешь изменить?"),
        Column(
            Button(
                Format("👤 Изменить ФИО"),
                id="edit_full_name",
                on_click=on_edit_field_clicked
            ),
            Button(
                Format("🎓 Изменить университет"),
                id="edit_university", 
                on_click=on_edit_field_clicked
            ),
            Button(
                Format("📱 Изменить телефон"),
                id="edit_phone",
                on_click=on_edit_field_clicked
            ),
            Button(
                Format("📧 Изменить email"),
                id="edit_email",
                on_click=on_edit_field_clicked
            ),
            Button(
                Format("📢 Изменить 'Откуда узнал(а) о КБК'"),
                id="edit_how_found",
                on_click=on_edit_field_clicked
            ),
            Button(
                Format("💼 Изменить опыт"),
                id="edit_experience",
                on_click=on_edit_field_clicked
            ),
            Button(
                Format("💭 Изменить мотивацию"),
                id="edit_motivation",
                on_click=on_edit_field_clicked
            ),
            Button(
                Format("📄 Изменить резюме"),
                id="edit_resume",
                on_click=on_edit_field_clicked
            ),
            Button(
                Format("Изменить выбор вакансий"),
                id="edit_department",
                on_click=on_edit_field_clicked
            )
        ),
        Button(
            Const("⬅️ Назад к подтверждению"),
            id="back_to_confirmation",
            on_click=on_back_to_confirmation
        ),
        state=FirstStageSG.edit_menu,
        getter=get_edit_menu_data
    ),
    
    # Окна редактирования отдельных полей
    Window(
        Const("Напиши свои фамилию, имя и отчество полностью:"),
        TextInput(
            id="edit_full_name_input",
            on_success=on_edit_full_name_input
        ),
        Button(
            Const("⬅️ Назад к меню"),
            id="back_to_edit_menu",
            on_click=on_back_to_confirmation
        ),
        state=FirstStageSG.edit_full_name
    ),
    
    Window(
        Const("Где ты учишься? Укажи факультет, университет, курс, год выпуска.\n\nнапример: СПбГУ, ВШМ, 2 курс, 2027"),
        TextInput(
            id="edit_university_input",
            on_success=on_edit_university_input
        ),
        Button(
            Const("⬅️ Назад к меню"),
            id="back_to_edit_menu",
            on_click=on_back_to_confirmation
        ),
        state=FirstStageSG.edit_university
    ),
    
    Window(
        Const("Напиши номер телефона в формате <b>+7XXXXXXXXXX</b>, чтобы мы могли связаться с тобой"),
        TextInput(
            id="edit_phone_input",
            on_success=on_edit_phone_input
        ),
        Button(
            Const("⬅️ Назад к меню"),
            id="back_to_edit_menu",
            on_click=on_back_to_confirmation
        ),
        state=FirstStageSG.edit_phone
    ),
    
    Window(
        Const("Укажи действующий e-mail. Не волнуйся, мы не отправляем спам"),
        TextInput(
            id="edit_email_input",
            on_success=on_edit_email_input
        ),
        Button(
            Const("⬅️ Назад к меню"),
            id="back_to_edit_menu",
            on_click=on_back_to_confirmation
        ),
        state=FirstStageSG.edit_email
    ),
    
    Window(
        Const("Откуда ты узнал о КБК? Можно выбрать несколько вариантов"),
        Column(
            Multiselect(
                Format("✅ {item[text]}"),
                Format("☐ {item[text]}"),
                id="edit_how_found_multi",
                item_id_getter=lambda item: item["id"],
                items="how_found_options",
                on_state_changed=on_edit_how_found_state_changed
            ),
        ),
        Button(
            Const("Продолжить ➡️"),
            id="edit_how_found_continue",
            on_click=on_edit_how_found_continue
        ),
        Button(
            Const("⬅️ Назад к меню"),
            id="back_to_edit_menu",
            on_click=on_back_to_confirmation
        ),
        getter=get_edit_how_found_options,
        state=FirstStageSG.edit_how_found_kbk
    ),
    
    Window(
        Const("Респект, коллега! В каком отделе ты работал?"),
        Column(
            Radio(
                Format("🔘 {item[text]}"),
                Format("⚪ {item[text]}"),
                id="edit_previous_dept_radio",
                item_id_getter=lambda item: item["id"],
                items="departments",
                on_click=on_edit_previous_department_selected
            )
        ),
        Button(
            Const("⬅️ Назад к меню"),
            id="back_to_edit_menu",
            on_click=on_back_to_confirmation
        ),
        getter=get_departments_for_previous,
        state=FirstStageSG.edit_previous_department
    ),
    
    Window(
        Const("Опиши проекты, в которых участвовал: какие задачи выполнял, чего достиг. Если нет опыта — расскажи, где проявлял инициативу и брал ответственность на себя."),
        TextInput(
            id="edit_experience_input",
            on_success=on_edit_experience_input
        ),
        Button(
            Const("⬅️ Назад к меню"),
            id="back_to_edit_menu",
            on_click=on_back_to_confirmation
        ),
        state=FirstStageSG.edit_experience
    ),
    
    Window(
        Const("Почему ты хочешь быть в команде КБК? Чего хочешь достичь? Расскажи о мотивации честно и своими словами."),
        TextInput(
            id="edit_motivation_input",
            on_success=on_edit_motivation_input
        ),
        Button(
            Const("⬅️ Назад к меню"),
            id="back_to_edit_menu",
            on_click=on_back_to_confirmation
        ),
        state=FirstStageSG.edit_motivation
    ),
    
    Window(
        Const("📄 Загрузите новое резюме (PDF, DOC, DOCX, изображения или любые другие файлы, размер до 15 МБ):"
              "\n\nТы можешь написать ссылку к своему резюме или портфолио, если тебе так удобнее."
              "\n\nТы также можешь не отправлять резюме. Но это будет минусом при рассмотрении твоей анкеты."),
        MessageInput(
            content_types=[ContentType.DOCUMENT, ContentType.PHOTO, ContentType.TEXT],
            func=on_edit_resume_uploaded
        ),
        Button(
            Const("⏭️ Пропустить отправку резюме"),
            id="skip_edit_resume",
            on_click=on_skip_edit_resume
        ),
        Button(
            Const("⬅️ Назад к меню"),
            id="back_to_edit_menu",
            on_click=on_back_to_confirmation
        ),
        state=FirstStageSG.edit_resume_upload
    ),
    
    # Успешная отправка
    Window(
        Const("🎉 <b>Готово!</b>\n\n"
              "Твоя заявка отправлена. Мы свяжемся с тобой в ближайшее время.\n\n"
              "Следи за статусом заявки в личном кабинете и за анонсами в нашем телеграм-канале."),
        Button(Const("🏠 В главное меню"), id="go_to_menu", on_click=go_to_menu),
        state=FirstStageSG.success
    ),
    on_process_result=on_job_selection_result
)
