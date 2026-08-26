"""
Orchestrator — the whole daily loop in one readable pass:

    fetch rack ─▶ grade yesterday ─▶ update markup ─▶ predict tomorrow ─▶ render

Run locally with `python run.py` to test; the GitHub Action runs the same thing
every morning and commits data/ + site/. Git history is your database.
"""

from __future__ import annotations
import csv
import os
import datetime as dt

import fetch
import model
from render_site import render

HIST = "data/history.csv"
FIELDS = ["date", "rack_vancouver", "rack_nanaimo", "retail_vancouver",
          "retail_victoria", "pred_van_dir", "pred_vic_dir", "graded_van", "graded_vic"]


def load_history() -> list[dict]:
    if not os.path.exists(HIST):
        return []
    with open(HIST) as f:
        rows = list(csv.DictReader(f))
    for r in rows:  # numeric coercion; blanks -> None
        for k in ("rack_vancouver", "rack_nanaimo", "retail_vancouver", "retail_victoria"):
            r[k] = float(r[k]) if r.get(k) not in (None, "") else None
    return rows


def append_history(row: dict) -> None:
    os.makedirs("data", exist_ok=True)
    new = not os.path.exists(HIST)
    with open(HIST, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    today = dt.date.today().isoformat()
    hist = load_history()
    prev = hist[-1] if hist else {}

    # Fail-safe: if the scrape breaks, reuse yesterday's rack so the public page
    # stays alive (showing a "data as of ..." note) instead of going dark.
    stale = False
    try:
        rack = fetch.fetch_rack()      # {'vancouver':.., 'nanaimo':..}
    except Exception as e:
        if prev.get("rack_vancouver") is None:
            raise                      # nothing to fall back to on day one — fail loudly
        print(f"WARN rack fetch failed ({e}); reusing last known values")
        rack = {"vancouver": prev["rack_vancouver"], "nanaimo": prev["rack_nanaimo"]}
        stale = True

    retail = fetch.fetch_retail()      # {'vancouver':.., 'victoria':..} (may be None)

    # 1) Grade yesterday's calls against today's actual retail.
    graded_van = model.grade(prev.get("pred_van_dir"), prev.get("retail_vancouver"), retail["vancouver"])
    graded_vic = model.grade(prev.get("pred_vic_dir"), prev.get("retail_victoria"), retail["victoria"])

    # 2) Refresh the learned markup from recent history.
    markup_van = model.rolling_markup(hist, "vancouver")
    markup_vic = model.rolling_markup(hist, "victoria")

    # 3) Predict tomorrow for each city off its own terminal rack.
    p_van = model.predict("vancouver", rack["vancouver"], prev.get("rack_vancouver"),
                          retail["vancouver"], markup_van)
    p_vic = model.predict("victoria", rack["nanaimo"], prev.get("rack_nanaimo"),
                          retail["victoria"], markup_vic)

    # 4) Rolling accuracy for display (last 30 graded days).
    graded = [g for g in ((r.get("graded_van"), r.get("graded_vic")) for r in hist[-30:])]
    flat = [x == "True" for pair in graded for x in pair if x in ("True", "False")]
    hit_rate = f"{round(100 * sum(flat) / len(flat))}% ({len(flat)} calls)" if flat else "building…"

    # 5) Persist + render.
    append_history({
        "date": today,
        "rack_vancouver": rack["vancouver"], "rack_nanaimo": rack["nanaimo"],
        "retail_vancouver": retail["vancouver"] if retail["vancouver"] is not None else "",
        "retail_victoria": retail["victoria"] if retail["victoria"] is not None else "",
        "pred_van_dir": p_van.direction, "pred_vic_dir": p_vic.direction,
        "graded_van": graded_van, "graded_vic": graded_vic,
    })
    render([p_van, p_vic], rack, hit_rate, stale=stale)
    print(f"{today}  Van {p_van.direction} ({p_van.change_c:+}c)  "
          f"Vic {p_vic.direction} ({p_vic.change_c:+}c)  acc={hit_rate}")


if __name__ == "__main__":
    main()
