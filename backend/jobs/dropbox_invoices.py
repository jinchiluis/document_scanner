import base64
from datetime import date, datetime
from pathlib import Path
from typing import Any

from jobs.browser_invoices import (
    InvoiceProvider,
    accept_common_consent,
    click_first,
    fill_first,
)

START_URL = "https://www.dropbox.com/manage/billing"


def login(page: Any, email: str, password: str) -> None:
    # Dropbox uses a two-step flow: email → continue → password → sign in
    page.goto("https://www.dropbox.com/login", wait_until="domcontentloaded", timeout=60000)
    accept_common_consent(page)

    # Step 1: fill email and click continue
    fill_first(page, ["input[name='susi_email']"], email)
    click_first(page, ["button.email-submit-button", "button[type='submit']"], timeout=8000)

    # Step 2: wait for password field, fill it, submit
    page.wait_for_selector("input[name='login_password']", timeout=15000)
    fill_first(page, ["input[name='login_password']", "input[autocomplete='current-password']"], password)
    click_first(page, ["button[data-testid='login-form-submit-button']", "button[type='submit']"], timeout=8000)

    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass


def is_logged_in(page: Any) -> bool:
    return "/login" not in page.url


def _parse_dropbox_date(text: str) -> date | None:
    try:
        return datetime.strptime(text.strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


def _page_to_pdf(page: Any) -> bytes:
    """Print the current page to PDF via CDP (works headless and headful)."""
    cdp = page.context.new_cdp_session(page)
    result = cdp.send("Page.printToPDF", {
        "printBackground": True,
        "paperWidth": 8.27,
        "paperHeight": 11.69,
        "marginTop": 0.4,
        "marginBottom": 0.4,
        "marginLeft": 0.4,
        "marginRight": 0.4,
    })
    return base64.b64decode(result["data"])


def collect(page: Any, date_from: date, date_to: date, output_dir: Path) -> dict[str, Any]:
    downloaded: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    inspected_rows = 0

    # browser_invoices.py already navigated to START_URL before calling collect()
    page.wait_for_selector("button[data-testid='billing-history-more-menu-trigger-button']", timeout=30000)

    # Expand all rows if the "Alle ansehen" button is still active
    show_all = page.locator("button:has-text('Alle ansehen')")
    if show_all.count() > 0 and show_all.first.is_enabled():
        show_all.first.click()
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

    # Scrape all rows and their dates in one JS pass
    raw_rows: list[dict] = page.evaluate("""() => {
        const rows = Array.from(document.querySelectorAll('[data-testid^="billing-history-table-row-"]'))
            .filter(el => /^billing-history-table-row-\\d+$/.test(el.dataset.testid));
        return rows.map((row, i) => ({
            index: i,
            testid: row.dataset.testid,
            dateText: (row.firstChild?.textContent ?? row.innerText?.split('\\n')[0] ?? '').trim(),
        }));
    }""")

    for row_info in raw_rows:
        inspected_rows += 1
        row_date = _parse_dropbox_date(row_info["dateText"])
        if row_date and not (date_from <= row_date <= date_to):
            continue

        testid = row_info["testid"]
        try:
            # Click the "..." menu for this specific row
            row_locator = page.locator(f'[data-testid="{testid}"]')
            menu_btn = row_locator.locator('button[data-testid="billing-history-more-menu-trigger-button"]')
            menu_btn.click(timeout=5000)

            # Get invoice URL from the menu
            invoice_link = page.locator('a[data-testid="invoice-page-link"]').first
            invoice_href = invoice_link.get_attribute("href", timeout=5000) or ""
            bill_id = invoice_href.split("bill_id=")[1].split("&")[0] if "bill_id=" in invoice_href else ""
            page.keyboard.press("Escape")

            if not bill_id:
                raise RuntimeError("Could not extract bill_id from invoice link")

            invoice_url = f"https://www.dropbox.com/payments/invoice?bill_id={bill_id}&most_recent_invoice_only=true"

            # Open invoice page and print to PDF via CDP
            inv_page = page.context.new_page()
            try:
                inv_page.goto(invoice_url, wait_until="networkidle", timeout=30000)
                pdf_bytes = _page_to_pdf(inv_page)
            finally:
                inv_page.close()

            filename = f"dropbox_invoice_{bill_id}.pdf"
            out_path = output_dir / filename
            out_path.write_bytes(pdf_bytes)
            downloaded.append({
                "filename": filename,
                "path": str(out_path),
                "bill_id": bill_id,
                "date": str(row_date),
                "description": row_info.get("dateText", ""),
                "url": invoice_url,
            })
        except Exception as exc:
            errors.append({"row": testid, "date": row_info.get("dateText", ""), "message": str(exc)})

    return {
        "downloaded": downloaded,
        "inspected_rows": inspected_rows,
        "errors": errors,
    }


PROVIDER = InvoiceProvider(
    source="dropbox",
    start_url=START_URL,
    state_file="dropbox.state.json",
    email_env="DROPBOX_EMAIL",
    password_env="DROPBOX_PASSWORD",
    login=login,
    login_check=is_logged_in,
    collect=collect,
)
