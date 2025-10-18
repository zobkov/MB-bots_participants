"""Utilities for managing timetable illustration file_ids."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)

TIMETABLE_MEDIA_CHAT_ID = 257026813
ROOT_DIR = Path(__file__).resolve().parents[2]
TIMETABLE_ASSETS_DIR = ROOT_DIR / "assets" / "timetable"
FILE_IDS_PATH = TIMETABLE_ASSETS_DIR / "file_ids.json"


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _list_image_files() -> List[Path]:
    if not TIMETABLE_ASSETS_DIR.exists():
        logger.warning("Timetable assets directory not found at %s", TIMETABLE_ASSETS_DIR)
        return []
    return sorted(
        [
            path
            for path in TIMETABLE_ASSETS_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ],
        key=lambda path: path.name,
    )


def _load_file_ids() -> Dict[str, str]:
    if not FILE_IDS_PATH.exists():
        return {}
    try:
        with FILE_IDS_PATH.open("r", encoding="utf-8") as mapping_file:
            data = json.load(mapping_file)
            if isinstance(data, dict):
                return {str(key): str(value) for key, value in data.items()}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read timetable file_ids: %s", exc)
    return {}


def _save_file_ids(mapping: Dict[str, str]) -> None:
    FILE_IDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FILE_IDS_PATH.open("w", encoding="utf-8") as mapping_file:
        json.dump(mapping, mapping_file, ensure_ascii=False, indent=2)


async def _regenerate_file_ids(bot: Bot, chat_id: int, image_paths: Iterable[Path]) -> Dict[str, str]:
    paths = list(image_paths)
    logger.info("Regenerating timetable file_ids for %s images", len(paths))
    mapping: Dict[str, str] = {}
    for image_path in paths:
        try:
            message = await bot.send_photo(chat_id=chat_id, photo=FSInputFile(image_path))
        except TelegramAPIError as exc:  # noqa: PERF203
            logger.exception("Failed to upload timetable image %s", image_path.name, exc_info=exc)
            raise
        if not message.photo:
            raise RuntimeError(f"Telegram response does not contain photo data for {image_path.name}")
        file_id = message.photo[-1].file_id
        mapping[image_path.name] = file_id
        logger.debug("Stored timetable file_id for %s", image_path.name)
    _save_file_ids(mapping)
    logger.info("Successfully regenerated timetable file_ids")
    return mapping


async def ensure_timetable_media(bot: Bot, chat_id: int = TIMETABLE_MEDIA_CHAT_ID) -> Dict[str, str]:
    image_paths = _list_image_files()
    if not image_paths:
        logger.warning("No timetable images found; skipping media setup")
        return {}

    mapping = _load_file_ids()

    missing_files = [path.name for path in image_paths if path.name not in mapping]
    if missing_files:
        logger.info("Timetable media mapping missing entries for: %s", ", ".join(missing_files))
        mapping = await _regenerate_file_ids(bot, chat_id, image_paths)

    first_image_name = image_paths[0].name
    file_id = mapping.get(first_image_name)
    if not file_id:
        logger.warning("File_id for %s not found; regenerating mapping", first_image_name)
        mapping = await _regenerate_file_ids(bot, chat_id, image_paths)
        file_id = mapping.get(first_image_name)

    if not file_id:
        logger.error("Failed to obtain file_id even after regeneration; aborting timetable media setup")
        return mapping

    try:
        await bot.send_photo(chat_id=chat_id, photo=file_id)
        logger.info("Timetable teaser photo sent successfully using cached file_id")
    except TelegramAPIError as exc:
        logger.warning("Failed to send timetable teaser via cached file_id, regenerating", exc_info=exc)
        mapping = await _regenerate_file_ids(bot, chat_id, image_paths)
        refreshed_id = mapping.get(image_paths[0].name)
        if refreshed_id:
            await bot.send_photo(chat_id=chat_id, photo=refreshed_id)
            logger.info("Timetable teaser photo sent after regeneration")
        else:
            logger.error("Regenerated mapping still missing primary image id")

    return mapping