import json
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from config import BACKEND_DIR
from storage import source_folder


PDF_EXTENSION = ".pdf"
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

BROWSER_STATE_DIR = BACKEND_DIR / "browser_state"
MAX_PLAYWRIGHT = 1
DEFAULT_LOGIN_TIMEOUT_MS = 5 * 60 * 1000
_playwright_sem = threading.BoundedSemaphore(MAX_PLAYWRIGHT)


@dataclass(frozen=True)
class InvoiceProvider:
    source: str
    start_url: str
    state_file: str
    email_env: str
    password_env: str
    login: Callable[[Any, str, str], None]
    collect: Callable[[Any, date, date, Path], dict[str, Any]]
    login_check: Callable[[Any], bool] | None = None


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format") from exc


def _safe_filename(filename: str) -> str:
    name = INVALID_FILENAME_CHARS.sub("_", filename).strip().strip(".")
    return name or "invoice.pdf"


def unique_path(folder: Path, filename: str) -> Path:
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


def click_first(page: Any, selectors: list[str], timeout: int = 2500) -> bool:
    for selector in selectors:
        try:
            page.locator(selector).first.click(timeout=timeout)
            return True
        except Exception:
            continue
    return False


def fill_first(page: Any, selectors: list[str], value: str, timeout: int = 60000) -> str:
    for selector in selectors:
        try:
            page.wait_for_selector(selector, timeout=timeout)
            page.fill(selector, value)
            return selector
        except Exception:
            continue
    raise RuntimeError(f"Could not find input field matching: {selectors}")


def accept_common_consent(page: Any) -> None:
    click_first(
        page,
        [
            "button:has-text('Accept all')",
            "button:has-text('Accept All')",
            "button:has-text('Alle akzeptieren')",
            "button:has-text('Zustimmen')",
            "button:has-text('I agree')",
            "[data-testid='uc-accept-all-button']",
            "#onetrust-accept-btn-handler",
        ],
    )


def save_download(download: Any, output_dir: Path, suggested_name: str | None = None) -> dict[str, Any]:
    filename = suggested_name or download.suggested_filename or "invoice.pdf"
    if Path(filename).suffix.lower() != PDF_EXTENSION:
        filename = f"{Path(filename).stem}.pdf"
    destination = unique_path(output_dir, filename)
    download.save_as(str(destination))
    return {
        "filename": destination.name,
        "path": str(destination),
        "suggested_filename": download.suggested_filename,
        "size": destination.stat().st_size,
    }


def _load_provider(source: str) -> InvoiceProvider:
    if source == "wix":
        from jobs.wix_invoices import PROVIDER

        return PROVIDER
    if source == "dropbox":
        from jobs.dropbox_invoices import PROVIDER

        return PROVIDER
    raise ValueError("source must be one of: wix, dropbox")


def _state_path(provider: InvoiceProvider) -> Path:
    return BROWSER_STATE_DIR / provider.state_file


def _new_context(browser: Any, state_path: Path | None = None):
    kwargs: dict[str, Any] = {
        "accept_downloads": True,
        "user_agent": UA,
        "viewport": {"width": 1366, "height": 850},
    }
    if state_path and state_path.exists():
        kwargs["storage_state"] = str(state_path)
    return browser.new_context(**kwargs)


