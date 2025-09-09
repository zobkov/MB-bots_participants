from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import Button
import json
import os

from app.bot.states.job_selection import JobSelectionSG
from app.bot.states.first_stage import FirstStageSG
from app.bot.assets.media_groups.media_groups import (
    build_creative_stage_media_group, 
    build_smm_social_media_group, 
    build_smm_media_media_group
)


def load_departments_config():
    """Загрузить конфигурацию отделов"""
    config_path = os.path.join(os.path.dirname(__file__), '../../../../config/departments.json')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def on_department_selected(
    callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str
):
    """Обработчик выбора департамента"""
    config = load_departments_config()
    current_state = dialog_manager.current_context().state.state
    
    print(f"DEBUG: on_department_selected called")
    print(f"DEBUG: current_state = {current_state}")
    print(f"DEBUG: item_id = {item_id}")
    
    dialog_manager.dialog_data["selected_department"] = item_id
    
    # Проверяем, есть ли у отдела под-отделы
    dept_data = config["departments"].get(item_id, {})
    has_subdepartments = "subdepartments" in dept_data
    
    if current_state == JobSelectionSG.select_department.state:
        dialog_manager.dialog_data["priority_1_department"] = item_id
        if has_subdepartments:
            await dialog_manager.switch_to(JobSelectionSG.select_subdepartment)
        else:
            await dialog_manager.switch_to(JobSelectionSG.select_position)
    elif current_state == JobSelectionSG.select_department_2.state:
        dialog_manager.dialog_data["priority_2_department"] = item_id
        if has_subdepartments:
            await dialog_manager.switch_to(JobSelectionSG.select_subdepartment_2)
        else:
            await dialog_manager.switch_to(JobSelectionSG.select_position_2)
    elif current_state == JobSelectionSG.select_department_3.state:
        dialog_manager.dialog_data["priority_3_department"] = item_id
        if has_subdepartments:
            await dialog_manager.switch_to(JobSelectionSG.select_subdepartment_3)
        else:
            await dialog_manager.switch_to(JobSelectionSG.select_position_3)


async def on_subdepartment_selected(
    callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str
):
    """Обработчик выбора под-отдела"""
    current_state = dialog_manager.current_context().state.state
    
    print(f"DEBUG: on_subdepartment_selected called")
    print(f"DEBUG: current_state = {current_state}")
    print(f"DEBUG: item_id = {item_id}")
    
    dialog_manager.dialog_data["selected_subdepartment"] = item_id
    
    # Получаем информацию о выбранном отделе
    selected_dept = dialog_manager.dialog_data.get("selected_department")
    
    # Проверяем, нужна ли медиа-группа для этого подотдела
    media_group = None
    if selected_dept == "creative" and item_id == "stage":
        media_group = build_creative_stage_media_group()
    elif selected_dept == "smm_pr" and item_id == "social":
        media_group = build_smm_social_media_group()
    elif selected_dept == "smm_pr" and item_id == "media":
        media_group = build_smm_media_media_group()
    
    # Если нужна медиа-группа, отправляем её и сохраняем ID сообщений для последующего удаления
    if media_group:
        sent_messages = await callback.bot.send_media_group(
            chat_id=callback.message.chat.id, 
            media=media_group
        )
        # Сохраняем ID сообщений медиа-группы для удаления
        media_group_message_ids = [msg.message_id for msg in sent_messages]
        dialog_manager.dialog_data["media_group_message_ids"] = media_group_message_ids
    
    if current_state == JobSelectionSG.select_subdepartment.state:
        dialog_manager.dialog_data["priority_1_subdepartment"] = item_id
        await dialog_manager.switch_to(JobSelectionSG.select_position, show_mode=ShowMode.DELETE_AND_SEND)
    elif current_state == JobSelectionSG.select_subdepartment_2.state:
        dialog_manager.dialog_data["priority_2_subdepartment"] = item_id
        await dialog_manager.switch_to(JobSelectionSG.select_position_2, show_mode=ShowMode.DELETE_AND_SEND)
    elif current_state == JobSelectionSG.select_subdepartment_3.state:
        dialog_manager.dialog_data["priority_3_subdepartment"] = item_id
        await dialog_manager.switch_to(JobSelectionSG.select_position_3, show_mode=ShowMode.DELETE_AND_SEND)


