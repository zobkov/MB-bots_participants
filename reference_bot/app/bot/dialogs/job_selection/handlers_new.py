from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button

from app.bot.states.job_selection import JobSelectionSG
from app.bot.states.first_stage import FirstStageSG


async def on_department_selected(
    callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str
):
    """Обработчик выбора департамента"""
    # Определяем текущий этап выбора
    current_state = dialog_manager.current_context().state.state
    
    print(f"DEBUG: on_department_selected called")
    print(f"DEBUG: current_state = {current_state}")
    print(f"DEBUG: item_id = {item_id}")
    
    if current_state == JobSelectionSG.select_department.state:
        # Первый приоритет
        dialog_manager.dialog_data["selected_department"] = item_id
        dialog_manager.dialog_data["priority_1_department"] = item_id
        print(f"DEBUG: saved priority_1_department = {item_id}")
        await dialog_manager.next()
    elif current_state == JobSelectionSG.select_department_2.state:
        # Второй приоритет
        dialog_manager.dialog_data["selected_department"] = item_id
        dialog_manager.dialog_data["priority_2_department"] = item_id
        print(f"DEBUG: saved priority_2_department = {item_id}")
        await dialog_manager.next()
    elif current_state == JobSelectionSG.select_department_3.state:
        # Третий приоритет
        dialog_manager.dialog_data["selected_department"] = item_id
        dialog_manager.dialog_data["priority_3_department"] = item_id
        print(f"DEBUG: saved priority_3_department = {item_id}")
        await dialog_manager.next()


async def on_position_selected(
    callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str
):
    """Обработчик выбора позиции"""
    current_state = dialog_manager.current_context().state.state
    
    print(f"DEBUG: on_position_selected called")
    print(f"DEBUG: current_state = {current_state}")
    print(f"DEBUG: item_id = {item_id}")
    print(f"DEBUG: before save - dialog_data = {dialog_manager.dialog_data}")
    
    if current_state == JobSelectionSG.select_position.state:
        # Первый приоритет
        dialog_manager.dialog_data["priority_1_position"] = item_id
        print(f"DEBUG: saved priority_1_position = {item_id}")
        print(f"DEBUG: after save - dialog_data = {dialog_manager.dialog_data}")
        # Переходим к обзору приоритетов - пользователь может продолжить или подтвердить
        await dialog_manager.switch_to(JobSelectionSG.priorities_overview)
    elif current_state == JobSelectionSG.select_position_2.state:
        # Второй приоритет
        dialog_manager.dialog_data["priority_2_position"] = item_id
        print(f"DEBUG: saved priority_2_position = {item_id}")
        # Переходим к выбору третьего приоритета
        await dialog_manager.switch_to(JobSelectionSG.select_department_3)
    elif current_state == JobSelectionSG.select_position_3.state:
        # Третий приоритет
        dialog_manager.dialog_data["priority_3_position"] = item_id
        print(f"DEBUG: saved priority_3_position = {item_id}")
        # Переходим к обзору приоритетов
        await dialog_manager.switch_to(JobSelectionSG.priorities_overview)


