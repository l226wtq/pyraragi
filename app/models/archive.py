from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Archive(Base):
    __tablename__ = "archives"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    file_path: Mapped[str] = mapped_column(Text, unique=True)
    extension: Mapped[str] = mapped_column(String(16), index=True)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    file_mtime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    partial_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    full_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0, index=True)
    cover_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    is_new: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    pages: Mapped[list[ArchivePage]] = relationship(
        back_populates="archive",
        cascade="all, delete-orphan",
        order_by="ArchivePage.page_index",
    )
    tag_links: Mapped[list[ArchiveTag]] = relationship(back_populates="archive", cascade="all, delete-orphan")


class ArchivePage(Base):
    __tablename__ = "archive_pages"
    __table_args__ = (UniqueConstraint("archive_id", "page_index", name="uq_archive_page_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    archive_id: Mapped[str] = mapped_column(ForeignKey("archives.id", ondelete="CASCADE"), index=True)
    page_index: Mapped[int] = mapped_column(Integer)
    inner_path: Mapped[str] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_md5: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    page_type: Mapped[str] = mapped_column(String(32), default="normal", index=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    duplicate_of_archive_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    duplicate_of_page_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    archive: Mapped[Archive] = relationship(back_populates="pages")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("namespace", "name", name="uq_tag_namespace_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    namespace: Mapped[str] = mapped_column(String(96), default="", index=True)
    name: Mapped[str] = mapped_column(String(256), index=True)
    normalized_name: Mapped[str] = mapped_column(String(256), index=True)

    archive_links: Mapped[list[ArchiveTag]] = relationship(back_populates="tag", cascade="all, delete-orphan")


class ArchiveTag(Base):
    __tablename__ = "archive_tags"
    __table_args__ = (UniqueConstraint("archive_id", "tag_id", name="uq_archive_tag"),)

    archive_id: Mapped[str] = mapped_column(ForeignKey("archives.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    archive: Mapped[Archive] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship(back_populates="archive_links")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), unique=True)
    query: Mapped[str] = mapped_column(Text, default="")
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)


class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    __table_args__ = (UniqueConstraint("archive_id", "user_key", name="uq_reading_progress_user_archive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    archive_id: Mapped[str] = mapped_column(ForeignKey("archives.id", ondelete="CASCADE"), index=True)
    user_key: Mapped[str] = mapped_column(String(128), default="local", index=True)
    page: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_path: Mapped[str] = mapped_column(Text)
    destination_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_extension: Mapped[str] = mapped_column(String(8), default="cbz")
    overwrite: Mapped[bool] = mapped_column(Boolean, default=False)
    delete_source: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    current_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    completed_files: Mapped[int] = mapped_column(Integer, default=0)
    skipped_files: Mapped[int] = mapped_column(Integer, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    log: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    stop_requested: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    skipped_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    current_item: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    log: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FileDuplicateGroup(Base):
    __tablename__ = "file_duplicate_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_size: Mapped[int] = mapped_column(BigInteger, index=True)
    partial_hash: Mapped[str] = mapped_column(String(64), index=True)
    full_sha256: Mapped[str] = mapped_column(String(64), index=True)
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    members: Mapped[list[FileDuplicateMember]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="FileDuplicateMember.file_path",
    )


class FileDuplicateMember(Base):
    __tablename__ = "file_duplicate_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("file_duplicate_groups.id", ondelete="CASCADE"), index=True)
    archive_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    file_path: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(512))
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)

    group: Mapped[FileDuplicateGroup] = relationship(back_populates="members")


Index("ix_archives_title_trgm", Archive.title, postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"})
Index("ix_tags_normalized_name_trgm", Tag.normalized_name, postgresql_using="gin", postgresql_ops={"normalized_name": "gin_trgm_ops"})
