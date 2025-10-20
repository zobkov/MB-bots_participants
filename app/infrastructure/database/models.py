"""SQLAlchemy models for the application"""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """User model for storing telegram user information and debate registration"""
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)  # telegram user_id
    username = Column(String, nullable=True)  # telegram username
    visible_name = Column(String, nullable=False)  # user's visible name
    debate_reg = Column(Integer, nullable=True)  # debate case number (1-5)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', visible_name='{self.visible_name}', debate_reg={self.debate_reg})>"


class EventRegistration(Base):
    """Registration record for timetable events."""

    __tablename__ = 'event_registrations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    event_id = Column(String(32), nullable=False, index=True)
    group_id = Column(String(32), nullable=False, index=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'group_id', name='uq_event_registration_user_group'),
        UniqueConstraint('user_id', 'event_id', name='uq_event_registration_user_event'),
    )

    def __repr__(self):
        return (
            f"<EventRegistration(id={self.id}, user_id={self.user_id}, event_id='{self.event_id}', "
            f"group_id='{self.group_id}')>"
        )


class CoachSessionRequest(Base):
    """Stored coach session application."""

    __tablename__ = "coach_session_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    full_name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=True)
    university = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(64), nullable=False)
    telegram = Column(String(128), nullable=False)
    request_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<CoachSessionRequest(id={self.id}, full_name='{self.full_name}', email='{self.email}')>"