"""Database manager for SQLAlchemy operations"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, Set, Iterable

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.config import DatabaseConfig
from .models import Base, EventRegistration, User, CoachSessionRequest

logger = logging.getLogger(__name__)


class EventRegistrationStatus(Enum):
    SUCCESS = "success"
    SWITCHED = "switched"
    ALREADY_REGISTERED_THIS = "already_registered_this"
    GROUP_FULL = "group_full"
    USER_NOT_FOUND = "user_not_found"
    ERROR = "error"


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine = None
        self.sessionmaker = None
        
    async def init(self):
        """Initialize database connection"""
        database_url = (
            f"postgresql+asyncpg://{self.config.user}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{self.config.database}"
        )
        
        self.engine = create_async_engine(database_url, echo=False)
        self.sessionmaker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Create tables if they don't exist
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
        
    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by telegram user_id"""
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def create_user(self, user_id: int, username: Optional[str], visible_name: str) -> User:
        """Create new user"""
        async with self.sessionmaker() as session:
            user = User(
                id=user_id,
                username=username,
                visible_name=visible_name,
                debate_reg=None
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"Created new user: {user}")
            return user
    
    async def update_user_debate_registration(self, user_id: int, case_number: Optional[int]) -> bool:
        """Update user's debate registration (case_number can be None to unregister)"""
        async with self.sessionmaker() as session:
            try:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return False
                    
                user.debate_reg = case_number
                await session.commit()
                
                if case_number is None:
                    logger.info(f"Unregistered user {user_id} from debate")
                else:
                    logger.info(f"Updated user {user_id} debate registration to case {case_number}")
                return True
            except Exception as e:
                logger.error(f"Error updating user {user_id} debate registration: {e}")
                await session.rollback()
                return False
    
    async def get_debate_registrations_count(self) -> Dict[int, int]:
        """Get count of registrations for each debate case"""
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(User.debate_reg, func.count(User.id))
                .where(User.debate_reg.isnot(None))
                .group_by(User.debate_reg)
            )
            
            counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}  # Initialize all cases with 0
            for case_num, count in result.fetchall():
                counts[case_num] = count
                
            logger.debug(f"Current debate registrations: {counts}")
            return counts
    
    async def check_user_already_registered(self, user_id: int) -> Optional[int]:
        """Check if user is already registered for a debate case"""
        user = await self.get_user(user_id)
        return user.debate_reg if user else None
    
    async def get_users_by_debate_case(self, case_number: int) -> List[User]:
        """Get all users registered for a specific debate case"""
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(User)
                .where(User.debate_reg == case_number)
                .order_by(User.id)
            )
            return result.scalars().all()
    
    async def get_total_users_count(self) -> int:
        """Get total number of users in the database"""
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(func.count(User.id))
            )
            return result.scalar()
    
    async def get_registered_users_count(self) -> int:
        """Get number of users registered for any debate case"""
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(func.count(User.id))
                .where(User.debate_reg.isnot(None))
            )
            return result.scalar()
    
    async def get_all_users_for_export(self) -> List[Dict[str, Any]]:
        """Get all users data for export to Google Sheets"""
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(User).order_by(User.id)
            )
            users = result.scalars().all()
            
            # Convert to dictionaries for easier processing
            users_data = []
            for user in users:
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'visible_name': user.visible_name,
                    'debate_reg': user.debate_reg,
                    'updated_at': "—"  # We can add timestamps later if needed
                })
            
            return users_data

    async def register_user_for_event(
        self,
        user_id: int,
        event_id: str,
        group_id: str,
        capacity: int,
    ) -> EventRegistrationStatus:
        async with self.sessionmaker() as session:
            try:
                async with session.begin():
                    return await self._register_user_for_event(session, user_id, event_id, group_id, capacity)
            except Exception as exc:
                logger.error("Error registering user %s for event %s: %s", user_id, event_id, exc)
                return EventRegistrationStatus.ERROR

    async def _register_user_for_event(
        self,
        session: AsyncSession,
        user_id: int,
        event_id: str,
        group_id: str,
        capacity: int,
    ) -> EventRegistrationStatus:
        user = await session.get(User, user_id)
        if not user:
            logger.warning("Attempt to register missing user %s", user_id)
            return EventRegistrationStatus.USER_NOT_FOUND

        existing_registration_result = await session.execute(
            select(EventRegistration)
            .where(
                EventRegistration.user_id == user_id,
                EventRegistration.group_id == group_id,
            )
            .with_for_update()
        )
        existing_registration = existing_registration_result.scalar_one_or_none()

        count_stmt = (
            select(EventRegistration.id)
            .where(EventRegistration.event_id == event_id)
            .with_for_update()
        )
        current_count = len((await session.execute(count_stmt)).scalars().all())

        if existing_registration:
            if existing_registration.event_id == event_id:
                return EventRegistrationStatus.ALREADY_REGISTERED_THIS

            if current_count >= capacity:
                return EventRegistrationStatus.GROUP_FULL

            existing_registration.event_id = event_id
            existing_registration.registered_at = datetime.now(timezone.utc)
            await session.flush()
            return EventRegistrationStatus.SWITCHED

        if current_count >= capacity:
            return EventRegistrationStatus.GROUP_FULL

        registration = EventRegistration(
            user_id=user_id,
            event_id=event_id,
            group_id=group_id,
            registered_at=datetime.now(timezone.utc),
        )
        session.add(registration)
        await session.flush()
        return EventRegistrationStatus.SUCCESS

    async def unregister_user_from_event(self, user_id: int, group_id: str) -> bool:
        async with self.sessionmaker() as session:
            try:
                async with session.begin():
                    result = await session.execute(
                        select(EventRegistration)
                        .where(
                            EventRegistration.user_id == user_id,
                            EventRegistration.group_id == group_id,
                        )
                        .with_for_update()
                    )
                    registration = result.scalar_one_or_none()
                    if not registration:
                        return False

                    await session.delete(registration)
                    await session.flush()
                    return True
            except Exception as exc:
                logger.error("Error unregistering user %s from group %s: %s", user_id, group_id, exc)
                return False

    async def get_event_counts_for_group(self, group_id: str) -> Dict[str, int]:
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(EventRegistration.event_id, func.count(EventRegistration.id))
                .where(EventRegistration.group_id == group_id)
                .group_by(EventRegistration.event_id)
            )
            counts = {event_id: count for event_id, count in result.fetchall()}
            logger.debug("Group %s counts: %s", group_id, counts)
            return counts

    async def get_user_event_registration(self, user_id: int, group_id: str) -> Optional[EventRegistration]:
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(EventRegistration)
                .where(
                    EventRegistration.user_id == user_id,
                    EventRegistration.group_id == group_id,
                )
            )
            return result.scalar_one_or_none()

    async def get_event_registrations_for_export(self) -> List[Dict[str, Any]]:
        """Collect event registrations with user info for offline export preparation."""
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(
                    EventRegistration.user_id,
                    EventRegistration.event_id,
                    EventRegistration.group_id,
                    EventRegistration.registered_at,
                    User.visible_name,
                    User.username,
                )
                .join(User, User.id == EventRegistration.user_id)
                .order_by(EventRegistration.group_id, EventRegistration.registered_at)
            )

            payload: List[Dict[str, Any]] = []
            for row in result.all():
                registered_at = row.registered_at.isoformat() if row.registered_at else ""
                payload.append(
                    {
                        "user_id": row.user_id,
                        "event_id": row.event_id,
                        "group_id": row.group_id,
                        "registered_at": registered_at,
                        "visible_name": row.visible_name,
                        "username": f"@{row.username}" if row.username else "",
                        "status": "Активна",
                        "event_title": "",
                        "group_label": "",
                    }
                )
            return payload

    async def get_all_event_registrations_map(self) -> Dict[int, Set[str]]:
        """Return mapping of user_id to registered event IDs."""
        async with self.sessionmaker() as session:
            result = await session.execute(
                select(EventRegistration.user_id, EventRegistration.event_id)
            )

            mapping: Dict[int, Set[str]] = {}
            for user_id, event_id in result.fetchall():
                mapping.setdefault(int(user_id), set()).add(str(event_id))

            return mapping

    async def delete_event_registrations(self, event_ids: Iterable[str]) -> int:
        """Delete registrations for provided event identifiers."""
        event_ids_list = [str(event_id) for event_id in event_ids if event_id]
        if not event_ids_list:
            return 0

        async with self.sessionmaker() as session:
            try:
                stmt = delete(EventRegistration).where(EventRegistration.event_id.in_(event_ids_list))
                result = await session.execute(stmt)
                await session.commit()
                deleted_count = result.rowcount or 0
                logger.info("Deleted %s registrations for events", deleted_count)
                return deleted_count
            except Exception as exc:
                logger.error("Failed to delete registrations for events %s: %s", event_ids_list, exc)
                await session.rollback()
                raise

    async def delete_event_registrations_by_group(self, group_id: str) -> int:
        """Delete all registrations bound to a specific parallel group."""

        clean_group_id = (group_id or "").strip()
        if not clean_group_id:
            logger.warning("Attempted to delete registrations for empty group id")
            return 0

        async with self.sessionmaker() as session:
            try:
                stmt = delete(EventRegistration).where(EventRegistration.group_id == clean_group_id)
                result = await session.execute(stmt)
                await session.commit()
                deleted_count = result.rowcount or 0
                logger.info("Deleted %s registrations for group %s", deleted_count, clean_group_id)
                return deleted_count
            except Exception as exc:
                logger.error("Failed to delete registrations for group %s: %s", clean_group_id, exc)
                await session.rollback()
                raise

    async def create_coach_session_request(
        self,
        user_id: Optional[int],
        full_name: str,
        age: Optional[int],
        university: str,
        email: str,
        phone: str,
        telegram: str,
        request_text: str,
    ) -> CoachSessionRequest:
        """Persist new coach session application."""

        async with self.sessionmaker() as session:
            try:
                entry = CoachSessionRequest(
                    user_id=user_id,
                    full_name=full_name,
                    age=age,
                    university=university,
                    email=email,
                    phone=phone,
                    telegram=telegram,
                    request_text=request_text,
                )
                session.add(entry)
                await session.commit()
                await session.refresh(entry)
                logger.info("Coach session request stored: id=%s", entry.id)
                return entry
            except Exception as exc:
                await session.rollback()
                logger.error("Failed to store coach session request: %s", exc)
                raise

    async def get_last_coach_session_request(self, user_id: int) -> Optional[CoachSessionRequest]:
        """Fetch the most recent coach session request for the user, if it exists."""

        async with self.sessionmaker() as session:
            result = await session.execute(
                select(CoachSessionRequest)
                .where(CoachSessionRequest.user_id == user_id)
                .order_by(CoachSessionRequest.created_at.desc())
                .limit(1)
            )
            entry = result.scalar_one_or_none()
            if entry:
                logger.debug("Found existing coach session request id=%s for user %s", entry.id, user_id)
            return entry