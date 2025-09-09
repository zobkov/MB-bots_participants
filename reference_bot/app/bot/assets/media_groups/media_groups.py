from pathlib import Path

from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.types.input_file import FSInputFile
from app.utils.photo_utils import get_photo_sender


def compose_media_group(paths: list[str], caption: str | None = None) -> MediaGroupBuilder:
        """Build a MediaGroup from local file paths.

        - caption is optional; if None or empty, no caption will be sent.
        - Telegram requires InputFile objects for local uploads; passing plain strings
            may be treated as URLs/file_ids and lead to WEBPAGE_MEDIA_EMPTY.
        """
        media_group = MediaGroupBuilder(caption=caption) if caption else MediaGroupBuilder()
        for p in paths:
                media_group.add_photo(FSInputFile(p))
        return media_group


def compose_media_group_optimized(relative_paths: list[str], caption: str | None = None) -> MediaGroupBuilder:
    """
    Build a MediaGroup using file_id when available, fallback to local files.
    
    Args:
        relative_paths: List of paths relative to images folder (e.g., ["start/1.png", "start/2.png"])
        caption: Optional caption for the media group
        
    Returns:
        MediaGroupBuilder ready to build
    """
    photo_sender = get_photo_sender()
    media_group = MediaGroupBuilder(caption=caption) if caption else MediaGroupBuilder()
    
    for relative_path in relative_paths:
        # Пытаемся получить file_id
        file_id = photo_sender.get_file_id(relative_path)
        
        if file_id:
            # Используем file_id для быстрой отправки
            media_group.add_photo(file_id)
        else:
            # Fallback: используем файл напрямую
            full_path = Path("app/bot/assets/images") / relative_path
            if full_path.exists():
                media_group.add_photo(FSInputFile(full_path))
    
    return media_group


def build_start_media_group(caption: str | None = None):
    """Build optimized media group for start images using file_id when available"""
    
    # Относительные пути от папки images
    start_relative_paths = [
        "start/1.jpg",
        "start/2.png", 
        "start/3.png",
        "start/4.png",
        "start/5.png",
        "start/6.png",
        "start/8.png",
        "start/7.png",
        "start/9.png",
    ]
    
    # Используем оптимизированную функцию
    media_group = compose_media_group_optimized(start_relative_paths, caption=caption)
    return media_group.build()


def build_start_media_group_legacy(caption: str | None = None):
    """Legacy version using file paths (kept for compatibility)"""
    # Используем папку с новыми изображениями
    images_dir = Path(__file__).parent.parent / "images" / "start"
    
    # Используем все PNG файлы из папки start (1.png - 9.png)
    start_media_paths = [
        images_dir / "1.png",
        images_dir / "2.png",
        images_dir / "3.png",
        images_dir / "4.png",
        images_dir / "5.png",
        images_dir / "6.png",
        images_dir / "7.png",
        images_dir / "8.png",
        images_dir / "9.png",
    ]

    media_group = compose_media_group([str(p) for p in start_media_paths], caption=caption)
    return media_group.build()


def build_creative_stage_media_group(caption: str | None = None):
    """Build media group for creative stage subdepartment"""
    creative_stage_paths = [
        "choose_position/creative/ТВОРЧЕСКИЙ_сцена_1.png",
        "choose_position/creative/ТВОРЧЕСКИЙ_сцена_2.png", 
        "choose_position/creative/ТВОРЧЕСКИЙ_сцена_3.png"
    ]
    
    media_group = compose_media_group_optimized(creative_stage_paths, caption=caption)
    return media_group.build()


def build_smm_social_media_group(caption: str | None = None):
    """Build media group for SMM social networks subdepartment"""
    smm_social_paths = [
        "choose_position/smmpr/СММ_соцсети_1.png",
        "choose_position/smmpr/СММ_соцсети_2.png"
    ]
    
    media_group = compose_media_group_optimized(smm_social_paths, caption=caption)
    return media_group.build()


def build_smm_media_media_group(caption: str | None = None):
    """Build media group for SMM media show subdepartment"""
    smm_media_paths = [
        "choose_position/smmpr/СММ_шоу_1.png",
        "choose_position/smmpr/СММ_шоу_2.png"
    ]
    
    media_group = compose_media_group_optimized(smm_media_paths, caption=caption)
    return media_group.build()



