import logging
from datetime import datetime, timezone
from typing import Optional

from psycopg import AsyncConnection, AsyncCursor

from app.infrastructure.database.models.applications import ApplicationsModel

logger = logging.getLogger(__name__)


class _ApplicationsDB:
    __tablename__ = "applications"

    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def create_application(
        self,
        *,
        user_id: int,
    ) -> None:
        await self.connection.execute(
            """
            INSERT INTO applications(user_id, created, updated)
            VALUES(%s, %s, %s) ON CONFLICT (user_id) DO NOTHING;
        """,
            (user_id, datetime.now(timezone.utc), datetime.now(timezone.utc)),
        )
        logger.info(
            "Application created. db='%s', user_id=%d",
            self.__tablename__,
            user_id,
        )

    async def get_application(self, *, user_id: int) -> ApplicationsModel | None:
        cursor: AsyncCursor = await self.connection.execute(
            """
            SELECT id, user_id, created, updated,
                   full_name, university, course, phone, email, telegram_username,
                   how_found_kbk, department_1, position_1, subdepartment_1,
                   department_2, position_2, subdepartment_2, department_3, position_3, subdepartment_3,
                   experience, motivation, resume_local_path, resume_google_drive_url, previous_department
            FROM applications
            WHERE user_id = %s
        """,
            (user_id,),
        )
        data = await cursor.fetchone()
        return ApplicationsModel(*data) if data else None

    async def update_first_stage_form(
        self,
        *,
        user_id: int,
        full_name: str,
        university: str,
        course: int,
        phone: str,
        email: str,
        telegram_username: str,
        how_found_kbk: str,
        department_1: Optional[str] = None,
        position_1: Optional[str] = None,
        subdepartment_1: Optional[str] = None,
        department_2: Optional[str] = None,
        position_2: Optional[str] = None,
        subdepartment_2: Optional[str] = None,
        department_3: Optional[str] = None,
        position_3: Optional[str] = None,
        subdepartment_3: Optional[str] = None,
        experience: str,
        motivation: str,
        resume_local_path: Optional[str] = None,
        resume_google_drive_url: Optional[str] = None,
        previous_department: Optional[str] = None,
    ) -> None:
        await self.connection.execute(
            """
            UPDATE applications
            SET full_name = %s, university = %s, course = %s, phone = %s, email = %s,
                telegram_username = %s, how_found_kbk = %s, 
                department_1 = %s, position_1 = %s, subdepartment_1 = %s,
                department_2 = %s, position_2 = %s, subdepartment_2 = %s,
                department_3 = %s, position_3 = %s, subdepartment_3 = %s,
                experience = %s, motivation = %s, resume_local_path = %s, 
                resume_google_drive_url = %s, previous_department = %s, updated = %s
            WHERE user_id = %s
        """,
            (
                full_name, university, course, phone, email, telegram_username,
                how_found_kbk, 
                department_1, position_1, subdepartment_1,
                department_2, position_2, subdepartment_2,
                department_3, position_3, subdepartment_3,
                experience, motivation,
                resume_local_path, resume_google_drive_url, previous_department,
                datetime.now(timezone.utc), user_id
            ),
        )
        logger.info(
            "Application first stage form updated. db='%s', user_id=%d",
            self.__tablename__,
            user_id,
        )
