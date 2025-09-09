from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram.enums import ContentType
import json
import os

from app.utils.optimized_dialog_widgets import get_file_id_for_path


def load_departments_config():
    """Загрузить конфигурацию отделов"""
    config_path = os.path.join(os.path.dirname(__file__), '../../../../config/departments.json')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def get_departments_list(dialog_manager: DialogManager, **kwargs):
    """Получить список департаментов для выбора"""
    config = load_departments_config()
    departments = []
    
    for dept_key, dept_data in config["departments"].items():
        departments.append((dept_key, dept_data["name"]))
    
    return {
        "departments": departments,
    }


async def get_subdepartments_list(dialog_manager: DialogManager, **kwargs):
    """Получить список под-отделов для выбранного департамента"""
    config = load_departments_config()
    
    # Получаем выбранный департамент из состояния
    selected_dept = dialog_manager.dialog_data.get("selected_department")
    if not selected_dept:
        return {"subdepartments": [], "selected_department": "", "department_description": ""}
    
    dept_data = config["departments"].get(selected_dept, {})
    subdepartments = []
    
    # Если есть под-отделы
    if "subdepartments" in dept_data:
        for subdept_key, subdept_data in dept_data["subdepartments"].items():
            subdepartments.append((subdept_key, subdept_data["name"]))
    
    return {
        "subdepartments": subdepartments,
        "selected_department": dept_data.get("name", selected_dept),
        "department_description": dept_data.get("description", "")
    }


def _is_vacancy_already_selected(dialog_data, dept_key, subdept_key, pos_index, exclude_priority=None):
    """Проверить, выбрана ли уже данная вакансия"""
    current_vacancy = (dept_key, subdept_key, pos_index)
    
    # Проверяем все приоритеты
    for i in range(1, 4):
        # Пропускаем проверку для редактируемого приоритета
        if exclude_priority and i == exclude_priority:
            continue
            
        dept = dialog_data.get(f"priority_{i}_department")
        subdept = dialog_data.get(f"priority_{i}_subdepartment")
        pos = dialog_data.get(f"priority_{i}_position")
        
        if dept and pos is not None:
            stored_vacancy = (dept, subdept, str(pos))
            if stored_vacancy == current_vacancy:
                return True
    
    return False


async def get_positions_for_department(dialog_manager: DialogManager, **kwargs):
    """Получить список позиций для выбранного департамента или под-отдела"""
    config = load_departments_config()
    
    # Получаем выбранный департамент и под-отдел из состояния
    selected_dept = dialog_manager.dialog_data.get("selected_department")
    selected_subdept = dialog_manager.dialog_data.get("selected_subdepartment")
    
    print(f"DEBUG: get_positions_for_department - selected_dept={selected_dept}, selected_subdept={selected_subdept}")
    
    if not selected_dept:
        return {"positions": [], "selected_department": "", "department_description": ""}
    
    dept_data = config["departments"].get(selected_dept, {})
    positions = []
    department_name = dept_data.get("name", selected_dept)
    department_description = dept_data.get("description", "")
    
    # Если выбран под-отдел
    if selected_subdept and "subdepartments" in dept_data:
        subdept_data = dept_data["subdepartments"].get(selected_subdept, {})
        positions_list = subdept_data.get("positions", [])
        department_name = f"{department_name} - {subdept_data.get('name', selected_subdept)}"
        department_description = subdept_data.get("description", department_description)
        print(f"DEBUG: Using subdepartment positions - subdept={selected_subdept}, positions_count={len(positions_list)}")
    else:
        # Берем позиции напрямую из отдела
        positions_list = dept_data.get("positions", [])
        print(f"DEBUG: Using department positions - dept={selected_dept}, positions_count={len(positions_list)}")
    
    print(f"DEBUG: positions_list = {positions_list}")
    
    dialog_data = dialog_manager.dialog_data
    
    # Определяем, какой приоритет мы сейчас выбираем, чтобы исключить его из проверки
    current_state = dialog_manager.current_context().state.state
    exclude_priority = None
    if current_state == "JobSelectionSG:select_position":
        exclude_priority = 1
    elif current_state == "JobSelectionSG:select_position_2":
        exclude_priority = 2
    elif current_state == "JobSelectionSG:select_position_3":
        exclude_priority = 3
    
    for i, pos_name in enumerate(positions_list):
        # Проверяем, не выбрана ли уже эта позиция
        if not _is_vacancy_already_selected(dialog_data, selected_dept, selected_subdept, str(i), exclude_priority):
            positions.append((str(i), pos_name))
    
    print(f"DEBUG: final positions = {positions}")
    
    return {
        "positions": positions,
        "selected_department": department_name,
        "department_description": department_description
    }


