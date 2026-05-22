from datetime import datetime

from pydantic import BaseModel


class TagOut(BaseModel):
    namespace: str
    name: str


class ArchiveOut(BaseModel):
    id: str
    title: str
    filename: str
    extension: str
    file_size: int
    page_count: int
    is_new: bool
    last_read_at: datetime | None
    tags: list[TagOut]


class ArchivePageOut(BaseModel):
    page_index: int
    inner_path: str
    width: int | None = None
    height: int | None = None
    byte_size: int | None = None
    content_md5: str | None = None
    content_sha256: str | None = None
    content_dhash: str | None = None
    dhash_distance: int | None = None
    page_type: str = "normal"
    hidden: bool = False
    duplicate_of_archive_id: str | None = None
    duplicate_of_page_index: int | None = None


class SearchResult(BaseModel):
    total: int
    data: list[ArchiveOut]


class UploadResult(BaseModel):
    id: str
    title: str
    queued: bool
