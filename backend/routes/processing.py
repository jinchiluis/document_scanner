from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from config import get_image_processing_config, update_image_processing_config


router = APIRouter()


@router.post("/configure-processing")
async def configure_processing(req: Request):
    try:
        config = await req.json()
        updated = update_image_processing_config(config)
        return JSONResponse({"status": "updated", "config": updated})
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@router.get("/processing-config")
async def processing_config():
    return JSONResponse(get_image_processing_config())