async def get_priorities_overview(dialog_manager: DialogManager, **kwargs):
    """Получить обзор всех выбранных приоритетов"""
    data = dialog_manager.dialog_data
    config = load_departments_config()
    
    # Проверяем start_data, так как данные могут быть переданы через start()
    start_data = dialog_manager.start_data or {}
    combined_data = {**start_data, **data}  # start_data имеет меньший приоритет
    
    # Проверяем, это редактирование или первичное заполнение
    is_editing = combined_data.get("is_editing", False)
    
    priorities_text = ""
    priorities_count = 0
    
    # Формируем текст с приоритетами
    for i in range(1, 4):
        dept_key = combined_data.get(f"priority_{i}_department")
        subdept_key = combined_data.get(f"priority_{i}_subdepartment")
        pos_index = combined_data.get(f"priority_{i}_position")
        
        if dept_key and pos_index is not None:
            priorities_count += 1
            dept_data = config["departments"].get(dept_key, {})
            dept_name = dept_data.get("name", dept_key)
            
            # Если есть под-отдел
            if subdept_key and "subdepartments" in dept_data:
                subdept_data = dept_data["subdepartments"].get(subdept_key, {})
                positions_list = subdept_data.get("positions", [])
                full_dept_name = f"{dept_name} - {subdept_data.get('name', subdept_key)}"
            else:
                positions_list = dept_data.get("positions", [])
                full_dept_name = dept_name
            
            # Получаем позицию по индексу из массива
            try:
                pos_name = positions_list[int(pos_index)]
            except (IndexError, ValueError):
                pos_name = "Неизвестная позиция"
                
            priorities_text += f"🥇 <b>{i}-й приоритет:</b> {full_dept_name} - {pos_name}\n"
        else:
            priorities_text += f"⚪ <b>{i}-й приоритет:</b> <i>не выбран</i>\n"
    
    return {
        "priorities_text": priorities_text,
        "priorities_count": priorities_count,
        "can_add_2": priorities_count >= 1 and not combined_data.get("priority_2_department"),
        "can_add_3": priorities_count >= 2 and not combined_data.get("priority_3_department"),
        "is_editing": is_editing,
        "continue_button_text": "✅ Сохранить изменения" if is_editing else "✅ Продолжить заполнение анкеты"
    }


async def get_edit_departments_list(dialog_manager: DialogManager, **kwargs):
    """Получить список департаментов для редактирования с предзаполнением текущего выбора"""
    # Получаем обычный список отделов
    result = await get_departments_list(dialog_manager, **kwargs)
    
    # Определяем редактируемый приоритет и отмечаем выбранный отдел
    editing_priority = dialog_manager.dialog_data.get("editing_priority", 1)
    current_dept = dialog_manager.dialog_data.get(f"priority_{editing_priority}_department")
    
    if current_dept:
        # Устанавливаем выбранный отдел в состояние редактирования
        dialog_manager.dialog_data["edit_selected_department"] = current_dept
        
        # Отмечаем текущий выбор в списке отделов
        departments = result.get("departments", [])
        updated_departments = []
        for dept_id, dept_name in departments:
            if dept_id == current_dept:
                updated_departments.append((dept_id, f"✅ {dept_name} (текущий выбор)"))
            else:
                updated_departments.append((dept_id, dept_name))
        result["departments"] = updated_departments
    
    return result