async def on_position_selected(
    callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str
):
    """Обработчик выбора позиции"""
    current_state = dialog_manager.current_context().state.state
    
    print(f"DEBUG: on_position_selected called")
    print(f"DEBUG: current_state = {current_state}")
    print(f"DEBUG: item_id = {item_id}")
    
    # Удаляем медиа-группу, если она была отправлена
    media_group_message_ids = dialog_manager.dialog_data.get("media_group_message_ids")
    if media_group_message_ids:
        try:
            for message_id in media_group_message_ids:
                await callback.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=message_id
                )
        except Exception as e:
            print(f"Ошибка при удалении медиа-группы: {e}")
        finally:
            # Очищаем ID медиа-группы
            dialog_manager.dialog_data.pop("media_group_message_ids", None)
    
    if current_state == JobSelectionSG.select_position.state:
        dialog_manager.dialog_data["priority_1_position"] = item_id
        await dialog_manager.switch_to(JobSelectionSG.priorities_overview)
    elif current_state == JobSelectionSG.select_position_2.state:
        dialog_manager.dialog_data["priority_2_position"] = item_id
        await dialog_manager.switch_to(JobSelectionSG.select_department_3)
    elif current_state == JobSelectionSG.select_position_3.state:
        dialog_manager.dialog_data["priority_3_position"] = item_id
        await dialog_manager.switch_to(JobSelectionSG.priorities_overview)


async def on_priority_confirmed(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик подтверждения выбора приоритетов"""
    # Получаем исходные данные формы переданные при запуске диалога
    original_form_data = dict(dialog_manager.start_data or {})
    
    # Проверяем, это редактирование или первичное заполнение
    is_editing = original_form_data.get("is_editing", False)
    
    # Сохраняем данные приоритетов в основные данные заявки
    priority_data = {}
    
    for i in range(1, 4):
        dept_key = dialog_manager.dialog_data.get(f"priority_{i}_department")
        subdept_key = dialog_manager.dialog_data.get(f"priority_{i}_subdepartment")
        pos_index = dialog_manager.dialog_data.get(f"priority_{i}_position")
        
        if dept_key and pos_index is not None:
            priority_data[f"priority_{i}_department"] = dept_key
            if subdept_key:
                priority_data[f"priority_{i}_subdepartment"] = subdept_key
            priority_data[f"priority_{i}_position"] = pos_index
    
    # Объединяем исходные данные формы с новыми данными приоритетов
    combined_data = {**original_form_data, **priority_data}
    
    # Сохраняем приоритеты в родительском диалоге
    dialog_manager.dialog_data.update(priority_data)
    
    if is_editing:
        # Если это редактирование, возвращаемся с результатом в родительский диалог
        # Родительский диалог должен остаться на том же состоянии (confirmation)
        await dialog_manager.done(result=priority_data)
    else:
        # Если это первичное заполнение, продолжаем обычный flow
        await dialog_manager.done(result=priority_data)


async def on_edit_priority_1(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик редактирования первого приоритета"""
    dialog_manager.dialog_data["editing_priority"] = 1
    
    # Проверяем, есть ли уже выбранные данные для этого приоритета
    current_dept = dialog_manager.dialog_data.get("priority_1_department")
    current_subdept = dialog_manager.dialog_data.get("priority_1_subdepartment")
    
    if current_dept:
        # Предзаполняем данные редактирования
        dialog_manager.dialog_data["edit_selected_department"] = current_dept
        
        # Проверяем, есть ли под-отделы у этого отдела
        config = load_departments_config()
        dept_data = config["departments"].get(current_dept, {})
        has_subdepartments = "subdepartments" in dept_data
        has_subdepartments = "subdepartments" in dept_data
        
        if has_subdepartments:
            if current_subdept:
                # Есть и отдел, и под-отдел - переходим к выбору позиции
                dialog_manager.dialog_data["edit_selected_subdepartment"] = current_subdept
                await dialog_manager.switch_to(JobSelectionSG.edit_priority_1_position)
            else:
                # Есть отдел, но нет под-отдела - переходим к выбору под-отдела
                await dialog_manager.switch_to(JobSelectionSG.edit_priority_1_subdepartment)
        else:
            # Отдел без под-отделов - переходим к выбору позиции
            await dialog_manager.switch_to(JobSelectionSG.edit_priority_1_position)
    else:
        # Нет выбранного отдела - начинаем с выбора отдела
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_1)


