"""Utility helpers for timetable dialog"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from config.config import Event


@dataclass
class ScheduleItem:
    """Structure representing a row in the day timetable."""

    item_id: str
    label: str
    start_datetime: str
    type: str  # "simple" or "group"
    group_id: Optional[str] = None


def generate_event_id(event: Event) -> str:
    """Return deterministic identifier for event."""
    return event.event_id


def generate_group_id(event: Event) -> Optional[str]:
    """Return deterministic identifier for event group if registration is required."""
    return event.group_id


def format_event_time_range(start_time: str, end_time: str) -> str:
    """Format a time range for display."""
    return f"{start_time} – {end_time}"


def format_event_summary(title: str, location: str, time_range: str) -> str:
    """Format short summary for event detail."""
    location_display = f" ({location})" if location else ""
    return f"<b>{title}</b>{location_display}\n{time_range}"


def distribute_capacity(total_capacity: int, events: List[Event]) -> Dict[str, int]:
    """Split total capacity equally between events and assign leftovers to later items."""

    if not events:
        return {}

    base = total_capacity // len(events)
    remainder = total_capacity % len(events)

    capacities: Dict[str, int] = {}
    for index, event in enumerate(sorted(events, key=lambda e: e.title)):
        extra = 1 if index >= len(events) - remainder else 0
        capacities[event.event_id] = base + extra
    return capacities


def build_day_schedule(events: List[Event]) -> Tuple[List[ScheduleItem], Dict[str, List[Event]]]:
    """Create display items for a day and map of group events."""

    schedule: List[ScheduleItem] = []
    groups: Dict[str, List[Event]] = {}

    for event in events:
        group_id = generate_group_id(event) if event.registration_required else None

        if group_id:
            groups.setdefault(group_id, []).append(event)
        else:
            schedule.append(
                ScheduleItem(
                    item_id=f"event:{event.event_id}",
                    label=f"{event.start_time} – {event.end_time} · {event.title}",
                    start_datetime=event.start_datetime.isoformat(),
                    type="simple",
                    group_id=None,
                )
            )

    # Append grouped entries preserving chronological order
    added_groups = set()
    for event in events:
        group_id = generate_group_id(event) if event.registration_required else None
        if group_id and group_id not in added_groups:
            added_groups.add(group_id)
            schedule.append(
                ScheduleItem(
                    item_id=f"group:{group_id}",
                    label=f"{event.start_time} – {event.end_time} · Параллельные мероприятия (регистрация)",
                    start_datetime=event.start_datetime.isoformat(),
                    type="group",
                    group_id=group_id,
                )
            )

    schedule.sort(key=lambda item: item.start_datetime)
    return schedule, groups


def serialize_event(event: Event) -> Dict[str, Any]:
    """Convert Event object to JSON-serialisable payload."""
    return {
        "event_id": event.event_id,
        "group_id": event.group_id,
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "start_date": event.start_date,
        "start_time": event.start_time,
        "end_date": event.end_date,
        "end_time": event.end_time,
        "registration_required": event.registration_required,
    }