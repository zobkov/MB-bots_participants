"""SQLAlchemy models for the application"""

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class User(Base):
    """User model for storing telegram user information and debate registration"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)  # telegram user_id
    username = Column(String, nullable=True)  # telegram username
    visible_name = Column(String, nullable=False)  # user's visible name
    debate_reg = Column(Integer, nullable=True)  # debate case number (1-5)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', visible_name='{self.visible_name}', debate_reg={self.debate_reg})>"