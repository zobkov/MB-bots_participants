# Utility functions for timetable dialog
# Place your utility functions here

def generate_event_id(event_title: str, start_date: str, start_time: str) -> int:
    """Генерирует уникальный ID для события"""
    return hash(f"{event_title}_{start_date}_{start_time}")


def format_event_time_range(start_time: str, end_time: str) -> str:
    """Форматирует временной диапазон события"""
    return f"{start_time} – {end_time}"


def format_event_summary(title: str, location: str, time_range: str) -> str:
    """Форматирует краткое описание события"""
    return f"<b>{title}</b> ({location})\n{time_range}"