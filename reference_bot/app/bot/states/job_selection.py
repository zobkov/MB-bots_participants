from aiogram.fsm.state import State, StatesGroup


class JobSelectionSG(StatesGroup):
    # Выбор первого приоритета
    select_department = State()
    select_subdepartment = State()  # Новое состояние для выбора под-отдела
    select_position = State()
    
    # Выбор второго приоритета
    select_department_2 = State()
    select_subdepartment_2 = State()  # Новое состояние для выбора под-отдела
    select_position_2 = State()
    
    # Выбор третьего приоритета
    select_department_3 = State()
    select_subdepartment_3 = State()  # Новое состояние для выбора под-отдела
    select_position_3 = State()
    
    # Обзор всех приоритетов
    priorities_overview = State()
    
    # Редактирование первого приоритета
    edit_priority_1 = State()
    edit_priority_1_subdepartment = State()  # Новое состояние
    edit_priority_1_position = State()
    
    # Редактирование второго приоритета
    edit_priority_2 = State()
    edit_priority_2_subdepartment = State()  # Новое состояние
    edit_priority_2_position = State()
    
    # Редактирование третьего приоритета
    edit_priority_3 = State()
    edit_priority_3_subdepartment = State()  # Новое состояние
    edit_priority_3_position = State()
    
    # Обмен приоритетов
    swap_priorities_menu = State()
    
    # Завершение выбора
    complete_selection = State()