async def on_edit_priority_2(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик редактирования второго приоритета"""
    dialog_manager.dialog_data["editing_priority"] = 2
    
    # Проверяем, есть ли уже выбранные данные для этого приоритета
    current_dept = dialog_manager.dialog_data.get("priority_2_department")
    current_subdept = dialog_manager.dialog_data.get("priority_2_subdepartment")
    
    if current_dept:
        # Предзаполняем данные редактирования
        dialog_manager.dialog_data["edit_selected_department"] = current_dept
        
        # Проверяем, есть ли под-отделы у этого отдела
        config = load_departments_config()
        dept_data = config["departments"].get(current_dept, {})
        has_subdepartments = "subdepartments" in dept_data
        has_subdepartments = "subdepartments" in dept_data
        
        if has_subdepartments:
            if current_subdept:
                # Есть и отдел, и под-отдел - переходим к выбору позиции
                dialog_manager.dialog_data["edit_selected_subdepartment"] = current_subdept
                await dialog_manager.switch_to(JobSelectionSG.edit_priority_2_position)
            else:
                # Есть отдел, но нет под-отдела - переходим к выбору под-отдела
                await dialog_manager.switch_to(JobSelectionSG.edit_priority_2_subdepartment)
        else:
            # Отдел без под-отделов - переходим к выбору позиции
            await dialog_manager.switch_to(JobSelectionSG.edit_priority_2_position)
    else:
        # Нет выбранного отдела - начинаем с выбора отдела
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_2)


async def on_edit_priority_3(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик редактирования третьего приоритета"""
    dialog_manager.dialog_data["editing_priority"] = 3
    
    # Проверяем, есть ли уже выбранные данные для этого приоритета
    current_dept = dialog_manager.dialog_data.get("priority_3_department")
    current_subdept = dialog_manager.dialog_data.get("priority_3_subdepartment")
    
    if current_dept:
        # Предзаполняем данные редактирования
        dialog_manager.dialog_data["edit_selected_department"] = current_dept
        
        # Проверяем, есть ли под-отделы у этого отдела
        config = load_departments_config()
        dept_data = config["departments"].get(current_dept, {})
        has_subdepartments = "subdepartments" in dept_data
        has_subdepartments = "subdepartments" in dept_data
        
        if has_subdepartments:
            if current_subdept:
                # Есть и отдел, и под-отдел - переходим к выбору позиции
                dialog_manager.dialog_data["edit_selected_subdepartment"] = current_subdept
                await dialog_manager.switch_to(JobSelectionSG.edit_priority_3_position)
            else:
                # Есть отдел, но нет под-отдела - переходим к выбору под-отдела
                await dialog_manager.switch_to(JobSelectionSG.edit_priority_3_subdepartment)
        else:
            # Отдел без под-отделов - переходим к выбору позиции
            await dialog_manager.switch_to(JobSelectionSG.edit_priority_3_position)
    else:
        # Нет выбранного отдела - начинаем с выбора отдела
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_3)


async def on_edit_department_selected(
    callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str
):
    """Обработчик выбора департамента при редактировании"""
    config = load_departments_config()
    
    dialog_manager.dialog_data["edit_selected_department"] = item_id
    
    # Определяем какой приоритет редактируется
    editing_priority = dialog_manager.dialog_data.get("editing_priority", 1)
    
    # Сбрасываем выбранную позицию и подотдел, так как сменился отдел
    # Это исправляет баг с отображением неправильной позиции при смене отдела
    if f"priority_{editing_priority}_position" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data[f"priority_{editing_priority}_position"]
    if f"priority_{editing_priority}_subdepartment" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data[f"priority_{editing_priority}_subdepartment"]
    
    # Сбрасываем также временные данные редактирования для подотдела
    if "edit_selected_subdepartment" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data["edit_selected_subdepartment"]
    
    # Проверяем, есть ли у отдела под-отделы
    dept_data = config["departments"].get(item_id, {})
    has_subdepartments = "subdepartments" in dept_data
    
    if has_subdepartments:
        if editing_priority == 1:
            await dialog_manager.switch_to(JobSelectionSG.edit_priority_1_subdepartment)
        elif editing_priority == 2:
            await dialog_manager.switch_to(JobSelectionSG.edit_priority_2_subdepartment)
        elif editing_priority == 3:
            await dialog_manager.switch_to(JobSelectionSG.edit_priority_3_subdepartment)
    else:
        if editing_priority == 1:
            await dialog_manager.switch_to(JobSelectionSG.edit_priority_1_position, show_mode=ShowMode.DELETE_AND_SEND)
        elif editing_priority == 2:
            await dialog_manager.switch_to(JobSelectionSG.edit_priority_2_position, show_mode=ShowMode.DELETE_AND_SEND)
        elif editing_priority == 3:
            await dialog_manager.switch_to(JobSelectionSG.edit_priority_3_position, show_mode=ShowMode.DELETE_AND_SEND)


