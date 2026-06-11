from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config import get_image_processing_config
from storage import folder_status, list_document_files, scan_folder


router = APIRouter()


@router.get("/api/folder/status")
async def get_folder_status():
    return JSONResponse(folder_status())


@router.get("/api/folder/files")
async def get_folder_files(limit: int | None = None):
    return JSONResponse({"files": list_document_files(limit=limit)})


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "scan_folder": str(scan_folder()),
        "processing_enabled": True,
        "processing_config": get_image_processing_config(),
    }
