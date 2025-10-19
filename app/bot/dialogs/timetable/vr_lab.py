"""Helpers and constants for VR lab registration flow."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Iterable, Optional, Tuple

VR_LAB_GROUP_ID = "vr_lab:20251024"
VR_LAB_ROOMS: Tuple[str, ...] = ("2206", "2212", "2213", "2215")
VR_LAB_EVENT_TITLE_PREFIX = "vr-lab"
_VR_START_TIME = datetime.strptime("14:00", "%H:%M")
_VR_SLOT_INTERVAL_MINUTES = 15
_VR_SLOT_COUNT = 8

VR_LAB_SLOT_TIMES: Tuple[str, ...] = tuple(
    (_VR_START_TIME + timedelta(minutes=_VR_SLOT_INTERVAL_MINUTES * index)).strftime("%H:%M")
    for index in range(_VR_SLOT_COUNT)
)

TOTAL_SLOTS_PER_ROOM = len(VR_LAB_SLOT_TIMES)


def is_vr_lab_event(event_payload: Dict[str, object]) -> bool:
    """Return True if payload corresponds to the VR lab timetable entry."""
    title = (event_payload.get("title") or "").lower()
    return title.startswith(VR_LAB_EVENT_TITLE_PREFIX)


def build_slot_event_id(room: str, slot_time: str) -> str:
    """Generate persistent identifier for room+slot pair."""
    return f"vr_lab:{room}:{slot_time.replace(':', '')}"


def parse_slot_event_id(event_id: str) -> Optional[Tuple[str, str]]:
    """Extract room and readable slot from stored identifier."""
    if not event_id.startswith("vr_lab:"):
        return None

    parts = event_id.split(":", maxsplit=2)
    if len(parts) != 3:
        return None

    room = parts[1]
    raw_slot = parts[2]
    if len(raw_slot) == 4 and raw_slot.isdigit():
        slot_time = f"{raw_slot[:2]}:{raw_slot[2:]}"
    else:
        slot_time = raw_slot
    return room, slot_time


def iter_room_slot_event_ids(room: str) -> Iterable[str]:
    """Yield all slot identifiers for the given room."""
    for slot_time in VR_LAB_SLOT_TIMES:
        yield build_slot_event_id(room, slot_time)


def count_room_taken_slots(room: str, counts: Dict[str, int]) -> int:
    """Return how many slots are occupied for a room based on counts mapping."""
    return sum(counts.get(event_id, 0) for event_id in iter_room_slot_event_ids(room))


def ensure_room(room: str) -> str:
    if room not in VR_LAB_ROOMS:
        raise ValueError(f"Unknown VR lab room: {room}")
    return room
