from aiogram.fsm.state import State, StatesGroup


class FirstStageSG(StatesGroup):
    # Информация о первом этапе
    stage_info = State()
    
    # Форма анкеты
    full_name = State()
    university = State()
    course = State()
    phone = State()
    email = State()
    how_found_kbk = State()
    previous_department = State()  # Новое состояние для отдела предыдущего участия в КБК
    experience = State()
    motivation = State()
    resume_upload = State()
    
    # Подтверждение
    confirmation = State()
    
    # Меню редактирования
    edit_menu = State()
    edit_full_name = State()
    edit_university = State()
    edit_course = State()
    edit_phone = State()
    edit_email = State()
    edit_how_found_kbk = State()
    edit_previous_department = State()
    edit_experience = State()
    edit_motivation = State()
    edit_resume_upload = State()
    
    success = State()