def _launch_chromium(p: Any, headless: bool):
    launch_kwargs = {
        "headless": headless,
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    channel = os.environ.get("PLAYWRIGHT_BROWSER_CHANNEL", "").strip()
    if channel:
        return p.chromium.launch(channel=channel, **launch_kwargs)

    try:
        return p.chromium.launch(**launch_kwargs)
    except Exception as bundled_error:
        last_error = bundled_error
        for fallback_channel in ("chrome", "msedge"):
            try:
                return p.chromium.launch(channel=fallback_channel, **launch_kwargs)
            except Exception as exc:
                last_error = exc
        raise last_error from bundled_error


def _wait_for_login_completion(provider: InvoiceProvider, page: Any, timeout_ms: int) -> None:
    deadline = time.monotonic() + (timeout_ms / 1000)
    last_url = ""
    print("")
    print(f"{provider.source}: finish any 2FA/login challenge in the browser window.")
    print(f"{provider.source}: waiting up to {timeout_ms // 1000} seconds before saving session state.")

    while time.monotonic() < deadline:
        try:
            accept_common_consent(page)
            last_url = page.url
            if provider.login_check and provider.login_check(page):
                return
            if not provider.login_check and provider.start_url.split("/", 3)[2] in page.url:
                return
        except Exception:
            pass
        page.wait_for_timeout(2000)

    raise RuntimeError(
        f"{provider.source} login did not complete within {timeout_ms // 1000} seconds. "
        f"Last browser URL: {last_url or 'unknown'}"
    )


def _ensure_login(
    p: Any,
    provider: InvoiceProvider,
    state_path: Path,
    headless: bool,
    login_timeout_ms: int,
) -> None:
    email = os.environ.get(provider.email_env, "")
    password = os.environ.get(provider.password_env, "")
    if not email or not password:
        raise RuntimeError(
            f"Missing credentials. Set {provider.email_env} and {provider.password_env} in the server environment."
        )

    browser = _launch_chromium(p, headless=headless)
    try:
        ctx = _new_context(browser)
        page = ctx.new_page()
        provider.login(page, email, password)
        _wait_for_login_completion(provider, page, login_timeout_ms)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        ctx.storage_state(path=str(state_path))
        ctx.close()
    finally:
        browser.close()


def download_browser_invoices(
    source: str,
    date_from: str,
    date_to: str,
    force_login: bool = False,
    headless: bool = False,
    login_timeout_ms: int = DEFAULT_LOGIN_TIMEOUT_MS,
) -> dict[str, Any]:
    provider = _load_provider(source)
    start_date = _parse_date(date_from, "date_from")
    end_date = _parse_date(date_to, "date_to")
    if end_date < start_date:
        raise ValueError("date_to must be on or after date_from")

    output_dir = source_folder(provider.source) / f"{date_from}_to_{date_to}"
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = _state_path(provider)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Browser invoice jobs require Playwright. Install with: pip install -r requirements.txt "
            "and then run: python -m playwright install chromium"
        ) from exc

    with _playwright_sem:
        with sync_playwright() as p:
            if force_login or not state_path.exists():
                _ensure_login(
                    p,
                    provider,
                    state_path,
                    headless=headless,
                    login_timeout_ms=login_timeout_ms,
                )

            browser = _launch_chromium(p, headless=headless)
            try:
                ctx = _new_context(browser, state_path)
                page = ctx.new_page()
                page.goto(provider.start_url, wait_until="domcontentloaded", timeout=60000)
                accept_common_consent(page)
                if provider.login_check and not provider.login_check(page):
                    ctx.close()
                    browser.close()
                    _ensure_login(
                        p,
                        provider,
                        state_path,
                        headless=headless,
                        login_timeout_ms=login_timeout_ms,
                    )
                    browser = _launch_chromium(p, headless=headless)
                    ctx = _new_context(browser, state_path)
                    page = ctx.new_page()
                    page.goto(provider.start_url, wait_until="domcontentloaded", timeout=60000)
                    accept_common_consent(page)

                result = provider.collect(page, start_date, end_date, output_dir)
                try:
                    ctx.storage_state(path=str(state_path))
                except Exception:
                    pass
                ctx.close()
            finally:
                browser.close()

    downloaded = result.get("downloaded", [])
    errors = result.get("errors", [])
    manifest = {
        "source": provider.source,
        "attachment_type": "pdf",
        "date_from": date_from,
        "date_to": date_to,
        "output_dir": str(output_dir),
        "state_path": str(state_path),
        "downloaded_count": len(downloaded),
        "error_count": len(errors),
        **result,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, indent=2, ensure_ascii=False)
        manifest_file.write("\n")

    manifest["manifest_path"] = str(manifest_path)
    return manifest
