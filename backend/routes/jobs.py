import traceback

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from jobs.browser_invoices import download_browser_invoices
from jobs.outlook_attachments import download_outlook_pdf_attachments
from storage import save_job_summary


router = APIRouter(prefix="/api/jobs")


@router.post("/outlook/attachments")
async def outlook_attachments(req: Request):
    try:
        data = await req.json()
        result = await run_in_threadpool(
            download_outlook_pdf_attachments,
            data.get("date_from", ""),
            data.get("date_to", ""),
            bool(data.get("include_subfolders", True)),
        )
        save_job_summary("outlook", result)
        return JSONResponse({"status": "done", "result": result})
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(
            {
                "status": "error",
                "message": str(exc),
                "error_type": type(exc).__name__,
            },
            status_code=500,
        )


@router.post("/{source}/invoices")
async def browser_invoices(source: str, req: Request):
    try:
        data = await req.json()
        result = await run_in_threadpool(
            download_browser_invoices,
            source,
            data.get("date_from", ""),
            data.get("date_to", ""),
            bool(data.get("force_login", False)),
            bool(data.get("headless", False)),
            int(data.get("login_timeout_ms", 300000)),
        )
        save_job_summary(source, result)
        return JSONResponse({"status": "done", "result": result})
    except Exception as exc:
        traceback.print_exc()
        return JSONResponse(
            {
                "status": "error",
                "message": str(exc),
                "error_type": type(exc).__name__,
            },
            status_code=500,
        )
