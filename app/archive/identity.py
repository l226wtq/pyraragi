from pathlib import Path
import hashlib


def compute_archive_id(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        digest.update(handle.read(512_000))
    return digest.hexdigest()
