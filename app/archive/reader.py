from pathlib import Path

from app.archive.zip_reader import ZipArchiveReader


def get_reader(archive_path: str | Path) -> ZipArchiveReader:
    suffix = Path(archive_path).suffix.lower()
    if suffix in {".zip", ".cbz"}:
        return ZipArchiveReader(archive_path)
    raise ValueError(f"Unsupported archive format: {suffix}")
