from sqlalchemy import inspect, text

from app.db.session import Base, engine
from app import models  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_archive_hash_columns()
    _ensure_archive_page_fingerprint_columns()


def _ensure_archive_hash_columns() -> None:
    inspector = inspect(engine)
    if "archives" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("archives")}
    statements = []
    if "partial_hash" not in existing:
        statements.append("ALTER TABLE archives ADD COLUMN partial_hash VARCHAR(64)")
    if "full_sha256" not in existing:
        statements.append("ALTER TABLE archives ADD COLUMN full_sha256 VARCHAR(64)")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _ensure_archive_page_fingerprint_columns() -> None:
    inspector = inspect(engine)
    if "archive_pages" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("archive_pages")}
    statements = []
    if "content_md5" not in existing:
        statements.append("ALTER TABLE archive_pages ADD COLUMN content_md5 VARCHAR(32)")
    if "content_sha256" not in existing:
        statements.append("ALTER TABLE archive_pages ADD COLUMN content_sha256 VARCHAR(64)")
    if "content_dhash" not in existing:
        statements.append("ALTER TABLE archive_pages ADD COLUMN content_dhash VARCHAR(16)")
    if "content_phash" not in existing:
        statements.append("ALTER TABLE archive_pages ADD COLUMN content_phash VARCHAR(16)")
    if "dhash_distance" not in existing:
        statements.append("ALTER TABLE archive_pages ADD COLUMN dhash_distance INTEGER")
    if "phash_distance" not in existing:
        statements.append("ALTER TABLE archive_pages ADD COLUMN phash_distance INTEGER")
    if "page_type" not in existing:
        statements.append("ALTER TABLE archive_pages ADD COLUMN page_type VARCHAR(32) DEFAULT 'normal'")
    if "hidden" not in existing:
        statements.append("ALTER TABLE archive_pages ADD COLUMN hidden BOOLEAN DEFAULT false")
    if "duplicate_of_archive_id" not in existing:
        statements.append("ALTER TABLE archive_pages ADD COLUMN duplicate_of_archive_id VARCHAR(40)")
    if "duplicate_of_page_index" not in existing:
        statements.append("ALTER TABLE archive_pages ADD COLUMN duplicate_of_page_index INTEGER")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
