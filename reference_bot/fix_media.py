#!/usr/bin/env python3
"""
Скрипт для автоматической замены StaticMedia на DynamicMedia в job_selection dialogs
"""

import re

# Читаем файл
with open('/Users/artyomzobkov/cbc_crew_selection_bot/app/bot/dialogs/job_selection/dialogs.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем DynamicMedia path/type на "media"
content = re.sub(
    r'DynamicMedia\(\s*path="[^"]*",\s*type="photo"\s*\)',
    'DynamicMedia(\n            "media"\n        )',
    content
)

# Обновляем getters для окон с подотделами и позициями
replacements = [
    # Подотделы - добавляем get_subdepartment_media
    (r'(state=JobSelectionSG\.select_subdepartment(?:_2|_3)?,\s*getter=)get_subdepartments_list', 
     r'\1[get_subdepartments_list, get_subdepartment_media]'),
    
    # Позиции - добавляем get_position_media 
    (r'(state=JobSelectionSG\.select_position(?:_2|_3)?,\s*getter=)get_positions_for_department',
     r'\1[get_positions_for_department, get_position_media]'),
     
    # Отделы (кроме уже обновленных) - добавляем get_department_selection_media
    (r'(state=JobSelectionSG\.select_department(?:_3)?,\s*getter=)get_departments_list',
     r'\1[get_departments_list, get_department_selection_media]'),
     
    # Редактирование отделов - добавляем get_department_selection_media
    (r'(state=JobSelectionSG\.edit_priority_[123],\s*getter=)get_edit_departments_list',
     r'\1[get_edit_departments_list, get_department_selection_media]'),
     
    # Редактирование подотделов - добавляем get_edit_subdepartment_media  
    (r'(state=JobSelectionSG\.edit_priority_[123]_subdepartment,\s*getter=)get_edit_subdepartments_list',
     r'\1[get_edit_subdepartments_list, get_edit_subdepartment_media]'),
     
    # Редактирование позиций - добавляем get_edit_position_media
    (r'(state=JobSelectionSG\.edit_priority_[123]_position,\s*getter=)get_edit_positions_for_department',
     r'\1[get_edit_positions_for_department, get_edit_position_media]'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Записываем обратно
with open('/Users/artyomzobkov/cbc_crew_selection_bot/app/bot/dialogs/job_selection/dialogs.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Замены выполнены успешно!")
