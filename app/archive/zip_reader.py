from __future__ import annotations

import re
import zipfile
from pathlib import Path

from app.archive.types import is_image_path


def natural_key(value: str) -> list[int | str]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


class ZipArchiveReader:
    def __init__(self, archive_path: str | Path) -> None:
        self.archive_path = Path(archive_path)

    def list_images(self) -> list[str]:
        with zipfile.ZipFile(self.archive_path) as archive:
            names = [
                info.filename
                for info in archive.infolist()
                if not info.is_dir() and is_image_path(info.filename) and not _is_noise_path(info.filename)
            ]
        return sorted(names, key=natural_key)

    def read_file(self, inner_path: str) -> bytes:
        with zipfile.ZipFile(self.archive_path) as archive:
            with archive.open(inner_path) as handle:
                return handle.read()


def _is_noise_path(path: str) -> bool:
    parts = Path(path).parts
    name = Path(path).name
    return "__MACOSX" in parts or name.startswith("._")
