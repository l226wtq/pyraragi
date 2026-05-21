from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


def generate_thumbnail(image_bytes: bytes, output_path: Path, size: tuple[int, int] = (420, 620)) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(image_bytes).hexdigest()
    with Image.open(BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail(size)
        background = Image.new("RGB", size, (24, 26, 30))
        x = (size[0] - image.width) // 2
        y = (size[1] - image.height) // 2
        background.paste(image.convert("RGB"), (x, y))
        background.save(output_path, "WEBP", quality=78, method=6)
    return digest


def get_image_size(image_bytes: bytes) -> tuple[int | None, int | None]:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            return image.width, image.height
    except Exception:
        return None, None