async def get_edit_subdepartments_list(dialog_manager: DialogManager, **kwargs):
    """Получить список под-отделов для редактирования с предзаполнением текущего выбора"""
    config = load_departments_config()
    
    # Получаем выбранный департамент из состояния редактирования
    selected_dept = dialog_manager.dialog_data.get("edit_selected_department")
    if not selected_dept:
        return {"subdepartments": [], "selected_department": "", "department_description": ""}
    
    dept_data = config["departments"].get(selected_dept, {})
    subdepartments = []
    
    # Получаем текущий выбранный под-отдел для редактируемого приоритета
    editing_priority = dialog_manager.dialog_data.get("editing_priority", 1)
    current_subdept = dialog_manager.dialog_data.get(f"priority_{editing_priority}_subdepartment")
    
    # Если есть под-отделы
    if "subdepartments" in dept_data:
        for subdept_key, subdept_data in dept_data["subdepartments"].items():
            if subdept_key == current_subdept:
                display_name = f"✅ {subdept_data['name']} (текущий выбор)"
            else:
                display_name = subdept_data["name"]
            subdepartments.append((subdept_key, display_name))
    
    if current_subdept:
        dialog_manager.dialog_data["edit_selected_subdepartment"] = current_subdept
    
    return {
        "subdepartments": subdepartments,
        "selected_department": dept_data.get("name", selected_dept),
        "department_description": dept_data.get("description", "")
    }


async def get_edit_positions_for_department(dialog_manager: DialogManager, **kwargs):
    """Получить список позиций для редактирования выбранного департамента/под-отдела"""
    config = load_departments_config()
    
    # Получаем выбранный департамент и под-отдел из состояния редактирования
    selected_dept = dialog_manager.dialog_data.get("edit_selected_department")
    selected_subdept = dialog_manager.dialog_data.get("edit_selected_subdepartment")
    
    if not selected_dept:
        return {"positions": [], "selected_department": "", "department_description": ""}
    
    dept_data = config["departments"].get(selected_dept, {})
    positions = []
    department_name = dept_data.get("name", selected_dept)
    department_description = dept_data.get("description", "")
    
    # Если выбран под-отдел
    if selected_subdept and "subdepartments" in dept_data:
        subdept_data = dept_data["subdepartments"].get(selected_subdept, {})
        positions_list = subdept_data.get("positions", [])
        department_name = f"{department_name} - {subdept_data.get('name', selected_subdept)}"
        department_description = subdept_data.get("description", department_description)
    else:
        # Берем позиции напрямую из отдела
        positions_list = dept_data.get("positions", [])
    
    dialog_data = dialog_manager.dialog_data
    editing_priority = dialog_data.get("editing_priority", 1)
    
    # Получаем текущую выбранную позицию для редактируемого приоритета
    current_position = dialog_data.get(f"priority_{editing_priority}_position")
    current_dept = dialog_data.get(f"priority_{editing_priority}_department")
    current_subdept = dialog_data.get(f"priority_{editing_priority}_subdepartment")
    
    for i, pos_name in enumerate(positions_list):
        # Проверяем, не выбрана ли уже эта позиция
        # (исключая редактируемый приоритет)
        if not _is_vacancy_already_selected(dialog_data, selected_dept, selected_subdept, str(i), exclude_priority=editing_priority):
            # Отмечаем текущую выбранную позицию специальным символом
            # Проверяем не только индекс позиции, но и соответствие отдела/подотдела
            is_current_choice = (
                current_position is not None and 
                str(i) == str(current_position) and 
                current_dept == selected_dept and 
                current_subdept == selected_subdept
            )
            
            if is_current_choice:
                display_name = f"✅ {pos_name} (текущий выбор)"
            else:
                display_name = pos_name
            positions.append((str(i), display_name))
    
    return {
        "positions": positions,
        "selected_department": department_name,
        "department_description": department_description
    }


async def get_department_selection_media(dialog_manager: DialogManager, **kwargs):
    """Получаем медиа для окна выбора отдела"""
    file_id = get_file_id_for_path("choose_department/отделы.png")
    
    if file_id:
        media = MediaAttachment(
            type=ContentType.PHOTO,
            file_id=MediaId(file_id)
        )
    else:
        media = MediaAttachment(
            type=ContentType.PHOTO,
            path="app/bot/assets/images/choose_department/отделы.png"
        )
    
    return {
        "media": media
    }


