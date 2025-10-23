"""Utility script to wipe registrations for selected timetable events."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.config import load_config
from app.infrastructure.database import DatabaseManager

TARGET_ALIASES: List[str] = []

TARGET_SLOTS: List[Dict[str, Any]] = [
    {
        "start_date": "2025-10-25",
        "start_time": "14:30",
        "description": "День 3 · 14:30–15:50",
    },
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

    slot_groups = []
    for slot in TARGET_SLOTS:
        matches = [
            event for event in config.events
            if event.start_date == slot["start_date"]
            and event.start_time == slot["start_time"]
            and event.registration_required
        ]

        if not matches:
            logging.error(
                "No registration-required events found for slot %s %s",
                slot["start_date"],
                slot["start_time"],
            )
            continue

        group_id = matches[0].group_id
        slot_groups.append((slot, group_id, matches))

    db_manager = DatabaseManager(config.db)
    await db_manager.init()

    try:
        deleted_aliases = 0
        if event_ids:
            deleted_aliases = await db_manager.delete_event_registrations(event_ids)

        deleted_groups = []
        for slot, group_id, matches in slot_groups:
            deleted = await db_manager.delete_event_registrations_by_group(group_id)
            deleted_groups.append((slot, group_id, deleted, matches))
    finally:
        await db_manager.close()

    if target_events:
        readable_targets = ", ".join(f"{alias} ({event.event_id})" for alias, event in target_events)
        logging.info("Processed alias-based events: %s", readable_targets)
        logging.info("Deleted registrations by alias: %s", deleted_aliases)

    for slot, group_id, deleted, matches in slot_groups:
        match_aliases = ", ".join(event.alias or event.title for event in matches)
        logging.info(
            "Cleared group %s (%s %s · %s events: %s) — deleted registrations: %s",
            group_id,
            slot["start_date"],
            slot["description"],
            len(matches),
            match_aliases,
            deleted,
        )


if __name__ == "__main__":
    asyncio.run(main())
