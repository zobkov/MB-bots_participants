from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.infrastructure.database.models.base import BaseModel


@dataclass
class ApplicationsModel(BaseModel):
    id: int
    user_id: int
    created: datetime
    updated: datetime
    
    # Форма первого этапа
    full_name: Optional[str] = None
    university: Optional[str] = None
    course: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    telegram_username: Optional[str] = None
    how_found_kbk: Optional[str] = None
    # Система приоритетов (заменяет старые department/position)
    department_1: Optional[str] = None
    position_1: Optional[str] = None
    subdepartment_1: Optional[str] = None
    department_2: Optional[str] = None
    position_2: Optional[str] = None
    subdepartment_2: Optional[str] = None
    department_3: Optional[str] = None
    position_3: Optional[str] = None
    subdepartment_3: Optional[str] = None
    experience: Optional[str] = None
    motivation: Optional[str] = None
    resume_local_path: Optional[str] = None
    resume_google_drive_url: Optional[str] = None
    previous_department: Optional[str] = None

    def __post_init__(self):
        pass