async def get_subdepartment_media(dialog_manager: DialogManager, **kwargs):
    """Получаем медиа для под-отдела на основе выбранного отдела"""
    selected_dept = dialog_manager.dialog_data.get("selected_department")
    
    if not selected_dept:
        # Fallback изображение
        return await get_department_selection_media(dialog_manager, **kwargs)
    
    # Определяем путь к изображению отдела
    department_images = {
        "creative": "choose_department/creative/творческий.png",
        "design": "choose_department/design/дизайн.png", 
        "exhibition": "choose_department/exhibition/exhibition.png",
        "logistics_it": "choose_department/logistics/логистика.png",
        "partners": "choose_department/partners/partners.png",
        "program": "choose_department/program/program.png",
        "smm_pr": "choose_department/smmpr/smm.png"
    }
    
    image_path = department_images.get(selected_dept, "choose_department/отделы.png")
    file_id = get_file_id_for_path(image_path)
    
    if file_id:
        media = MediaAttachment(
            type=ContentType.PHOTO,
            file_id=MediaId(file_id)
        )
    else:
        media = MediaAttachment(
            type=ContentType.PHOTO,
            path=f"app/bot/assets/images/{image_path}"
        )
    
    return {
        "media": media
    }


async def get_position_media(dialog_manager: DialogManager, **kwargs):
    """Получаем медиа для позиций на основе выбранного отдела и под-отдела"""
    selected_dept = dialog_manager.dialog_data.get("selected_department")
    selected_subdept = dialog_manager.dialog_data.get("selected_subdepartment")
    
    # Проверяем, была ли отправлена медиа-группа для этого подотдела
    # Если да, то не показываем DynamicMedia (медиа-группа уже отправлена отдельно)
    if (selected_dept == "creative" and selected_subdept == "stage") or \
       (selected_dept == "smm_pr" and selected_subdept in ["social", "media"]):
        # Для подотделов с медиа-группами возвращаем простое placeholder изображение
        file_id = get_file_id_for_path("choose_department/отделы.png")
        if file_id:
            media = MediaAttachment(
                type=ContentType.PHOTO,
                file_id=MediaId(file_id)
            )
        else:
            media = MediaAttachment(
                type=ContentType.PHOTO,
                path="app/bot/assets/images/choose_department/отделы.png"
            )
        return {
            "media": media
        }
    
    if not selected_dept:
        return await get_department_selection_media(dialog_manager, **kwargs)
    
    # Базовые изображения для отделов без подотделов
    department_position_images = {
        "design": "choose_position/design/ДИЗАЙН.png",
        "exhibition": "choose_position/exhibition/ВЫСТАВКИ.png", 
        "logistics_it": "choose_position/logistics/ЛОГИСТИКА.png",
        "partners": "choose_position/partners/ПАРТНЕРЫ.png",
        "program": "choose_position/program/ПРОГРАММА.png"
    }
    
    # Для отделов с подотделами без медиа-группы
    if selected_dept == "creative" and selected_subdept == "booth":
        image_path = "choose_position/creative/ТВОРЧЕСКИЙ_стенд.png"
    else:
        # Обычные отделы
        image_path = department_position_images.get(selected_dept, "choose_department/отделы.png")
    
    file_id = get_file_id_for_path(image_path)
    
    if file_id:
        media = MediaAttachment(
            type=ContentType.PHOTO,
            file_id=MediaId(file_id)
        )
    else:
        media = MediaAttachment(
            type=ContentType.PHOTO,
            path=f"app/bot/assets/images/{image_path}"
        )
    
    return {
        "media": media
    }


# Функции для редактирования (аналогичные основным, но используют edit_ префиксы)
async def get_edit_subdepartment_media(dialog_manager: DialogManager, **kwargs):
    """Получаем медиа для под-отдела при редактировании"""
    selected_dept = dialog_manager.dialog_data.get("edit_selected_department")
    
    if not selected_dept:
        return await get_department_selection_media(dialog_manager, **kwargs)
    
    department_images = {
        "creative": "choose_department/creative/творческий.png",
        "design": "choose_department/design/дизайн.png",
        "exhibition": "choose_department/exhibition/выставочный.png", 
        "logistics_it": "choose_department/logistics/логистика.png",
        "partners": "choose_department/partners/партнеры.png",
        "program": "choose_department/program/программа.png",
        "smm_pr": "choose_department/smmpr/smm.png"
    }
    
    image_path = department_images.get(selected_dept, "choose_department/отделы.png")
    file_id = get_file_id_for_path(image_path)
    
    if file_id:
        media = MediaAttachment(
            type=ContentType.PHOTO,
            file_id=MediaId(file_id)
        )
    else:
        media = MediaAttachment(
            type=ContentType.PHOTO,
            path=f"app/bot/assets/images/{image_path}"
        )
    
    return {
        "media": media
    }


