from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif"}
ARCHIVE_EXTENSIONS = {".zip", ".cbz"}


def is_supported_archive(path: str | Path) -> bool:
    return Path(path).suffix.lower() in ARCHIVE_EXTENSIONS


def is_image_path(path: str) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS
