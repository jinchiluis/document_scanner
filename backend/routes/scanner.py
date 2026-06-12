import base64
import io
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from config import get_image_processing_config
from image_processor import process_document_image
from storage import save_scan_bytes, scan_folder


router = APIRouter()

PDF_IMAGE_MAX_DIMENSION = 1800
PDF_IMAGE_JPEG_QUALITY = 85
PAGE_IMAGE_MAX_DIMENSION = 2400
PAGE_IMAGE_JPEG_QUALITY = 92


def _decode_data_url(data_url: str) -> bytes:
    return base64.b64decode(data_url.split(",", 1)[1])


def _process_pages(pages: list[str], cropped_flags: list[bool]) -> list[str]:
    """Process scanned pages, skipping auto-crop for pages the phone already
    perspective-cropped (re-cropping a clean scan risks cutting into content)."""
    config = get_image_processing_config()
    processed = []
    for index, page in enumerate(pages):
        page_config = dict(config)
        if index < len(cropped_flags) and cropped_flags[index]:
            page_config["auto_crop"] = False
        processed.append(process_document_image(page, **page_config))
    return processed


def _prepare_pdf_image(page_data: str):
    img = Image.open(io.BytesIO(_decode_data_url(page_data))).convert("RGB")
    img.thumbnail(
        (PDF_IMAGE_MAX_DIMENSION, PDF_IMAGE_MAX_DIMENSION),
        Image.Resampling.LANCZOS,
    )

    compressed = io.BytesIO()
    img.save(
        compressed,
        format="JPEG",
        quality=PDF_IMAGE_JPEG_QUALITY,
        optimize=True,
        progressive=True,
    )
    compressed.seek(0)
    return ImageReader(compressed), img.size


@router.post("/save-image")
async def save_image(req: Request):
    try:
        data = await req.json()
        img_data = data["image"]
        processed_img_data = process_document_image(
            img_data,
            **get_image_processing_config(),
        )

        img_bytes = _decode_data_url(processed_img_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = save_scan_bytes(f"doc_{timestamp}.png", img_bytes)

        return JSONResponse(
            {
                "status": "saved",
                "file": str(filename),
                "timestamp": timestamp,
                "processed": True,
            }
        )
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@router.post("/save-pdf")
async def save_pdf(req: Request):
    try:
        data = await req.json()
        pages = data.get("pages", [])

        if not pages:
            return JSONResponse(
                {"status": "error", "message": "No pages provided"},
                status_code=400,
            )

        processed_pages = _process_pages(pages, data.get("cropped", []))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = scan_folder(create=True) / f"doc_{timestamp}.pdf"

        pdf = canvas.Canvas(str(pdf_filename), pagesize=A4)
        page_width, page_height = A4

        for index, page_data in enumerate(processed_pages):
            img_reader, (img_width, img_height) = _prepare_pdf_image(page_data)
            aspect = img_height / float(img_width)
            margin = 50
            available_width = page_width - (2 * margin)
            available_height = page_height - (2 * margin)

            if img_width > img_height:
                new_width = available_width
                new_height = new_width * aspect
                if new_height > available_height:
                    new_height = available_height
                    new_width = new_height / aspect
            else:
                new_height = available_height
                new_width = new_height / aspect
                if new_width > available_width:
                    new_width = available_width
                    new_height = new_width * aspect

            x = (page_width - new_width) / 2
            y = (page_height - new_height) / 2

            pdf.drawImage(img_reader, x, y, width=new_width, height=new_height)

            if index < len(processed_pages) - 1:
                pdf.showPage()

        pdf.save()

        return JSONResponse(
            {
                "status": "saved",
                "file": str(pdf_filename),
                "pages": len(processed_pages),
                "timestamp": timestamp,
                "processed": True,
                "compression": {
                    "max_dimension": PDF_IMAGE_MAX_DIMENSION,
                    "jpeg_quality": PDF_IMAGE_JPEG_QUALITY,
                },
            }
        )
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


@router.post("/save-pages")
async def save_pages(req: Request):
    try:
        data = await req.json()
        pages = data.get("pages", [])

        if not pages:
            return JSONResponse(
                {"status": "error", "message": "No pages provided"},
                status_code=400,
            )

        processed_pages = _process_pages(pages, data.get("cropped", []))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = []

        for index, page_data in enumerate(processed_pages, start=1):
            image = Image.open(io.BytesIO(_decode_data_url(page_data))).convert("RGB")
            image.thumbnail(
                (PAGE_IMAGE_MAX_DIMENSION, PAGE_IMAGE_MAX_DIMENSION),
                Image.Resampling.LANCZOS,
            )
            output = io.BytesIO()
            image.save(
                output,
                format="JPEG",
                quality=PAGE_IMAGE_JPEG_QUALITY,
                optimize=True,
                progressive=True,
            )
            filename = save_scan_bytes(f"doc_{timestamp}_page_{index:02d}.jpg", output.getvalue())
            saved_files.append(str(filename))

        return JSONResponse(
            {
                "status": "saved",
                "files": saved_files,
                "pages": len(saved_files),
                "timestamp": timestamp,
                "processed": True,
                "compression": {
                    "format": "jpeg",
                    "max_dimension": PAGE_IMAGE_MAX_DIMENSION,
                    "jpeg_quality": PAGE_IMAGE_JPEG_QUALITY,
                },
            }
        )
    except Exception as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)
