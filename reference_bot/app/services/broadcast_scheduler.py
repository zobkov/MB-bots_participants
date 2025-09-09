import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Literal
import hashlib

from aiogram import Bot
import psycopg_pool
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.triggers.date import DateTrigger

from app.infrastructure.database.database.db import DB

logger = logging.getLogger(__name__)

# Московский часовой пояс (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))

UserGroup = Literal["not_submitted", "submitted"]


@dataclass
class BroadcastItem:
    when: datetime
    text: str
    groups: List[UserGroup]

    @staticmethod
    def from_dict(d: dict) -> "BroadcastItem":
        # Accept ISO timestamps, default to Moscow time if no tz
        ts = d.get("datetime") or d.get("when")
        if not ts:
            raise ValueError("Broadcast item missing datetime")
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            # Если нет часового пояса - считаем что это московское время
            dt = dt.replace(tzinfo=MOSCOW_TZ)
        
        text = d.get("text")
        if not text:
            raise ValueError("Broadcast item missing text")
        groups = d.get("groups") or []
        groups = [g for g in groups if g in ("not_submitted", "submitted")]
        if not groups:
            raise ValueError("Broadcast item must have at least one valid group")
        return BroadcastItem(when=dt, text=text, groups=groups)

    def get_job_id(self) -> str:
        """Generate unique job ID based on content"""
        content = f"{self.when.isoformat()}{self.text}{'|'.join(self.groups)}"
        return f"broadcast_{hashlib.md5(content.encode()).hexdigest()[:12]}"


async def send_broadcast_message(bot: Bot, db_pool: psycopg_pool.AsyncConnectionPool, text: str, groups: List[str]):
    """
    Функция для отправки рассылки, которая будет выполняться планировщиком
    """
    logger.info("Executing broadcast: '%s' to groups %s", text[:50], groups)
    total = 0
    
    for group in groups:
        try:
            async with db_pool.connection() as conn:
                db = DB(users_connection=conn, applications_connection=conn)
                user_ids = await db.users.list_user_ids_by_group(group=group)
                if not user_ids:
                    logger.info("No users found for group '%s'", group)
                    continue
                
                logger.info("Sending to %d users in group '%s'", len(user_ids), group)
                sent = await _broadcast_to_users(bot, db_pool, user_ids, text)
                total += sent
                
        except Exception as e:
            logger.error("Error broadcasting to group '%s': %s", group, e)
    
    logger.info("Broadcast completed: sent to %d users total", total)


async def _broadcast_to_users(bot: Bot, db_pool: psycopg_pool.AsyncConnectionPool, user_ids: List[int], text: str) -> int:
    """Helper function to send messages to list of users"""
    sent = 0
    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=text)
            sent += 1
            # Rate limiting
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning("Failed to send broadcast to user %s: %s", uid, e)
            try:
                # Mark user as blocked if forbidden
                if "Forbidden" in str(e) or "bot was blocked" in str(e):
                    async with db_pool.connection() as conn:
                        db = DB(users_connection=conn, applications_connection=conn)
                        await db.users.update_alive_status(user_id=uid, is_alive=False)
            except Exception:
                pass
    return sent


class BroadcastScheduler:
    def __init__(self, bot: Bot, db_pool: psycopg_pool.AsyncConnectionPool, json_path: str | Path):
        self.bot = bot
        self.db_pool = db_pool
        self.json_path = Path(json_path)
        self.scheduler: AsyncIOScheduler | None = None
        
    async def start(self):
        """Initialize and start APScheduler"""
        if self.scheduler and self.scheduler.running:
            return
        
        # Setup APScheduler with fallback to memory storage
        try:
            from config.config import load_config
            config = load_config()
            
            # Use memory jobstore to avoid pickle issues with Redis
            jobstore = MemoryJobStore()
            logger.info("Using memory jobstore for APScheduler (Redis disabled due to pickle issues)")
            
        except Exception as e:
            logger.error("Failed to get config for APScheduler: %s", e)
            jobstore = MemoryJobStore()
    
        # Setup APScheduler
        jobstores = {
            'default': jobstore
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=MOSCOW_TZ  # По умолчанию московское время
        )
        
        self.scheduler.start()
        logger.info("APScheduler started with Moscow timezone")
        
        # Load and schedule broadcasts from JSON
        await self._schedule_broadcasts()
    
    async def stop(self):
        """Stop APScheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
            logger.info("APScheduler stopped")
    
    async def _schedule_broadcasts(self):
        """Load broadcasts from JSON and schedule them"""
        items = self._load_items()
        if not items:
            logger.info("No broadcast items to schedule")
            return
        
        # Get existing jobs to avoid duplicates
        existing_jobs = {job.id for job in self.scheduler.get_jobs()}
        
        scheduled_count = 0
        skipped_count = 0
        
        for item in items:
            job_id = item.get_job_id()
            
            # Skip if already scheduled
            if job_id in existing_jobs:
                logger.debug("Broadcast job %s already exists, skipping", job_id)
                skipped_count += 1
                continue
            
            # Skip if time has already passed (with 1 minute grace period)
            now = datetime.now(MOSCOW_TZ)
            if item.when <= now - timedelta(minutes=1):
                logger.debug("Broadcast time %s has passed, skipping", 
                           item.when.strftime("%Y-%m-%d %H:%M %Z"))
                skipped_count += 1
                continue
            
            # Schedule the broadcast
            self.scheduler.add_job(
                send_broadcast_message,
                trigger=DateTrigger(run_date=item.when),
                args=[self.bot, self.db_pool, item.text, item.groups],
                id=job_id,
                name=f"Broadcast: {item.text[:30]}...",
                replace_existing=False
            )
            
            scheduled_count += 1
            logger.info("Scheduled broadcast for %s: '%s'", 
                       item.when.strftime("%Y-%m-%d %H:%M %Z"), 
                       item.text[:50])
        
        logger.info("Broadcast scheduling completed: %d new jobs, %d skipped", 
                   scheduled_count, skipped_count)
    
    def _load_items(self) -> List[BroadcastItem]:
        """Load broadcast items from JSON file"""
        if not self.json_path.exists():
            logger.info("Broadcast file not found: %s", self.json_path)
            return []
        try:
            data = json.loads(self.json_path.read_text(encoding="utf-8"))
            items = [BroadcastItem.from_dict(x) for x in data]
            return sorted(items, key=lambda i: i.when)
        except Exception as e:
            logger.error("Failed to load broadcast file %s: %s", self.json_path, e)
            return []
    
    async def reload_broadcasts(self):
        """Reload broadcasts from JSON file (useful for dynamic updates)"""
        if not self.scheduler or not self.scheduler.running:
            logger.warning("Scheduler not started, cannot reload broadcasts")
            return
        logger.info("Reloading broadcasts from %s", self.json_path)
        await self._schedule_broadcasts()
    
    def list_scheduled_jobs(self):
        """List all scheduled broadcast jobs"""
        if not self.scheduler or not self.scheduler.running:
            logger.warning("Scheduler not started")
            return []
        
        jobs = self.scheduler.get_jobs()
        broadcast_jobs = [job for job in jobs if job.id.startswith('broadcast_')]
        
        logger.info("Found %d scheduled broadcast jobs:", len(broadcast_jobs))
        for job in broadcast_jobs:
            logger.info("  %s: %s (next run: %s)", job.id, job.name, job.next_run_time)
        
        return broadcast_jobs
