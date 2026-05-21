from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

FRONTEND_DIST = Path("frontend/dist")
FRONTEND_INDEX = FRONTEND_DIST / "index.html"
router = APIRouter(tags=["views"])


@router.get("/", response_class=HTMLResponse)
def index():
    return _spa_index()


@router.get("/{path:path}", response_class=HTMLResponse)
def spa_fallback(path: str):
    return _spa_index()


def _spa_index():
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="zh-CN">
        <head><meta charset="utf-8"><title>Pyrragi frontend not built</title></head>
        <body style="font-family:sans-serif;background:#34353B;color:#DDD;text-align:center;padding:40px">
          <h1>Pyrragi Vue frontend is not built yet.</h1>
          <p>Run <code>make frontend-dev</code> for local Vue development, or <code>make frontend-build</code> to build the SPA.</p>
        </body>
        </html>
        """,
        status_code=200,
    )
