from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from config import load_config, update_config
from storage import folder_status


router = APIRouter(prefix="/api/config")


@router.get("")
async def get_config():
    return JSONResponse(load_config())


@router.post("")
async def save_config(req: Request):
    try:
        updates = await req.json()
        config = update_config(updates)
        status = folder_status()
        return JSONResponse({"status": "saved", "config": config, "folder": status})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@router.post("/choose-folder")
async def choose_folder():
    try:
        config = load_config()
        selected = _open_folder_picker(config.get("active_folder") or "")

        if not selected:
            return JSONResponse({"status": "cancelled", "config": config})

        updated = update_config({"active_folder": selected})
        status = folder_status()
        return JSONResponse({"status": "saved", "config": updated, "folder": status})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


def _open_folder_picker(initial_dir: str) -> str:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(
            initialdir=initial_dir or None,
            mustexist=False,
            title="Choose invoice folder",
        )
    finally:
        root.destroy()

    return selected
