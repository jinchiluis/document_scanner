from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response

from config import FRONTEND_DIR


router = APIRouter()


def _page_response(path):
    if not path.exists():
        return HTMLResponse(f"<h1>Missing page</h1><p>{path}</p>", status_code=404)
    return FileResponse(path)


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    path = FRONTEND_DIR / "favicon.ico"
    if not path.exists():
        return Response(status_code=204)
    return FileResponse(path, media_type="image/x-icon")


@router.get("/")
async def root():
    return RedirectResponse("/scan")


@router.get("/scan")
async def scan_page():
    return _page_response(FRONTEND_DIR / "scan" / "index.html")


@router.get("/desktop")
async def desktop_page():
    return _page_response(FRONTEND_DIR / "desktop" / "index.html")
