from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

try:
    import pyvips
except Exception:  # pragma: no cover - depends on system libvips availability
    pyvips = None

THUMB_BACKGROUND = (24, 26, 30)


def generate_thumbnail(
    image_bytes: bytes,
    output_path: Path,
    size: tuple[int, int] = (420, 620),
    output_format: str = "webp",
) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(image_bytes).hexdigest()
    output_format = _normalize_output_format(output_format)

    if pyvips is not None:
        try:
            _generate_thumbnail_vips(image_bytes, output_path, size, output_format)
            return digest
        except Exception:
            # Keep local development resilient when libvips lacks support for a
            # particular codec. Pillow is slower, but it is a useful fallback.
            if output_format == "jxl":
                raise
            pass

    _generate_thumbnail_pillow(image_bytes, output_path, size, output_format)
    return digest


def get_image_size(image_bytes: bytes) -> tuple[int | None, int | None]:
    if pyvips is not None:
        try:
            image = pyvips.Image.new_from_buffer(image_bytes, "", access="sequential", autorotate=True)
            return image.width, image.height
        except Exception:
            pass

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            return image.width, image.height
    except Exception:
        return None, None


def _generate_thumbnail_vips(image_bytes: bytes, output_path: Path, size: tuple[int, int], output_format: str) -> None:
    image = pyvips.Image.new_from_buffer(image_bytes, "", access="sequential", autorotate=True)
    image = _vips_to_srgb(image)

    scale = min(size[0] / image.width, size[1] / image.height, 1.0)
    if scale < 1:
        image = image.resize(scale, kernel="lanczos3")

    canvas = pyvips.Image.black(size[0], size[1]).new_from_image(list(THUMB_BACKGROUND))
    left = max((size[0] - image.width) // 2, 0)
    top = max((size[1] - image.height) // 2, 0)
    canvas = canvas.insert(image, left, top).copy_memory()
    if output_format == "jxl":
        canvas.jxlsave(str(output_path), Q=78, effort=4)
    elif output_format == "jpg":
        canvas.jpegsave(str(output_path), Q=82, optimize_coding=True)
    else:
        canvas.webpsave(str(output_path), Q=78, effort=4)


def _vips_to_srgb(image):
    if image.hasalpha():
        image = image.flatten(background=list(THUMB_BACKGROUND))

    if image.bands == 1:
        image = image.colourspace("srgb")
    elif image.bands > 3:
        image = image.extract_band(0, n=3)

    if image.interpretation != "srgb":
        image = image.colourspace("srgb")
    return image


def _generate_thumbnail_pillow(image_bytes: bytes, output_path: Path, size: tuple[int, int], output_format: str) -> None:
    if output_format == "jxl":
        raise RuntimeError("JPEG XL thumbnail output requires libvips/pyvips.")

    with Image.open(BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail(size)
        background = Image.new("RGB", size, THUMB_BACKGROUND)
        x = (size[0] - image.width) // 2
        y = (size[1] - image.height) // 2
        background.paste(image.convert("RGB"), (x, y))
        if output_format == "jpg":
            background.save(output_path, "JPEG", quality=82, optimize=True)
        else:
            background.save(output_path, "WEBP", quality=78, method=6)


def _normalize_output_format(value: str) -> str:
    value = (value or "webp").lower().lstrip(".")
    if value == "jpeg":
        return "jpg"
    if value in {"webp", "jxl", "jpg"}:
        return value
    return "webp"