async def on_edit_subdepartment_selected(
    callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str
):
    """Обработчик выбора под-отдела при редактировании"""
    dialog_manager.dialog_data["edit_selected_subdepartment"] = item_id
    
    # Определяем какой приоритет редактируется
    editing_priority = dialog_manager.dialog_data.get("editing_priority", 1)
    
    # Сбрасываем выбранную позицию, так как сменился подотдел
    # Это исправляет баг с отображением неправильной позиции при смене подотдела
    if f"priority_{editing_priority}_position" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data[f"priority_{editing_priority}_position"]
    
    # Получаем информацию о выбранном отделе
    selected_dept = dialog_manager.dialog_data.get("edit_selected_department")
    
    # Проверяем, нужна ли медиа-группа для этого подотдела
    media_group = None
    if selected_dept == "creative" and item_id == "stage":
        media_group = build_creative_stage_media_group()
    elif selected_dept == "smm_pr" and item_id == "social":
        media_group = build_smm_social_media_group()
    elif selected_dept == "smm_pr" and item_id == "media":
        media_group = build_smm_media_media_group()
    
    # Если нужна медиа-группа, отправляем её и сохраняем ID сообщений для последующего удаления
    if media_group:
        sent_messages = await callback.bot.send_media_group(
            chat_id=callback.message.chat.id, 
            media=media_group
        )
        # Сохраняем ID сообщений медиа-группы для удаления
        media_group_message_ids = [msg.message_id for msg in sent_messages]
        dialog_manager.dialog_data["edit_media_group_message_ids"] = media_group_message_ids
    
    # Определяем какой приоритет редактируется
    editing_priority = dialog_manager.dialog_data.get("editing_priority", 1)
    
    if editing_priority == 1:
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_1_position, show_mode=ShowMode.DELETE_AND_SEND)
    elif editing_priority == 2:
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_2_position, show_mode=ShowMode.DELETE_AND_SEND)
    elif editing_priority == 3:
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_3_position, show_mode=ShowMode.DELETE_AND_SEND)


async def on_edit_position_selected(
    callback: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str
):
    """Обработчик выбора позиции при редактировании"""
    # Удаляем медиа-группу, если она была отправлена при редактировании
    edit_media_group_message_ids = dialog_manager.dialog_data.get("edit_media_group_message_ids")
    if edit_media_group_message_ids:
        try:
            for message_id in edit_media_group_message_ids:
                await callback.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=message_id
                )
        except Exception as e:
            print(f"Ошибка при удалении медиа-группы при редактировании: {e}")
        finally:
            # Очищаем ID медиа-группы
            dialog_manager.dialog_data.pop("edit_media_group_message_ids", None)
    
    editing_priority = dialog_manager.dialog_data.get("editing_priority", 1)
    edit_dept = dialog_manager.dialog_data.get("edit_selected_department")
    edit_subdept = dialog_manager.dialog_data.get("edit_selected_subdepartment")
    
    # Сохраняем изменения
    dialog_manager.dialog_data[f"priority_{editing_priority}_department"] = edit_dept
    if edit_subdept:
        dialog_manager.dialog_data[f"priority_{editing_priority}_subdepartment"] = edit_subdept
    else:
        # Удаляем под-отдел если он не выбран
        dialog_manager.dialog_data.pop(f"priority_{editing_priority}_subdepartment", None)
    dialog_manager.dialog_data[f"priority_{editing_priority}_position"] = item_id
    
    # Очищаем временные данные редактирования
    dialog_manager.dialog_data.pop("editing_priority", None)
    dialog_manager.dialog_data.pop("edit_selected_department", None)
    dialog_manager.dialog_data.pop("edit_selected_subdepartment", None)
    
    # Возвращаемся к обзору приоритетов
    await dialog_manager.switch_to(JobSelectionSG.priorities_overview)


