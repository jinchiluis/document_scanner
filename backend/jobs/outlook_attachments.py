import json
import os
import re
import time as time_module
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from storage import source_folder


PDF_EXTENSION = ".pdf"
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
OL_FOLDER_INBOX = 6
EXCLUDED_SENDER_CONTAINS = [
    "@apodiscounter.de",
    "@emotion.mvv.de",
    "schwimmverein-ilvesheim@gmx.de",
    "@payback.de",
    "@retail.mercedes-benz.com",
    "accounting@phorms.de",
    "@kundenservice.vodafone.com",
    "@notifications.nike.com",
    "@enbw.com",
    "@hischool.de",
    "@kaufland-marktplatz.de",
    "shopifyemail.com",
    "@gebuhrenfrei.com",
    "@koelnmesse.de",
]
ZONE_IDENTIFIER_STREAM = "Zone.Identifier"


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format") from exc


def _safe_filename(filename: str) -> str:
    name = INVALID_FILENAME_CHARS.sub("_", filename).strip().strip(".")
    return name or "attachment.pdf"


def _unique_path(folder: Path, filename: str) -> Path:
    safe_name = _safe_filename(filename)
    candidate = folder / safe_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        renamed = folder / f"{stem}_{counter}{suffix}"
        if not renamed.exists():
            return renamed
        counter += 1


def _remove_zone_identifier(path: Path) -> dict[str, Any]:
    """Remove Mark-of-the-Web so Windows Explorer can preview downloaded PDFs."""
    if os.name != "nt":
        return {"attempted": False, "removed": False}

    try:
        Path(f"{path}:{ZONE_IDENTIFIER_STREAM}").unlink()
        return {"attempted": True, "removed": True}
    except FileNotFoundError:
        return {"attempted": True, "removed": False}
    except OSError as exc:
        return {"attempted": True, "removed": False, "error": str(exc)}


