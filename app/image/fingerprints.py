from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps

try:
    import pyvips
except Exception:  # pragma: no cover - depends on system libvips availability
    pyvips = None


DHASH_WIDTH = 9
DHASH_HEIGHT = 8


def compute_dhash(image_bytes: bytes) -> str | None:
    try:
        pixels = _dhash_pixels_vips(image_bytes)
    except Exception:
        pixels = _dhash_pixels_pillow(image_bytes)

    if pixels is None:
        return None

    try:
        value = 0
        for row in pixels:
            for column in range(DHASH_WIDTH - 1):
                value = (value << 1) | int(row[column] > row[column + 1])
        return f"{value:016x}"
    except Exception:
        return None


def hash_distance(left: str | None, right: str | None) -> int | None:
    if not left or not right:
        return None
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError:
        return None


def hash_bands(value: str, band_chars: int = 2) -> set[str]:
    return {value[index : index + band_chars] for index in range(0, len(value), band_chars)}


def _dhash_pixels_vips(image_bytes: bytes) -> list[list[int]]:
    if pyvips is None:
        raise RuntimeError("pyvips is not available")

    image = pyvips.Image.new_from_buffer(image_bytes, "", access="sequential", autorotate=True)
    if image.hasalpha():
        image = image.flatten(background=[255, 255, 255])
    if image.bands > 1:
        image = image.colourspace("b-w")

    image = image.resize(DHASH_WIDTH / image.width, vscale=DHASH_HEIGHT / image.height, kernel="lanczos3")
    image = image.cast("uchar").copy_memory()
    raw = image.write_to_memory()
    return [
        [raw[row * DHASH_WIDTH + column] for column in range(DHASH_WIDTH)]
        for row in range(DHASH_HEIGHT)
    ]


def _dhash_pixels_pillow(image_bytes: bytes) -> list[list[int]] | None:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            image = image.convert("L").resize((DHASH_WIDTH, DHASH_HEIGHT), Image.Resampling.LANCZOS)
            flat = list(image.getdata())
            return [
                flat[row * DHASH_WIDTH : (row + 1) * DHASH_WIDTH]
                for row in range(DHASH_HEIGHT)
            ]
    except Exception:
        return None