async def on_back_from_positions(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик нажатия кнопки 'Назад' из окна выбора позиций с удалением медиа-группы"""
    # Удаляем медиа-группу, если она была отправлена
    media_group_message_ids = dialog_manager.dialog_data.get("media_group_message_ids")
    if media_group_message_ids:
        try:
            for message_id in media_group_message_ids:
                await callback.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=message_id
                )
        except Exception as e:
            print(f"Ошибка при удалении медиа-группы: {e}")
        finally:
            # Очищаем ID медиа-группы
            dialog_manager.dialog_data.pop("media_group_message_ids", None)
    
    # Также удаляем медиа-группу редактирования, если она есть
    edit_media_group_message_ids = dialog_manager.dialog_data.get("edit_media_group_message_ids")
    if edit_media_group_message_ids:
        try:
            for message_id in edit_media_group_message_ids:
                await callback.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=message_id
                )
        except Exception as e:
            print(f"Ошибка при удалении медиа-группы редактирования: {e}")
        finally:
            # Очищаем ID медиа-группы
            dialog_manager.dialog_data.pop("edit_media_group_message_ids", None)
    
    # Возвращаемся к выбору департамента в зависимости от кнопки
    button_id = button.widget_id
    if button_id == "back_to_dep_1":
        await dialog_manager.switch_to(JobSelectionSG.select_department)
    elif button_id == "back_to_dep_2":
        await dialog_manager.switch_to(JobSelectionSG.select_department_2)
    elif button_id == "back_to_dep_3":
        await dialog_manager.switch_to(JobSelectionSG.select_department_3)


async def on_back_from_edit_positions(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик нажатия кнопки 'Назад' из окна редактирования позиций с удалением медиа-группы"""
    # Удаляем медиа-группу редактирования, если она была отправлена
    edit_media_group_message_ids = dialog_manager.dialog_data.get("edit_media_group_message_ids")
    if edit_media_group_message_ids:
        try:
            for message_id in edit_media_group_message_ids:
                await callback.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=message_id
                )
        except Exception as e:
            print(f"Ошибка при удалении медиа-группы редактирования: {e}")
        finally:
            # Очищаем ID медиа-группы
            dialog_manager.dialog_data.pop("edit_media_group_message_ids", None)
    
    # Определяем какой приоритет редактируется и возвращаемся к соответствующему состоянию
    editing_priority = dialog_manager.dialog_data.get("editing_priority", 1)
    
    if editing_priority == 1:
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_1)
    elif editing_priority == 2:
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_2)
    elif editing_priority == 3:
        await dialog_manager.switch_to(JobSelectionSG.edit_priority_3)


async def on_swap_priorities(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик перехода к меню выбора приоритетов для обмена"""
    await dialog_manager.switch_to(JobSelectionSG.swap_priorities_menu, show_mode=ShowMode.DELETE_AND_SEND)


async def on_swap_1_2(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик обмена 1-го и 2-го приоритетов"""
    data = dialog_manager.dialog_data
    
    # Обмениваем местами 1-й и 2-й приоритеты
    temp_dept = data.get("priority_1_department")
    temp_subdept = data.get("priority_1_subdepartment")
    temp_pos = data.get("priority_1_position")
    
    data["priority_1_department"] = data.get("priority_2_department")
    data["priority_1_subdepartment"] = data.get("priority_2_subdepartment")
    data["priority_1_position"] = data.get("priority_2_position")
    
    data["priority_2_department"] = temp_dept
    data["priority_2_subdepartment"] = temp_subdept
    data["priority_2_position"] = temp_pos
    
    # Возвращаемся к обзору приоритетов
    await dialog_manager.switch_to(JobSelectionSG.priorities_overview)


async def on_swap_1_3(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик обмена 1-го и 3-го приоритетов"""
    data = dialog_manager.dialog_data
    
    # Обмениваем местами 1-й и 3-й приоритеты
    temp_dept = data.get("priority_1_department")
    temp_subdept = data.get("priority_1_subdepartment")
    temp_pos = data.get("priority_1_position")
    
    data["priority_1_department"] = data.get("priority_3_department")
    data["priority_1_subdepartment"] = data.get("priority_3_subdepartment")
    data["priority_1_position"] = data.get("priority_3_position")
    
    data["priority_3_department"] = temp_dept
    data["priority_3_subdepartment"] = temp_subdept
    data["priority_3_position"] = temp_pos
    
    # Возвращаемся к обзору приоритетов
    await dialog_manager.switch_to(JobSelectionSG.priorities_overview)


async def on_swap_2_3(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик обмена 2-го и 3-го приоритетов"""
    data = dialog_manager.dialog_data
    
    # Обмениваем местами 2-й и 3-й приоритеты
    temp_dept = data.get("priority_2_department")
    temp_subdept = data.get("priority_2_subdepartment")
    temp_pos = data.get("priority_2_position")
    
    data["priority_2_department"] = data.get("priority_3_department")
    data["priority_2_subdepartment"] = data.get("priority_3_subdepartment")
    data["priority_2_position"] = data.get("priority_3_position")
    
    data["priority_3_department"] = temp_dept
    data["priority_3_subdepartment"] = temp_subdept
    data["priority_3_position"] = temp_pos
    
    # Возвращаемся к обзору приоритетов
    await dialog_manager.switch_to(JobSelectionSG.priorities_overview)


async def on_back_to_priorities_overview(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    """Обработчик возврата к обзору приоритетов"""
    await dialog_manager.switch_to(JobSelectionSG.priorities_overview)


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
