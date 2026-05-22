from sqlalchemy import inspect, text

from app.db.session import Base, engine
from app import models  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_archive_hash_columns()


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