async def on_priority_confirmed(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик подтверждения выбора приоритетов"""
    print(f"DEBUG: on_priority_confirmed called")
    print(f"DEBUG: dialog_data before processing = {dialog_manager.dialog_data}")
    
    # Сохраняем данные приоритетов в основные данные заявки
    priority_data = {}
    
    for i in range(1, 4):
        dept_key = dialog_manager.dialog_data.get(f"priority_{i}_department")
        pos_index = dialog_manager.dialog_data.get(f"priority_{i}_position")
        
        print(f"DEBUG: priority_{i}_department = {dept_key}")
        print(f"DEBUG: priority_{i}_position = {pos_index}")
        
        if dept_key and pos_index is not None:
            priority_data[f"priority_{i}_department"] = dept_key
            priority_data[f"priority_{i}_position"] = pos_index
    
    print(f"DEBUG: priority_data to save = {priority_data}")
    
    # Сохраняем приоритеты в основном dialog_data
    dialog_manager.dialog_data.update(priority_data)
    
    print(f"DEBUG: dialog_data after update = {dialog_manager.dialog_data}")
    
    # Возвращаемся к подтверждению заявки первого этапа
    await dialog_manager.start(FirstStageSG.confirmation, mode=StartMode.NORMAL)


async def on_edit_priority_1(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик редактирования первого приоритета"""
    dialog_manager.dialog_data["editing_priority"] = 1
    await dialog_manager.switch_to(JobSelectionSG.edit_priority_1)


async def on_edit_priority_2(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик редактирования второго приоритета"""
    dialog_manager.dialog_data["editing_priority"] = 2
    await dialog_manager.switch_to(JobSelectionSG.edit_priority_2)


async def on_edit_priority_3(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик редактирования третьего приоритета"""
    dialog_manager.dialog_data["editing_priority"] = 3
    await dialog_manager.switch_to(JobSelectionSG.edit_priority_3)


async def on_edit_department_selected(
    callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str
):
    """Обработчик выбора департамента при редактировании"""
    dialog_manager.dialog_data["edit_selected_department"] = item_id
    
    # Определяем какой приоритет редактируется
    editing_priority = dialog_manager.dialog_data.get("editing_priority", 1)
    
    if editing_priority == 1:
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_1_position)
    elif editing_priority == 2:
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_2_position)
    elif editing_priority == 3:
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_3_position)


async def on_edit_position_selected(
    callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str
):
    """Обработчик выбора позиции при редактировании"""
    editing_priority = dialog_manager.dialog_data.get("editing_priority", 1)
    edit_dept = dialog_manager.dialog_data.get("edit_selected_department")
    
    # Сохраняем изменения
    dialog_manager.dialog_data[f"priority_{editing_priority}_department"] = edit_dept
    dialog_manager.dialog_data[f"priority_{editing_priority}_position"] = item_id
    
    # Очищаем временные данные редактирования
    dialog_manager.dialog_data.pop("editing_priority", None)
    dialog_manager.dialog_data.pop("edit_selected_department", None)
    
    # Возвращаемся к обзору приоритетов
    await dialog_manager.switch_to(JobSelectionSG.priorities_overview)


async def on_save_edited_priority(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик сохранения отредактированного приоритета"""
    # Этот обработчик может не понадобиться, так как сохранение происходит в on_edit_position_selected
    await dialog_manager.switch_to(JobSelectionSG.priorities_overview)


async def on_swap_priorities(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик смены приоритетов местами"""
    # Создаем простую логику обмена: 1->2, 2->3, 3->1
    data = dialog_manager.dialog_data
    
    # Сохраняем текущие значения
    temp_dept = data.get("priority_1_department")
    temp_pos = data.get("priority_1_position")
    
    # Циклический сдвиг: 1->2, 2->3, 3->1
    data["priority_1_department"] = data.get("priority_2_department")
    data["priority_1_position"] = data.get("priority_2_position")
    
    data["priority_2_department"] = data.get("priority_3_department")
    data["priority_2_position"] = data.get("priority_3_position")
    
    data["priority_3_department"] = temp_dept
    data["priority_3_position"] = temp_pos
    
    # Остаемся на том же экране для просмотра изменений
    await dialog_manager.update({})


async def on_start_over(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик начала выбора заново"""
    # Очищаем все данные о приоритетах
    keys_to_remove = [
        "priority_1_department", "priority_1_position",
        "priority_2_department", "priority_2_position", 
        "priority_3_department", "priority_3_position",
        "selected_department", "edit_selected_department", "editing_priority"
    ]
    
    for key in keys_to_remove:
        dialog_manager.dialog_data.pop(key, None)
    
    # Начинаем сначала
    await dialog_manager.switch_to(JobSelectionSG.select_department)


async def on_add_priority_2(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик добавления второго приоритета"""
    await dialog_manager.switch_to(JobSelectionSG.select_department_2)


async def on_add_priority_3(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик добавления третьего приоритета"""
    await dialog_manager.switch_to(JobSelectionSG.select_department_3)
