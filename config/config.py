import logging
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib
from environs import Env

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class RedisConfig:
    host: str
    port: int
    password: str


@dataclass
class TgBot:
    token: str


@dataclass
class LoggingConfig:
    level: str
    log_dir: str
    console_output: bool
    file_prefix: str
    retention_days: int
    admin_ids: List[int]


@dataclass
class GoogleSheetsConfig:
    credentials_path: str
    spreadsheet_id: str


@dataclass
class Event:
    title: str
    description: str
    location: str
    start_date: str
    start_time: str
    end_date: str
    end_time: str
    registration_required: bool = False
    group_title: Optional[str] = None

    @property
    def start_datetime(self) -> datetime:
        return datetime.strptime(f"{self.start_date} {self.start_time}", "%Y-%m-%d %H:%M")
    
    @property
    def end_datetime(self) -> datetime:
        return datetime.strptime(f"{self.end_date} {self.end_time}", "%Y-%m-%d %H:%M")

    @property
    def event_id(self) -> str:
        """Deterministic identifier for the event, safe to store in DB."""
        payload = f"{self.title}|{self.start_date}|{self.start_time}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    @property
    def group_id(self) -> Optional[str]:
        """Identifier for a parallel registration group, if applicable."""
        if not self.registration_required:
            return None
        payload = f"{self.start_date}|{self.start_time}|parallel"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


@dataclass
class Config:
    tg_bot: TgBot
    db: DatabaseConfig
    redis: RedisConfig
    logging: LoggingConfig
    google_sheets: GoogleSheetsConfig
    start_date: datetime
    events: List[Event]

    def get_day_events(self, day: int) -> List[Event]:
        """Получить события для определенного дня конференции (0-4)"""
        target_date = self.start_date.replace(
            day=self.start_date.day + day
        ).date()
        
        day_events = [
            event for event in self.events
            if datetime.strptime(event.start_date, "%Y-%m-%d").date() == target_date
        ]
        
        # Сортируем по времени начала
        return sorted(day_events, key=lambda x: x.start_datetime)

    def get_days_with_events(self) -> List[int]:
        """Получить список дней, в которые есть мероприятия"""
        conference_dates = set()
        for event in self.events:
            event_date = datetime.strptime(event.start_date, "%Y-%m-%d").date()
            day_diff = (event_date - self.start_date.date()).days
            if 0 <= day_diff <= 4:  # Только дни 0-4
                conference_dates.add(day_diff)
        
        return sorted(list(conference_dates))


def load_config(path: str = None) -> Config:
    """Загрузить конфигурацию из .env и JSON файлов"""
    
    # Загрузка переменных окружения
    env = Env()
    env.read_env()

    # Конфигурация бота
    tg_bot = TgBot(token=env.str("BOT_TOKEN"))

    # Конфигурация базы данных
    db_config = DatabaseConfig(
        host=env.str("POSTGRES_HOST"),
        port=env.int("POSTGRES_PORT", 5432),
        user=env.str("POSTGRES_USER"),
        password=env.str("POSTGRES_PASSWORD"),
        database=env.str("POSTGRES_DB")
    )

    # Конфигурация Redis
    redis_config = RedisConfig(
        host=env.str("REDIS_HOST"),
        port=env.int("REDIS_PORT", 6379),
        password=env.str("REDIS_PASSWORD")
    )

    # Конфигурация логирования
    logging_config = LoggingConfig(
        level=env.str("LOG_LEVEL", "INFO"),
        log_dir=env.str("LOG_DIR", "logs"),
        console_output=env.bool("CONSOLE_OUTPUT", True),
        file_prefix=env.str("LOG_FILE_PREFIX", "bot"),
        retention_days=env.int("LOG_RETENTION_DAYS", 30),
        admin_ids=[int(x.strip()) for x in env.str("ADMIN_IDS", "").split(",") if x.strip()]
    )

    # Конфигурация Google Sheets
    google_sheets_config = GoogleSheetsConfig(
        credentials_path=env.str("GOOGLE_CREDENTIALS_PATH", "config/google_credentials.json"),
        spreadsheet_id=env.str("GOOGLE_SPREADSHEET_ID")
    )

    # Загрузка конфигурации из JSON
    config_path = "config.json"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file {config_path} not found")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        json_config = json.load(f)

    # Парсинг даты начала конференции
    start_date = datetime.strptime(json_config["start_date"], "%Y-%m-%d")

    # Загрузка расписания
    timetable_path = "timetable.json"
    if not os.path.exists(timetable_path):
        raise FileNotFoundError(f"Timetable file {timetable_path} not found")
    
    with open(timetable_path, 'r', encoding='utf-8') as f:
        timetable_data = json.load(f)

    # Создание объектов событий
    events = [Event(**event_data) for event_data in timetable_data]

    logger.info(f"Loaded {len(events)} events from timetable")
    logger.info(f"Conference start date: {start_date.strftime('%Y-%m-%d')}")

    return Config(
        tg_bot=tg_bot,
        db=db_config,
        redis=redis_config,
        logging=logging_config,
        google_sheets=google_sheets_config,
        start_date=start_date,
        events=events
    )
