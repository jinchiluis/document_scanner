import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config import BACKEND_DIR, load_config


DOCUMENT_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
JOB_STATE_PATH = BACKEND_DIR / "job_state.json"


def active_folder(create: bool = False) -> Path:
    config = load_config()
    path = Path(config["active_folder"]).expanduser()
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def scan_folder(create: bool = False) -> Path:
    config = load_config()
    path = active_folder(create=create) / config["scan_subfolder"]
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def source_folder(source_name: str, create: bool = False) -> Path:
    config = load_config()
    sources = config.get("sources", {})
    source_config = sources.get(source_name, {})
    subfolder = source_config.get("subfolder", source_name)
    path = active_folder(create=create) / subfolder
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def save_scan_bytes(filename: str, content: bytes) -> Path:
    destination = scan_folder(create=True) / filename
    with destination.open("wb") as output_file:
        output_file.write(content)
    return destination


def _file_info(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "extension": path.suffix.lower(),
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }


def list_document_files(limit: int | None = None) -> list[dict[str, Any]]:
    folder = active_folder()
    if not folder.exists():
        return []
    files = [
        _file_info(path)
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in DOCUMENT_EXTENSIONS
    ]
    files.sort(key=lambda item: item["modified_at"], reverse=True)
    if limit is not None:
        return files[:limit]
    return files


def load_job_state() -> dict[str, Any]:
    if not JOB_STATE_PATH.exists():
        return {}

    try:
        with JOB_STATE_PATH.open("r", encoding="utf-8") as state_file:
            state = json.load(state_file)
    except Exception:
        return {}

    return state if isinstance(state, dict) else {}


def _job_summary(source: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": source,
        "date_from": result.get("date_from"),
        "date_to": result.get("date_to"),
        "downloaded_count": result.get("downloaded_count", 0),
        "error_count": result.get("error_count", 0),
        "output_dir": result.get("output_dir"),
        "manifest_path": result.get("manifest_path"),
        "inspected_rows": result.get("inspected_rows"),
        "inspected_messages": result.get("inspected_messages"),
        "skipped_non_pdf": result.get("skipped_non_pdf"),
        "skipped_excluded_sender": result.get("skipped_excluded_sender"),
        "skipped_outside_date_range": result.get("skipped_outside_date_range"),
        "subscriptions_count": len(result.get("subscriptions") or []),
        "next_invoice": result.get("next_invoice"),
        "completed_at": datetime.now().isoformat(timespec="seconds"),
    }


def save_job_summary(source: str, result: dict[str, Any]) -> dict[str, Any]:
    state = load_job_state()
    state[source] = _job_summary(source, result)
    JOB_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with JOB_STATE_PATH.open("w", encoding="utf-8") as state_file:
        json.dump(state, state_file, indent=2, ensure_ascii=False)
        state_file.write("\n")
    return state[source]


def folder_status() -> dict[str, Any]:
    folder = active_folder()
    scans = scan_folder()
    files = list_document_files()
    scan_files = [
        _file_info(path)
        for path in (scans.iterdir() if scans.exists() else [])
        if path.is_file() and path.suffix.lower() in DOCUMENT_EXTENSIONS
    ]
    scan_files.sort(key=lambda item: item["modified_at"], reverse=True)

    return {
        "active_folder": str(folder),
        "scan_folder": str(scans),
        "document_count": len(files),
        "scan_count": len(scan_files),
        "job_state": load_job_state(),
        "recent_files": files,
        "recent_scans": scan_files,
    }
