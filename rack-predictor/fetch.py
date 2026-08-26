"""
Data fetching.

  1. Petro-Canada posted terminal rack  (FREE, DAILY)  <- the only input needed
  2. Current retail pump average        (OPTIONAL — off by default)

You (Evan) don't need to edit anything here. The rack fetch runs on its own and,
if Petro-Canada ever changes their page, the app keeps showing the last known
number instead of breaking (see run.py). Retail is switched off so nothing extra
is required to launch; it can be turned on later to publish an accuracy log.

The notes below are for whoever maintains the code (that's me — if the fetch
ever fails, send me the error and I'll patch this file).
"""

from __future__ import annotations
import io
import requests
import pandas as pd

UA = {"User-Agent": "Mozilla/5.0 (compatible; rack-predictor/1.0; personal project)"}
RACK_URL = "https://www.petro-canada.ca/en/business/rack-prices"

# Terminals you care about. Vancouver -> Metro Van retail; Nanaimo -> Victoria/Island.
TERMINALS = {"vancouver": "Vancouver", "nanaimo": "Nanaimo"}

# Which product column to read. Regular 87, E-10 blend, in CAD cents/L excl. tax.
PRODUCT_HINT = "Regular"        # tune to the exact column label on the page


def fetch_rack() -> dict[str, float]:
    """
    Return {'vancouver': <c/L>, 'nanaimo': <c/L>} from Petro-Canada's posted rack.

    MAINTAINER NOTE ----------------------------------------------------------
    pandas.read_html works if the table is in the served markup. If it comes back
    empty, the table is JS-loaded from a JSON endpoint: DevTools -> Network ->
    XHR, find the request returning the rack numbers, and call THAT url here (it's
    plain JSON, and more robust than HTML scraping). run.py wraps this call so a
    failure reuses yesterday's values and keeps the site up rather than crashing.
    -------------------------------------------------------------------------
    """
    html = requests.get(RACK_URL, headers=UA, timeout=30).text
    tables = pd.read_html(io.StringIO(html))   # list of DataFrames found on the page

    out: dict[str, float] = {}
    for df in tables:
        cols = [str(c) for c in df.columns]
        loc_col = next((c for c in cols if "location" in c.lower() or "terminal" in c.lower()), cols[0])
        prod_col = next((c for c in cols if PRODUCT_HINT.lower() in c.lower()), None)
        if prod_col is None:
            continue
        for _, row in df.iterrows():
            name = str(row[loc_col]).strip().lower()
            for key, label in TERMINALS.items():
                if label.lower() in name and key not in out:
                    out[key] = _to_cents(row[prod_col])

    missing = [k for k in TERMINALS if k not in out]
    if missing:
        raise RuntimeError(
            f"Rack fetch found no value for {missing}. Page format likely changed "
            f"— see WIRE-UP #1 in fetch.py. Tables seen: {len(tables)}"
        )
    return out


def fetch_retail() -> dict[str, float | None]:
    """
    Return {'vancouver': <c/L or None>, 'victoria': <c/L or None>} — today's
    average pump price incl. taxes, used only to grade/tune the model.

    OFF BY DEFAULT so launch needs nothing extra. Returning None makes the model
    run on rack alone. To switch it on later (for a public accuracy log), plug a
    compliant retail source in here — that's a maintainer job, not yours.
    -------------------------------------------------------------------------
    """
    return {"vancouver": None, "victoria": None}


def _to_cents(v) -> float:
    """Coerce '148.9', '148.9¢', 148.9 -> 148.9 (float, cents/L)."""
    s = str(v).replace("¢", "").replace(",", "").strip()
    return round(float(s), 1)
