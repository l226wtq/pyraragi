from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.archives import router as archives_router
from app.api.conversions import router as conversions_router
from app.api.jobs import router as jobs_router
from app.api.library import router as library_router
from app.api.views import router as views_router
from app.core.config import get_settings
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.mount("/assets", StaticFiles(directory="frontend/dist/assets", check_dir=False), name="assets")
app.include_router(archives_router)
app.include_router(conversions_router)
app.include_router(jobs_router)
app.include_router(library_router)
app.include_router(views_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
