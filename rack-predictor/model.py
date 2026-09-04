"""
The prediction model. Deliberately simple and honest — a heuristic you can
explain on the site, not a black box. It captures the one real mechanism:

    tomorrow's pump  ≈  today's pump  +  (pass-through) x (today's rack move)

with ASYMMETRIC pass-through — "rockets and feathers": pump prices chase the
rack up quickly and fully, and drift down slowly and partially. Those two
coefficients are the whole model, and you tune them against your own logged
accuracy over the first few weeks.

If you don't yet have a reliable retail number, it falls back to a level
estimate: tomorrow's pump ≈ today's rack + a fixed markup (taxes + margin)
that you seed once and refine as retail data accumulates.
"""

from __future__ import annotations
from dataclasses import dataclass

# --- Tunables (start here, then adjust against your accuracy log) -------------
UP_PASS   = 0.90   # share of a rack INCREASE that reaches the pump next day
DOWN_PASS = 0.55   # share of a rack DECREASE that reaches the pump next day
NOISE_C   = 0.75   # dead-band in c/L: |predicted move| under this = "FLAT"

# Seed markup = a recent (pump incl. tax) minus (rack excl. tax) for each city.
# Eyeball it once from today's numbers; the model refines it automatically once
# real retail data flows. Metro Van carries the TransLink levy; the Island does
# not, so the two markups differ — that difference is itself a feature.
SEED_MARKUP = {"vancouver": 46.0, "victoria": 51.0}   # c/L, calibrated to GasBuddy avgs (Sep 2026)


@dataclass
class Prediction:
    city: str
    direction: str      # "UP" | "DOWN" | "FLAT"
    change_c: float     # predicted c/L change vs today
    predicted_c: float  # predicted pump level tomorrow, incl. tax
    verdict: str        # human line for the site
    basis: str          # "change-model" or "rack+markup"


def predict(city: str, rack_today: float, rack_prev: float | None,
            retail_today: float | None, markup_est: float | None) -> Prediction:
    # Direction comes from the RACK MOVE, so a prediction needs only rack data —
    # retail is optional (it just sharpens the predicted level and lets you grade).
    markup = markup_est if markup_est is not None else SEED_MARKUP.get(city, 60.0)
    base = retail_today if retail_today is not None else round(rack_today + markup, 1)

    if rack_prev is None:                      # first day ever — no move to read
        change, predicted, basis = 0.0, base, "warming-up"
    else:
        move = rack_today - rack_prev
        coeff = UP_PASS if move > 0 else DOWN_PASS
        change = round(coeff * move, 1)
        predicted = round(base + change, 1)
        basis = "change-model" if retail_today is not None else "rack-only"

    if change >= NOISE_C:
        direction, verdict = "UP",   f"Prices likely UP ~{abs(change):.1f}¢ tomorrow — fill up tonight."
    elif change <= -NOISE_C:
        direction, verdict = "DOWN", f"Prices likely DOWN ~{abs(change):.1f}¢ tomorrow — wait if you can."
    else:
        direction, verdict = "FLAT", "No meaningful move expected tomorrow — fill up whenever."

    return Prediction(city, direction, change, predicted, verdict, basis)


def rolling_markup(history_rows: list, city: str, days: int = 14):
    """Median of (retail - same-day rack) over recent days, when both exist."""
    rack_key = "rack_vancouver" if city == "vancouver" else "rack_nanaimo"
    diffs = [r[f"retail_{city}"] - r[rack_key]
             for r in history_rows[-days:]
             if r.get(f"retail_{city}") not in (None, "") and r.get(rack_key) not in (None, "")]
    if not diffs:
        return None
    diffs.sort()
    n = len(diffs)
    return round((diffs[n // 2] if n % 2 else (diffs[n // 2 - 1] + diffs[n // 2]) / 2), 1)


def grade(prev_pred_dir, prev_retail, today_retail):
    """Was yesterday's direction right? None if we can't tell (missing retail)."""
    if prev_pred_dir is None or prev_retail is None or today_retail is None:
        return None
    actual = today_retail - prev_retail
    if prev_pred_dir == "UP":
        return actual >= 0
    if prev_pred_dir == "DOWN":
        return actual <= 0
    return abs(actual) < NOISE_C
