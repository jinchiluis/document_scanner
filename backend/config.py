import json
from copy import deepcopy
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
CONFIG_PATH = BACKEND_DIR / "config.json"
ENV_PATH = ROOT_DIR / ".env"


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(ENV_PATH)


load_env()

DEFAULT_CONFIG: dict[str, Any] = {
    "active_folder": str(BACKEND_DIR / "saved_docs"),
    "scan_subfolder": "scans",
    "image_processing": {
        "enhance": True,
        "doc_type": "mixed",
        "auto_crop": True,
        "auto_rotate_enabled": True,
    },
    "sources": {
        "scanner": {"enabled": True, "subfolder": "scans"},
        "email": {"enabled": False, "subfolder": "email"},
        "wix": {"enabled": False, "subfolder": "wix"},
        "dropbox": {"enabled": False, "subfolder": "dropbox"},
        "manual": {"enabled": True, "subfolder": "manual"},
    },
}


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return deepcopy(DEFAULT_CONFIG)

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        loaded = json.load(config_file)

    return _deep_merge(DEFAULT_CONFIG, loaded)


def save_config(config: dict[str, Any]) -> dict[str, Any]:
    merged = _deep_merge(DEFAULT_CONFIG, config)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        json.dump(merged, config_file, indent=2)
        config_file.write("\n")
    return merged


def update_config(updates: dict[str, Any]) -> dict[str, Any]:
    current = load_config()
    updated = _deep_merge(current, updates)
    return save_config(updated)


def get_image_processing_config() -> dict[str, Any]:
    return load_config()["image_processing"]


def update_image_processing_config(updates: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    image_processing = config["image_processing"]
    image_processing.update(updates)
    return save_config(config)["image_processing"]