async def get_edit_position_media(dialog_manager: DialogManager, **kwargs):
    """Получаем медиа для позиций при редактировании"""
    selected_dept = dialog_manager.dialog_data.get("edit_selected_department")
    selected_subdept = dialog_manager.dialog_data.get("edit_selected_subdepartment")
    
    # Проверяем, была ли отправлена медиа-группа для этого подотдела при редактировании
    # Если да, то не показываем DynamicMedia (медиа-группа уже отправлена отдельно)
    if (selected_dept == "creative" and selected_subdept == "stage") or \
       (selected_dept == "smm_pr" and selected_subdept in ["social", "media"]):
        # Для подотделов с медиа-группами возвращаем простое placeholder изображение
        file_id = get_file_id_for_path("choose_department/отделы.png")
        if file_id:
            media = MediaAttachment(
                type=ContentType.PHOTO,
                file_id=MediaId(file_id)
            )
        else:
            media = MediaAttachment(
                type=ContentType.PHOTO,
                path="app/bot/assets/images/choose_department/отделы.png"
            )
        return {
            "media": media
        }
    
    if not selected_dept:
        return await get_department_selection_media(dialog_manager, **kwargs)
    
    department_position_images = {
        "design": "choose_position/design/ДИЗАЙН.png",
        "exhibition": "choose_position/exhibition/ВЫСТАВКИ.png",
        "logistics_it": "choose_position/logistics/ЛОГИСТИКА.png", 
        "partners": "choose_position/partners/ПАРТНЕРЫ.png",
        "program": "choose_position/program/ПРОГРАММА.png"
    }
    
    # Для отделов с подотделами без медиа-группы
    if selected_dept == "creative" and selected_subdept == "booth":
        image_path = "choose_position/creative/ТВОРЧЕСКИЙ_стенд.png"
    else:
        image_path = department_position_images.get(selected_dept, "choose_department/отделы.png")
    
    file_id = get_file_id_for_path(image_path)
    
    if file_id:
        media = MediaAttachment(
            type=ContentType.PHOTO,
            file_id=MediaId(file_id)
        )
    else:
        media = MediaAttachment(
            type=ContentType.PHOTO,
            path=f"app/bot/assets/images/{image_path}"
        )
    
    return {
        "media": media
    }



def should_show_position_media(data, widget, dialog_manager: DialogManager):
    """Проверяет, нужно ли показывать медиа в окне выбора позиций"""
    # Определяем текущее состояние для понимания какой приоритет
    current_state = dialog_manager.current_context().state.state
    
    # Проверяем, это обычный выбор или редактирование
    if current_state in ["JobSelectionSG:edit_priority_1_position", "JobSelectionSG:edit_priority_2_position", "JobSelectionSG:edit_priority_3_position"]:
        # Для редактирования используем edit_selected_* данные
        selected_dept = dialog_manager.dialog_data.get("edit_selected_department")
        selected_subdept = dialog_manager.dialog_data.get("edit_selected_subdepartment")
    else:
        # Определяем приоритет по состоянию для обычного выбора
        if current_state == "JobSelectionSG:select_position":
            priority = 1
        elif current_state == "JobSelectionSG:select_position_2":
            priority = 2
        elif current_state == "JobSelectionSG:select_position_3":
            priority = 3
        else:
            return True  # По умолчанию показываем медиа
        
        # Получаем данные о выбранном отделе и подотделе для этого приоритета
        selected_dept = dialog_manager.dialog_data.get(f"priority_{priority}_department")
        selected_subdept = dialog_manager.dialog_data.get(f"priority_{priority}_subdepartment")
    
    # Если выбран отдел с медиа-группой, то не показываем DynamicMedia
    if (selected_dept == "creative" and selected_subdept == "stage") or \
       (selected_dept == "smm_pr" and selected_subdept in ["social", "media"]):
        return False
    
    return True