def _to_iso(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _received_datetime(item) -> datetime | None:
    value = getattr(item, "ReceivedTime", None)
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.replace(tzinfo=None)

    if hasattr(value, "Format"):
        try:
            return datetime.strptime(value.Format("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    if hasattr(value, "timestamp"):
        try:
            return datetime.fromtimestamp(value.timestamp()).replace(tzinfo=None)
        except Exception:
            pass

    return None


def _is_excluded_sender(sender_email: str, sender_name: str) -> bool:
    sender_text = f"{sender_email} {sender_name}".lower()
    return any(excluded in sender_text for excluded in EXCLUDED_SENDER_CONTAINS)


def _iter_folders(folder, include_subfolders: bool):
    yield folder
    if not include_subfolders:
        return

    try:
        folder_count = folder.Folders.Count
    except Exception:
        return

    for index in range(1, folder_count + 1):
        try:
            child = folder.Folders.Item(index)
        except Exception:
            continue
        yield from _iter_folders(child, include_subfolders=True)


def _get_outlook_namespace():
    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(
            "Outlook addon requires pywin32. Install dependencies with: pip install -r requirements.txt"
        ) from exc

    try:
        outlook = win32com.client.GetActiveObject("Outlook.Application")
        return outlook.GetNamespace("MAPI")
    except Exception as active_error:
        last_error = active_error

    for _ in range(3):
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            return outlook.GetNamespace("MAPI")
        except Exception as exc:
            last_error = exc
            time_module.sleep(1)

    raise RuntimeError(
        "Could not connect to Outlook via COM. Make sure classic Outlook is running "
        f"and configured for this Windows user. Last error: {last_error}"
    )


def _scan_folder(folder, date_from: datetime, date_to_exclusive: datetime, output_dir: Path):
    folder_name = str(getattr(folder, "FolderPath", "") or getattr(folder, "Name", ""))
    errors: list[dict[str, str]] = []
    try:
        items = folder.Items
        items.Sort("[ReceivedTime]", True)
    except Exception as exc:
        return {
            "downloaded": [],
            "inspected_messages": 0,
            "skipped_non_pdf": 0,
            "errors": [{"folder": folder_name, "message": str(exc)}],
        }

    downloaded: list[dict[str, Any]] = []
    inspected_messages = 0
    skipped_non_pdf = 0
    skipped_excluded_sender = 0
    skipped_outside_date_range = 0

    for item in items:
        try:
            received_at = _received_datetime(item)
            if received_at is None:
                continue

            if received_at >= date_to_exclusive:
                skipped_outside_date_range += 1
                continue

            if received_at < date_from:
                break

            attachments = getattr(item, "Attachments", None)
            if attachments is None:
                continue

            sender_email = str(getattr(item, "SenderEmailAddress", "") or "")
            sender_name = str(getattr(item, "SenderName", "") or "")
            if _is_excluded_sender(sender_email, sender_name):
                skipped_excluded_sender += 1
                continue

            inspected_messages += 1
            for index in range(1, attachments.Count + 1):
                attachment = attachments.Item(index)
                original_name = str(getattr(attachment, "FileName", "") or "attachment")
                if Path(original_name).suffix.lower() != PDF_EXTENSION:
                    skipped_non_pdf += 1
                    continue

                destination = _unique_path(output_dir, original_name)
                attachment.SaveAsFile(str(destination))
                zone_identifier = _remove_zone_identifier(destination)
                downloaded_item = {
                    "filename": destination.name,
                    "original_filename": original_name,
                    "path": str(destination),
                    "sender": sender_email,
                    "sender_name": sender_name,
                    "subject": str(getattr(item, "Subject", "") or ""),
                    "received_at": _to_iso(received_at),
                    "folder": folder_name,
                    "zone_identifier_removed": zone_identifier["removed"],
                }
                if "error" in zone_identifier:
                    downloaded_item["zone_identifier_error"] = zone_identifier["error"]
                downloaded.append(downloaded_item)
        except Exception as exc:
            errors.append(
                {
                    "folder": folder_name,
                    "subject": str(getattr(item, "Subject", "") or ""),
                    "message": str(exc),
                }
            )

    return {
        "downloaded": downloaded,
        "inspected_messages": inspected_messages,
        "skipped_non_pdf": skipped_non_pdf,
        "skipped_excluded_sender": skipped_excluded_sender,
        "skipped_outside_date_range": skipped_outside_date_range,
        "errors": errors,
    }


def download_outlook_pdf_attachments(
    date_from: str,
    date_to: str,
    include_subfolders: bool = True,
) -> dict[str, Any]:
    try:
        import pythoncom
    except ImportError as exc:
        raise RuntimeError(
            "Outlook addon requires pywin32. Install dependencies with: pip install -r requirements.txt"
        ) from exc

    start_date = _parse_date(date_from, "date_from")
    end_date = _parse_date(date_to, "date_to")
    if end_date < start_date:
        raise ValueError("date_to must be on or after date_from")

    start_dt = datetime.combine(start_date, time.min)
    end_exclusive_dt = datetime.combine(end_date + timedelta(days=1), time.min)

    output_dir = source_folder("email") / f"{date_from}_to_{date_to}"
    output_dir.mkdir(parents=True, exist_ok=True)

    pythoncom.CoInitialize()
    try:
        namespace = _get_outlook_namespace()
        inbox = namespace.GetDefaultFolder(OL_FOLDER_INBOX)

        downloaded: list[dict[str, Any]] = []
        inspected_messages = 0
        skipped_non_pdf = 0
        skipped_excluded_sender = 0
        skipped_outside_date_range = 0
        inspected_folders = []
        errors = []

        for folder in _iter_folders(inbox, include_subfolders=include_subfolders):
            inspected_folders.append(str(getattr(folder, "FolderPath", "") or getattr(folder, "Name", "")))
            folder_result = _scan_folder(folder, start_dt, end_exclusive_dt, output_dir)
            downloaded.extend(folder_result["downloaded"])
            inspected_messages += folder_result["inspected_messages"]
            skipped_non_pdf += folder_result["skipped_non_pdf"]
            skipped_excluded_sender += folder_result["skipped_excluded_sender"]
            skipped_outside_date_range += folder_result["skipped_outside_date_range"]
            errors.extend(folder_result["errors"])
    finally:
        pythoncom.CoUninitialize()

    manifest = {
        "source": "outlook",
        "attachment_type": "pdf",
        "date_from": date_from,
        "date_to": date_to,
        "include_subfolders": include_subfolders,
        "output_dir": str(output_dir),
        "inspected_folders": inspected_folders,
        "inspected_messages": inspected_messages,
        "downloaded_count": len(downloaded),
        "date_filter_mode": "python_received_time",
        "skipped_non_pdf": skipped_non_pdf,
        "skipped_excluded_sender": skipped_excluded_sender,
        "skipped_outside_date_range": skipped_outside_date_range,
        "excluded_sender_contains": EXCLUDED_SENDER_CONTAINS,
        "error_count": len(errors),
        "errors": errors,
        "downloaded": downloaded,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, indent=2, ensure_ascii=False)
        manifest_file.write("\n")

    manifest["manifest_path"] = str(manifest_path)
    return manifest
