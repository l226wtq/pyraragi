from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image, ImageOps
from scipy.fftpack import dct

try:
    import pyvips
except Exception:  # pragma: no cover - depends on system libvips availability
    pyvips = None


DHASH_WIDTH = 9
DHASH_HEIGHT = 8
PHASH_SIZE = 32
PHASH_LOW_SIZE = 8


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


def compute_phash(image_bytes: bytes) -> str | None:
    try:
        pixels = _phash_pixels_vips(image_bytes)
    except Exception:
        pixels = _phash_pixels_pillow(image_bytes)

    if pixels is None:
        return None

    try:
        coefficients = dct(dct(pixels, axis=0, norm="ortho"), axis=1, norm="ortho")
        low_freq = coefficients[:PHASH_LOW_SIZE, :PHASH_LOW_SIZE].flatten()
        median = np.median(low_freq[1:])
        value = 0
        for bit in low_freq > median:
            value = (value << 1) | int(bit)
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


def _phash_pixels_vips(image_bytes: bytes) -> np.ndarray:
    if pyvips is None:
        raise RuntimeError("pyvips is not available")

    image = pyvips.Image.new_from_buffer(image_bytes, "", access="sequential", autorotate=True)
    if image.hasalpha():
        image = image.flatten(background=[255, 255, 255])
    if image.bands > 1:
        image = image.colourspace("b-w")

    image = image.resize(PHASH_SIZE / image.width, vscale=PHASH_SIZE / image.height, kernel="lanczos3")
    image = image.cast("uchar").copy_memory()
    pixels = np.frombuffer(image.write_to_memory(), dtype=np.uint8)
    return pixels.reshape(PHASH_SIZE, PHASH_SIZE).astype(np.float32)


def _phash_pixels_pillow(image_bytes: bytes) -> np.ndarray | None:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            image = image.convert("L").resize((PHASH_SIZE, PHASH_SIZE), Image.Resampling.LANCZOS)
            return np.asarray(image, dtype=np.float32)
    except Exception:
        return None
