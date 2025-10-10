"""Database manager for SQLAlchemy operations"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, select, func
from config.config import DatabaseConfig
from .models import Base, User

logger = logging.getLogger(__name__)


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