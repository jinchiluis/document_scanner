# Invoice Helper

Local FastAPI app for collecting quarterly invoice documents. The phone page is
only for scanning. The desktop page is the controller for the active quarter
folder and future automation addons.

## Structure

```text
backend/
  server.py              # app startup
  config.py              # JSON config loading/saving
  storage.py             # active folder and scan folder paths
  image_processor.py     # OpenCV processing
  routes/                # page, scanner, config, folder, processing APIs
  jobs/                  # future email/Wix/Dropbox automation modules
frontend/
  scan/                  # phone scanner UI
  desktop/               # desktop controller UI
```

## Running

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate a self-signed certificate for phone camera access:

```bash
python backend/generate_cert.py
```

Start the server from the repository root:

```bash
python backend/server.py
```

If certificates are present, the app runs at:

```text
https://localhost:8443/desktop
https://YOUR_COMPUTER_IP:8443/scan
```

Without certificates it falls back to:

```text
http://localhost:8000/desktop
http://localhost:8000/scan
```

The editable local config is stored in `backend/config.json` and is ignored by
Git. Scans are saved to `active_folder/scan_subfolder`.

## Outlook Addon

The desktop controller includes an Outlook PDF attachment downloader. It uses
the local Outlook desktop profile through Windows COM, so Outlook must be
installed and configured on the PC.

The addon scans Inbox messages in the selected date range, optionally including
Inbox subfolders, and saves PDF attachments only:

```text
active_folder/email/YYYY-MM-DD_to_YYYY-MM-DD/
```

Duplicate filenames are renamed automatically, for example `invoice.pdf`,
`invoice_2.pdf`, `invoice_3.pdf`. A `manifest.json` is written next to the
downloaded PDFs with sender, subject, received date, and saved path metadata.
