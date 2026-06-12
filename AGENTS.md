# AGENTS.md

Guidance for coding agents working in this repository.

## Project

This is a local, single-user **Invoice Helper** for collecting invoice and receipt documents into one folder. It has two browser surfaces over one backend:

- **Phone scanner** at `/scan`: camera capture, OpenCV cleanup, save as images or PDF.
- **Desktop controller** at `/desktop`: active folder management, invoice download jobs, and links to external finance tools.

The app runs on the user's Windows PC. There is no auth, no multi-tenancy, and no database; state lives in the filesystem plus JSON config files.

## Stack

- Backend: **FastAPI + uvicorn**, not Flask.
- Image processing: **OpenCV**, **Pillow**, **reportlab**.
- Browser jobs: **Playwright Chromium**.
- Outlook jobs: **pywin32 COM**, Windows Outlook desktop profile required.
- Python 3.10+ syntax is used.

## Running

Run commands from the repository root with PowerShell:

```powershell
pip install -r requirements.txt
python -m playwright install chromium
python backend\generate_cert.py
python backend\server.py
```

Or use `Start Document Scanner.bat`.

With `cert.pem` and `key.pem`, the app serves HTTP on port `8000` and HTTPS on port `8443`. Without certs, it serves HTTP only on port `8000`.

## Repository Layout

```text
backend/
  server.py            # app factory and HTTP/HTTPS startup
  config.py            # JSON config defaults and merge
  storage.py           # active folder, scan folder, source folders
  image_processor.py   # OpenCV processing pipeline
  routes/              # API and page routes
  jobs/                # Outlook, Wix, Dropbox invoice jobs
frontend/
  scan/                # phone scanner UI
  desktop/             # desktop controller UI
```

## Conventions

- Use FastAPI route patterns: `APIRouter`, `async def`, `await req.json()`, and `JSONResponse`.
- Wrap blocking jobs with `starlette.concurrency.run_in_threadpool`.
- API responses should include a `"status"` field and return JSON errors instead of uncaught exceptions.
- Read config fresh through `load_config()`; do not cache config globally.
- Add new config defaults to `DEFAULT_CONFIG` so old config files keep working.
- Use `storage.py` helpers for paths instead of building active folder paths manually.
- Desktop nav sections use `id="page-<name>"` and sidebar links with matching `data-page`.

## Important Constraints

- Use PowerShell on Windows. Do not rely on Bash or WSL behavior for this app.
- Do not commit ignored local state such as `backend/config.json`, `backend/job_state.json`, `backend/browser_profiles/`, `backend/browser_state/`, `*.pem`, or `.env`.
- The folder picker opens a native tkinter dialog on the server machine and needs a desktop session.
- The QR generator in `runtime.py` is intentionally dependency-free and has a fixed capacity limit.

## UI Checks

Do not open, inspect, or automate the UI unless the user explicitly asks for it or gives permission after being asked. If a UI check would be useful, ask first.

Non-UI checks such as syntax validation, tests, static analysis, and server health requests are fine when relevant.

## External Tools

The desktop Tools page links to the separate hosted finance app at `https://finanzapp.de-life.de` for German tax documents. Prefer maintaining those links over porting that external app into this repository.
