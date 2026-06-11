# Invoice Helper

A local **FastAPI** app for collecting a quarter's worth of invoices and
receipts into a single folder. It runs on your own Windows PC — no account, no
cloud, no database. State lives in the active folder plus a small JSON config.

Two surfaces share one backend:

- **Phone scanner** (`/scan`) — capture documents with your phone camera. Images
  are cleaned up with OpenCV (auto-rotate, auto-crop, enhance) and saved as
  images or a multi-page PDF.
- **Desktop controller** (`/desktop`) — manage the active quarter folder, run
  the invoice-download jobs, and jump to the external finance tools.

## Structure

```text
backend/
  server.py            # app startup (dual HTTP/HTTPS)
  config.py            # JSON config loading/saving
  storage.py           # active folder, scan folder, source folders, file listing
  image_processor.py   # OpenCV processing pipeline
  generate_cert.py     # self-signed certificate helper
  routes/              # pages, scanner, processing, settings, folder, jobs, runtime
  jobs/                # Outlook (COM) + Wix/Dropbox (Playwright) download jobs
frontend/
  scan/                # phone scanner UI
  desktop/             # desktop controller UI
```

## Running

Install dependencies:

```powershell
pip install -r requirements.txt
```

(Optional, only for the Wix/Dropbox jobs) install the Playwright browser:

```powershell
python -m playwright install chromium
```

(Optional) generate a self-signed certificate so phone camera access works over
HTTPS:

```powershell
python backend\generate_cert.py
```

Start the server **from the repository root**:

```powershell
python backend\server.py
```

(or double-click `Start Document Scanner.bat`)

With certificates present the app serves both HTTP and HTTPS at once:

```text
http://localhost:8000/desktop        # desktop controller (plain HTTP, no cert warning)
https://YOUR_COMPUTER_IP:8443/scan   # phone scanner (HTTPS, needed for camera)
```

Without certificates it falls back to HTTP only:

```text
http://localhost:8000/desktop
http://YOUR_COMPUTER_IP:8000/scan
```

The desktop page shows a QR code for the phone scanner URL so you can open it on
your phone quickly.

The editable local config is stored in `backend/config.json` (ignored by Git).
Scans are saved to `active_folder/scan_subfolder`. The active folder is chosen
from the desktop controller via a native folder picker.

## Image processing

Every scan runs through an OpenCV pipeline before saving. Settings live under
`image_processing` in the config and are editable at runtime:

- **auto_crop** — detect the document's edges and flatten to a top-down view.
- **auto_rotate** — correct small skew angles.
- **enhance** — contrast/sharpen (`mixed`/`photo`) or adaptive threshold
  (`text`), selected by **doc_type**.

## Invoice download jobs

The desktop controller's **Invoice Sources** page runs jobs that collect PDFs
for a chosen date range into `active_folder/<source>/<range>/`, each with a
`manifest.json`.

- **Outlook Attachments** — reads your local Outlook desktop profile through
  Windows COM (Outlook must be installed and configured), scanning Inbox (and
  optionally subfolders) for PDF attachments. Duplicate filenames are renamed
  (`invoice.pdf`, `invoice_2.pdf`, ...).
- **Wix Invoices** / **Dropbox Invoices** — browser automation via Playwright.
  Credentials are read from environment variables (a local `.env` file works),
  and a dedicated persistent browser profile is cached under
  `backend/browser_profiles/` so 2FA isn't needed every run. Use the "Force
  login" option to redo the interactive login.

## Tools

The desktop **Tools** page links out to the hosted finance app at
`https://finanzapp.de-life.de` for German tax documents — **Bewirtungsbeleg**
(hospitality receipts) and **Reisekosten** (travel expenses). Scan a receipt
here, then open the matching tool to build the proof. These are plain links;
that app is maintained separately.

## Notes

- Windows-only in practice: the Outlook job, the folder picker, and the
  Playwright browsers are native to the host. Run it with PowerShell.
- Local state ignored by Git: `backend/config.json`, `backend/saved_docs/`,
  `backend/browser_state/`, `backend/browser_profiles/`,
  `backend/job_state.json`, `*.pem`, and `.env`.
