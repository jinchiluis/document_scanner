from datetime import date
from pathlib import Path
from typing import Any

from jobs.browser_invoices import (
    InvoiceProvider,
    accept_common_consent,
    click_first,
    fill_first,
)

START_URL = "https://manage.wix.com/studio/billing-history"

_DE_MONTHS = {
    "jan": 1, "feb": 2, "märz": 3, "apr": 4, "mai": 5, "juni": 6,
    "juli": 7, "aug": 8, "sep": 9, "sept": 9, "okt": 10, "nov": 11, "dez": 12,
}


def login(page: Any, email: str, password: str) -> None:
    # Wix login is a two-step flow: email → continue → password → submit
    page.goto("https://users.wix.com/signin", wait_until="domcontentloaded", timeout=60000)
    accept_common_consent(page)

    # Step 1: fill email and click continue
    fill_first(page, ["input[name='email']", "input[data-hook='wsr-input']"], email)
    click_first(page, ["button[data-hook='login.submitButton']", "button[type='submit']"], timeout=8000)

    # Step 2: wait for password field, fill it, submit
    page.wait_for_selector("input[autocomplete='current-password']", timeout=15000)
    fill_first(page, ["input[autocomplete='current-password']", "input[type='password']"], password)
    click_first(page, ["button[data-hook='login.submitButton']", "button[type='submit']"], timeout=8000)

    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass


def is_logged_in(page: Any) -> bool:
    try:
        return "users.wix.com/signin" not in page.url
    except Exception:
        return False


def _parse_de_date(text: str) -> date | None:
    """Parse German date like '4. Nov. 2025' into a date object."""
    parts = text.replace(".", "").split()
    if len(parts) != 3:
        return None
    try:
        day = int(parts[0])
        month = _DE_MONTHS.get(parts[1].lower().rstrip("."))
        year = int(parts[2])
        if month:
            return date(year, month, day)
    except (ValueError, AttributeError):
        pass
    return None


SUBSCRIPTIONS_URL = "https://manage.wix.com/studio/subscriptions"


def _scrape_subscriptions(page: Any) -> list[dict[str, Any]]:
    page.goto(SUBSCRIPTIONS_URL, wait_until="domcontentloaded", timeout=60000)
    accept_common_consent(page)
    page.wait_for_selector("tr[data-hook^='table-row-']", timeout=30000)

    results = []
    rows = page.locator("tr[data-hook^='table-row-']")
    for i in range(rows.count()):
        row = rows.nth(i)
        try:
            plan = (
                row.locator("span[data-hook='plan--title']").first.inner_text(timeout=2000).strip()
                + " "
                + row.locator("span[data-hook='plan--product-name']").first.inner_text(timeout=2000).strip()
            ).strip()
            website = row.locator("a[data-hook='site-details--dashboard-link']").first.inner_text(timeout=2000).strip()
            last_payment_raw = row.locator("span[data-hook='subscription--payment-date']").first.inner_text(timeout=2000).strip()
            next_payment_raw = row.locator("div[data-hook='subscription--next-payment'] span[data-hook='subscription--payment-date']").first.inner_text(timeout=2000).strip()
            billing_cycle = row.locator("span[data-hook='subscription--payment-cycle-name']").first.inner_text(timeout=2000).strip()
            payment_method = row.locator("span[data-hook='payment-method--payment-text']").first.inner_text(timeout=2000).strip()
            status = row.locator("div[data-hook='active-column']").first.inner_text(timeout=2000).strip()
            invoice_href = row.locator("a[data-hook='subscription--last-payment-view-invoice']").first.get_attribute("href", timeout=2000) or ""
            invoice_id = invoice_href.split("invoiceId=")[-1] if "invoiceId=" in invoice_href else ""
            results.append({
                "plan": plan,
                "website": website,
                "last_payment_date": str(_parse_de_date(last_payment_raw) or last_payment_raw),
                "next_payment_date": str(_parse_de_date(next_payment_raw) or next_payment_raw),
                "billing_cycle": billing_cycle,
                "payment_method": payment_method,
                "status": status,
                "last_invoice_id": invoice_id,
            })
        except Exception as exc:
            results.append({"error": str(exc), "row_index": i})
    return results


def _next_invoice_summary(subscriptions: list[dict[str, Any]]) -> dict[str, Any] | None:
    dated: list[tuple[date, dict[str, Any]]] = []
    for subscription in subscriptions:
        raw_date = subscription.get("next_payment_date")
        if not isinstance(raw_date, str):
            continue
        try:
            next_date = date.fromisoformat(raw_date)
        except ValueError:
            continue
        dated.append((next_date, subscription))

    if not dated:
        return None

    next_date, subscription = min(dated, key=lambda item: item[0])
    return {
        "date": str(next_date),
        "plan": subscription.get("plan", ""),
        "website": subscription.get("website", ""),
        "billing_cycle": subscription.get("billing_cycle", ""),
        "payment_method": subscription.get("payment_method", ""),
        "status": subscription.get("status", ""),
    }


def collect(page: Any, date_from: date, date_to: date, output_dir: Path) -> dict[str, Any]:
    downloaded: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    inspected_rows = 0

    # browser_invoices.py already navigated to START_URL before calling collect()
    page.wait_for_selector("button[data-hook='invoice-number']", timeout=30000)

    # Scrape all invoice IDs and their dates from the grid in one JS pass.
    # Each row is div[data-hook="invoice"]; date is span[data-hook="date"] inside it.
    raw_pairs: list[dict] = page.evaluate("""() => {
        const btns = Array.from(document.querySelectorAll('button[data-hook="invoice-number"]'));
        return btns.map(btn => {
            const id = btn.innerText.trim().split('\\n')[0];
            const row = btn.closest('[data-hook="invoice"]');
            const dateText = row?.querySelector('[data-hook="date"]')?.innerText?.trim() ?? '';
            return { id, dateText };
        });
    }""")
    invoice_data: list[tuple[str, date | None]] = [
        (r["id"], _parse_de_date(r["dateText"])) for r in raw_pairs
    ]

    for invoice_id, invoice_date in invoice_data:
        inspected_rows += 1
        if invoice_date and not (date_from <= invoice_date <= date_to):
            continue
        try:
            pdf_url = f"https://manage.wix.com/premium-invoice/api/v1/invoice/{invoice_id}"
            # Use the session's request context — direct HTTP GET with browser cookies, no PDF viewer
            response = page.context.request.get(pdf_url, timeout=30000)
            if not response.ok:
                raise RuntimeError(f"HTTP {response.status} for invoice {invoice_id}")
            pdf_bytes = response.body()
            filename = f"wix_invoice_{invoice_id}.pdf"
            out_path = output_dir / filename
            out_path.write_bytes(pdf_bytes)
            downloaded.append({
                "filename": filename,
                "path": str(out_path),
                "invoice_id": invoice_id,
                "date": str(invoice_date),
                "url": pdf_url,
            })
        except Exception as exc:
            errors.append({"invoice_id": invoice_id, "message": str(exc)})

    subscriptions = _scrape_subscriptions(page)

    return {
        "downloaded": downloaded,
        "inspected_rows": inspected_rows,
        "errors": errors,
        "subscriptions": subscriptions,
        "next_invoice": _next_invoice_summary(subscriptions),
    }


PROVIDER = InvoiceProvider(
    source="wix",
    start_url=START_URL,
    state_file="wix.state.json",
    email_env="WIX_EMAIL",
    password_env="WIX_PASSWORD",
    login=login,
    login_check=is_logged_in,
    collect=collect,
)
