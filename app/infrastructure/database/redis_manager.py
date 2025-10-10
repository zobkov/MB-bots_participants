"""Redis manager for caching debate registration limits"""

import logging
import json
from typing import Dict, Optional
import redis.asyncio as redis
from config.config import RedisConfig

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages Redis connections and debate registration cache"""
    
    # Redis keys
    DEBATE_COUNTS_KEY = "debate:registrations:counts"
    DEBATE_LIMITS_KEY = "debate:registrations:limits"
    
    # Debate case limits
    LIMITS = {
        1: 32,  # ВТБ
        2: 41,  # Алабуга + Б1 <= 41 (cases 2 and 3)
        3: 41,  # Алабуга + Б1 <= 41 (cases 2 and 3) 
        4: 42,  # Северсталь + Альфа <= 42 (cases 4 and 5)
        5: 42,  # Северсталь + Альфа <= 42 (cases 4 and 5)
    }
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.redis = None
        
    async def init(self):
        """Initialize Redis connection"""
        self.redis = redis.Redis(
            host=self.config.host,
            port=self.config.port,
            password=self.config.password if self.config.password else None,
            decode_responses=True
        )
        
        # Test connection
        await self.redis.ping()
        
        # Initialize limits in Redis
        await self.redis.hset(self.DEBATE_LIMITS_KEY, mapping={
            str(k): v for k, v in self.LIMITS.items()
        })
        
        logger.info("Redis initialized successfully")
        
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")
    
    async def sync_with_database(self, db_counts: Dict[int, int]):
        """Sync Redis cache with database counts"""
        await self.redis.hset(self.DEBATE_COUNTS_KEY, mapping={
            str(k): v for k, v in db_counts.items()
        })
        logger.info(f"Synced Redis cache with database: {db_counts}")
    
    async def get_debate_counts(self) -> Dict[int, int]:
        """Get current debate registration counts from cache"""
        counts_data = await self.redis.hgetall(self.DEBATE_COUNTS_KEY)
        if not counts_data:
            return {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        return {int(k): int(v) for k, v in counts_data.items()}
    
    async def increment_debate_count(self, case_number: int) -> int:
        """Increment debate registration count for a case"""
        new_count = await self.redis.hincrby(self.DEBATE_COUNTS_KEY, str(case_number), 1)
        logger.info(f"Incremented case {case_number} count to {new_count}")
        return new_count
    
    async def get_remaining_slots(self) -> Dict[int, int]:
        """Get remaining slots for each debate case considering shared limits"""
        counts = await self.get_debate_counts()
        
        remaining = {}
        
        # ВТБ - individual limit
        remaining[1] = max(0, self.LIMITS[1] - counts[1])
        
        # Алабуга + Б1 - shared limit
        shared_count_23 = counts[2] + counts[3]
        remaining_23 = max(0, self.LIMITS[2] - shared_count_23)
        remaining[2] = remaining_23
        remaining[3] = remaining_23
        
        # Северсталь + Альфа - shared limit  
        shared_count_45 = counts[4] + counts[5]
        remaining_45 = max(0, self.LIMITS[4] - shared_count_45)
        remaining[4] = remaining_45
        remaining[5] = remaining_45
        
        return remaining
    
    async def can_register_for_case(self, case_number: int) -> bool:
        """Check if registration is possible for a specific case"""
        remaining = await self.get_remaining_slots()
        return remaining.get(case_number, 0) > 0
    
    async def get_case_name(self, case_number: int) -> str:
        """Get human-readable case name"""
        names = {
            1: "ВТБ",
            2: "Алабуга", 
            3: "Б1",
            4: "Северсталь",
            5: "Альфа"
        }
        return names.get(case_number, "Unknown")