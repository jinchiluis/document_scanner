import asyncio
import threading
import webbrowser

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import BACKEND_DIR, FRONTEND_DIR, get_image_processing_config
from routes import folder, jobs, pages, processing, runtime, scanner, settings


def _install_windows_connection_reset_filter() -> None:
    loop = asyncio.get_running_loop()
    default_handler = loop.get_exception_handler()

    def handle_exception(loop: asyncio.AbstractEventLoop, context: dict) -> None:
        exception = context.get("exception")
        handle = str(context.get("handle", ""))
        if (
            isinstance(exception, ConnectionResetError)
            and getattr(exception, "winerror", None) == 10054
            and "_ProactorBasePipeTransport._call_connection_lost" in handle
        ):
            return

        if default_handler is not None:
            default_handler(loop, context)
        else:
            loop.default_exception_handler(context)

    loop.set_exception_handler(handle_exception)


def create_app() -> FastAPI:
    app = FastAPI(title="Invoice Helper")

    @app.on_event("startup")
    async def install_asyncio_exception_filter() -> None:
        _install_windows_connection_reset_filter()

    app.include_router(pages.router)
    app.include_router(scanner.router)
    app.include_router(processing.router)
    app.include_router(settings.router)
    app.include_router(folder.router)
    app.include_router(jobs.router)
    app.include_router(runtime.router)

    app.mount(
        "/scan-static",
        StaticFiles(directory=FRONTEND_DIR / "scan"),
        name="scan-static",
    )
    app.mount(
        "/desktop-static",
        StaticFiles(directory=FRONTEND_DIR / "desktop"),
        name="desktop-static",
    )

    return app


app = create_app()


def run_server() -> None:
    processing_config = get_image_processing_config()
    desktop_url = runtime.desktop_url()
    phone_url = runtime.phone_scan_url()

    print("")
    print("Starting Invoice Helper")
    print(f"Backend directory: {BACKEND_DIR}")
    print(f"Frontend directory: {FRONTEND_DIR}")
    print("OpenCV processing is enabled")
    print(f"  Auto-crop: {processing_config['auto_crop']}")
    print(f"  Enhancement: {processing_config['enhance']}")
    print(f"  Document type: {processing_config['doc_type']}")
    print(f"  Auto-rotate: {processing_config['auto_rotate_enabled']}")

    cert_path = BACKEND_DIR / "cert.pem"
    key_path = BACKEND_DIR / "key.pem"

    if cert_path.exists() and key_path.exists():
        print("")
        print("SSL certificates found.")
        print(f"Desktop controller: {desktop_url}")
        print(f"Phone scanner: {phone_url}")
        print("Desktop runs over plain HTTP to avoid localhost certificate warnings.")
        print("The phone scanner still uses HTTPS because mobile camera access usually requires it.")
        _open_browser_later(desktop_url)
        threading.Thread(
            target=lambda: uvicorn.run(
                app,
                host="0.0.0.0",
                port=8443,
                ssl_keyfile=str(key_path),
                ssl_certfile=str(cert_path),
                log_level="info",
            ),
            daemon=True,
        ).start()
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
        )
        return

    print("")
    print("No SSL certificates found.")
    print("Phone camera access usually requires HTTPS on mobile browsers.")
    print("Run: python backend\\generate_cert.py")
    print(f"Desktop controller: {desktop_url}")
    print(f"Phone scanner: {phone_url}")
    _open_browser_later(desktop_url)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


def _open_browser_later(url: str) -> None:
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()


if __name__ == "__main__":
    run_server()
