from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Archive, ArchiveTag, Tag


def list_archives(
    db: Session,
    query: str = "",
    offset: int = 0,
    limit: int = 60,
    sort: str = "title",
    descending: bool = False,
) -> tuple[int, list[Archive]]:
    stmt: Select[tuple[Archive]] = select(Archive).options(selectinload(Archive.tag_links).selectinload(ArchiveTag.tag))

    tokens = [token.strip() for token in query.split() if token.strip()]
    for token in tokens:
        if ":" in token:
            namespace, name = token.split(":", 1)
            stmt = stmt.where(
                Archive.id.in_(
                    select(ArchiveTag.archive_id)
                    .join(Tag)
                    .where(Tag.namespace == namespace.lower(), Tag.normalized_name.ilike(f"%{name.lower()}%"))
                )
            )
        else:
            stmt = stmt.where(
                or_(
                    Archive.title.ilike(f"%{token}%"),
                    Archive.filename.ilike(f"%{token}%"),
                    Archive.id.in_(
                        select(ArchiveTag.archive_id).join(Tag).where(Tag.normalized_name.ilike(f"%{token.lower()}%"))
                    ),
                )
            )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    sort_column = {
        "title": Archive.title,
        "created": Archive.created_at,
        "last_read": Archive.last_read_at,
        "pages": Archive.page_count,
        "size": Archive.file_size,
    }.get(sort, Archive.title)
    stmt = stmt.order_by(sort_column.desc().nullslast() if descending else sort_column.asc().nullslast())
    stmt = stmt.offset(offset).limit(limit)
    return total, list(db.scalars(stmt).all())


def get_archive(db: Session, archive_id: str) -> Archive | None:
    return db.scalar(
        select(Archive)
        .where(Archive.id == archive_id)
        .options(selectinload(Archive.pages), selectinload(Archive.tag_links).selectinload(ArchiveTag.tag))
    )


def archive_to_dict(archive: Archive) -> dict:
    return {
        "id": archive.id,
        "title": archive.title,
        "filename": archive.filename,
        "extension": archive.extension,
        "file_size": archive.file_size,
        "partial_hash": archive.partial_hash,
        "full_sha256": archive.full_sha256,
        "page_count": archive.page_count,
        "is_new": archive.is_new,
        "last_read_at": archive.last_read_at,
        "tags": [{"namespace": link.tag.namespace, "name": link.tag.name} for link in archive.tag_links],
    }
