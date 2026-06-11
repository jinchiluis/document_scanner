# CLAUDE.md

Guidance for Claude Code working in this repository.

## What this is

A local, single-user **Invoice Helper** for collecting a quarter's worth of
invoice/receipt documents into one folder. Two surfaces share one backend:

- **Phone scanner** (`/scan`) — camera capture, sent to the backend for OpenCV
  cleanup and saved as image or PDF.
- **Desktop controller** (`/desktop`) — manages the active quarter folder, runs
  the invoice-download jobs, and links out to external finance tools.

It runs on the user's own Windows PC. There is no auth, no multi-tenancy, and
no database — state is the filesystem plus a couple of JSON files.

## Stack — important

- **FastAPI + uvicorn**, *not* Flask. Routes use `APIRouter`, `async def`,
  `await req.json()`, and return `JSONResponse`. Don't introduce Flask idioms.
- **OpenCV** (`opencv-python-headless`) for document processing, **reportlab**
  for PDF assembly, **Pillow** for image compression.
- **Playwright** (Chromium) for browser invoice jobs; **pywin32** COM for the
  Outlook job — both Windows-oriented and run on the host machine.
- Python 3.10+ (uses `X | None` unions, `list[...]` generics).

## Running

From the **repository root** (running the script puts `backend/` on
`sys.path`, which the bare `from config import ...` / `from routes import ...`
imports rely on):

```powershell
pip install -r requirements.txt
python -m playwright install chromium   # only needed for Wix/Dropbox jobs
python backend\generate_cert.py         # optional: enables HTTPS for phone camera
python backend\server.py
```

Or use `Start Document Scanner.bat`.

### Ports / URLs

- **With** `cert.pem` + `key.pem` present: HTTP on **8000** *and* HTTPS on
  **8443** run simultaneously (two `uvicorn.run` calls, one in a thread).
  Desktop opens over plain HTTP localhost (avoids cert warnings); the phone
  scanner uses HTTPS because mobile browsers require it for camera access.
- **Without** certs: HTTP only on **8000**.
- `/` redirects to `/scan`. Pages: `/scan`, `/desktop`. Static mounts:
  `/scan-static`, `/desktop-static`.

## Layout

```text
backend/
  server.py            # app factory + dual HTTP/HTTPS startup
  config.py            # JSON config: DEFAULT_CONFIG deep-merged over config.json
  storage.py           # active/scan/source folder paths, file listing, job_state
  image_processor.py   # OpenCV pipeline (rotate, crop, enhance)
  generate_cert.py     # self-signed cert helper
  routes/
    pages.py           # serves /scan and /desktop HTML, / -> /scan
    scanner.py         # /save-image, /save-pdf, /save-pages (reportlab/Pillow)
    processing.py      # get/update image-processing config
    settings.py        # /api/config + native tkinter folder picker
    folder.py          # /api/folder/status, /api/folder/files, /health
    jobs.py            # /api/jobs/outlook/attachments, /api/jobs/{source}/invoices
    runtime.py         # runtime URLs + hand-rolled QR SVG for the phone link
  jobs/
    outlook_attachments.py  # Outlook desktop via COM (Windows + Outlook required)
    browser_invoices.py     # shared Playwright driver
    wix_invoices.py         # Wix provider
    dropbox_invoices.py     # Dropbox provider
frontend/
  scan/                # phone scanner UI
  desktop/             # desktop controller UI (index.html / desktop.js / desktop.css)
```

## Conventions

- **Route handlers are `async`**; wrap blocking work (Playwright, Outlook COM,
  long jobs) in `starlette.concurrency.run_in_threadpool` — see `jobs.py`.
- API responses are JSON with a `"status"` field (`"saved"`, `"done"`,
  `"updated"`, `"error"`, ...). Catch exceptions and return them as a 500 with
  `{"status": "error", "message": ...}` rather than letting them bubble.
- Config is read fresh via `load_config()` each time; never cache it. New
  settings go in `DEFAULT_CONFIG` so the deep-merge supplies them for old
  config files.
- Filesystem paths come from `storage.py` helpers (`active_folder()`,
  `scan_folder()`, `source_folder(name)`) — they `mkdir(parents=True)` on
  demand. Don't build paths by hand in routes.
- The desktop nav (`desktop.js`) shows/hides `.content` sections by
  `id="page-<name>"` matching a sidebar link's `data-page`. To add a page, add
  a nav `<a data-page="x">` and a `<section class="content" id="page-x">`.

## Jobs and their requirements

- **Outlook** (`outlook/attachments`): uses the local Outlook profile through
  Windows COM. Outlook must be installed/configured. Saves PDF attachments only
  into `active_folder/email/<range>/` with a `manifest.json`. Has a hardcoded
  `EXCLUDED_SENDER_CONTAINS` list.
- **Wix / Dropbox** (`{source}/invoices`): Playwright Chromium. Credentials come
  from env vars (loaded from `.env`); persistent browser profiles are cached
  under `backend/browser_profiles/`, with `backend/browser_state/` kept as a
  storage-state export/migration fallback. A semaphore limits concurrency to one
  browser job. `force_login` re-runs the interactive 2FA login flow.

## External tools (not in this repo)

The desktop **Tools** page links out to a separate hosted Flask app at
`https://finanzapp.de-life.de` for German tax documents:
**Bewirtungsbeleg** (`/bewirtung/new`) and **Reisekosten** (`/travel/new`).
These are plain outbound links — intentionally *not* reimplemented here, to
avoid pulling in that app's HTML/paged.js + Playwright PDF stack and SQLite DB.
If asked to "add hospitality/travel features," prefer extending those links
over porting the code.

## Gotchas

- **Don't run via the Bash tool / WSL** — this is a Windows app (COM, native
  tkinter dialog, `.exe` browsers). Use PowerShell.
- `settings.py`'s folder picker opens a **native tkinter dialog on the server
  machine**; it blocks and only works where the server has a desktop session.
- Gitignored local state: `backend/config.json`, `backend/saved_docs/`,
  `backend/browser_state/`, `backend/browser_profiles/`,
  `backend/job_state.json`, `*.pem`, `.env`. Don't commit these or assume they
  exist on a fresh checkout.
- The QR generator in `runtime.py` is a self-contained encoder (fixed QR
  version 4) — it raises if the phone URL exceeds ~78 bytes. No qrcode dep.
