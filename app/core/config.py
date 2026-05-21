from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Pyrragi"
    app_env: str = "development"
    secret_key: str = "change-me"

    database_url: str = "postgresql+psycopg://pyrragi:pyrragi@postgres:5432/pyrragi"
    redis_url: str = "redis://redis:6379/0"
    celery_task_always_eager: bool = False
    celery_task_eager_propagates: bool = True

    archive_dir: Path = Field(default=Path("/data/archives"))
    thumb_dir: Path = Field(default=Path("/data/thumbs"))
    cache_dir: Path = Field(default=Path("/data/cache"))
    max_upload_mb: int = 2048


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.archive_dir.mkdir(parents=True, exist_ok=True)
    settings.thumb_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
