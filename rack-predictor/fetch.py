"""
Data fetching for the BC gas predictor.

Petro-Canada blocks plain HTTP requests (it returns a 500 / bot page to anything
that isn't a real browser), so we load the page in a headless browser
(Playwright) exactly as a person would, then read the Vancouver and Nanaimo
terminal rack from the rendered table. Retail is optional and off by default.

Maintainer note: if this stops finding values, either the page layout / column
labels changed, or Petro-Canada started blocking the runner's IP. run.py wraps
this call so a failure reuses yesterday's numbers and keeps the site up.
"""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright

RACK_URL = "https://www.petro-canada.ca/en/business/rack-prices"
TERMINALS = {"vancouver": "Vancouver", "nanaimo": "Nanaimo"}
PRODUCT = "REG E-10"        # the 10%-ethanol regular column (what pumps sell)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")


def _norm(s: str) -> str:
    """Lowercase and strip everything but letters/digits, so 'REG E-10' -> 'rege10'."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def fetch_rack() -> dict:
    """Return {'vancouver': <c/L>, 'nanaimo': <c/L>} from Petro-Canada's daily rack."""
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(user_agent=UA, locale="en-CA")
        page = ctx.new_page()
        try:
            page.goto(RACK_URL, wait_until="domcontentloaded", timeout=60000)
            # Wait until the React table is actually populated (many rows), which
            # also gives Cloudflare time to clear.
            page.wait_for_function(
                "document.querySelectorAll('table tr').length > 10", timeout=45000)
            rows = page.eval_on_selector_all(
                "table tr",
                "els => els.filter(tr => tr.offsetParent !== null)"
                ".map(tr => Array.from(tr.querySelectorAll('th,td'))"
                ".map(c => c.innerText.trim()))",
            )
        finally:
            browser.close()

    # Find the REG E-10 column index from the header row.
    target = _norm(PRODUCT)
    col = None
    for r in rows:
        for i, cell in enumerate(r):
            if _norm(cell) == target:
                col = i
                break
        if col is not None:
            break
    if col is None:
        raise RuntimeError(f"Rack table found but no '{PRODUCT}' column — layout changed?")

    out: dict = {}
    for r in rows:
        if not r:
            continue
        name = _norm(r[0])
        for key, label in TERMINALS.items():
            if _norm(label) in name and key not in out and len(r) > col:
                val = re.sub(r"[^0-9.]", "", r[col])
                if val:
                    out[key] = round(float(val), 1)

    missing = [k for k in TERMINALS if k not in out]
    if missing:
        raise RuntimeError(f"Rack fetch found no value for {missing} — page format changed?")
    return out


def fetch_retail() -> dict:
    """Optional retail (off by default). None makes the model run on rack alone."""
    return {"vancouver": None, "victoria": None}
