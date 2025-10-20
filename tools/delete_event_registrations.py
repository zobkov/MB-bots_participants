"""Utility script to wipe registrations for selected timetable events."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.config import load_config
from app.infrastructure.database import DatabaseManager

TARGET_ALIASES: List[str] = [
    "От идеи к рынку",
    "СИБУР",
    "Космос и атом",
]


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    config = load_config()
    events_by_alias = {}
    for event in config.events:
        key = event.alias or event.title
        if key not in events_by_alias:
            events_by_alias[key] = event

    missing = [alias for alias in TARGET_ALIASES if alias not in events_by_alias]
    if missing:
        logging.error("Aliases not found in timetable: %s", ", ".join(missing))
        return

    target_events = [(alias, events_by_alias[alias]) for alias in TARGET_ALIASES]
    event_ids = [event.event_id for _, event in target_events]

    db_manager = DatabaseManager(config.db)
    await db_manager.init()

    try:
        deleted = await db_manager.delete_event_registrations(event_ids)
    finally:
        await db_manager.close()

    readable_targets = ", ".join(f"{alias} ({event.event_id})" for alias, event in target_events)
    logging.info("Processed events: %s", readable_targets)
    logging.info("Deleted registrations: %s", deleted)


if __name__ == "__main__":
    asyncio.run(main())
