from pathlib import Path
import hashlib


PARTIAL_HASH_BYTES = 512_000


def compute_archive_id(path: Path) -> str:
    return compute_partial_sha1(path)


def compute_partial_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        digest.update(handle.read(PARTIAL_HASH_BYTES))
    return digest.hexdigest()


def compute_full_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()
