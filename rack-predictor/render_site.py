"""
Static-site rendering. No template engine — plain f-strings keep dependencies
(and surprises) to a minimum. Writes site/index.html, which GitHub Pages serves.
Styling is intentionally tiny here; drop in your real design later.
"""

from __future__ import annotations
import os
import json
import datetime as dt


def daily_blurb(preds: list, hit_rate: str) -> str:
    """
    Optional AI-written summary. If OPENAI_API_KEY isn't set, returns a plain
    deterministic sentence so the build never depends on the API. Swap in any
    provider you like; keep it cheap (a few cents/day) and fact-checked against
    the numbers you already computed — never let it invent prices.
    """
    key = os.environ.get("OPENAI_API_KEY")
    facts = "; ".join(f"{p.city.title()}: {p.verdict}" for p in preds)
    if not key:
        return facts
    try:
        # Minimal, dependency-free call. Replace model/endpoint as you wish.
        import requests
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content":
                        "You write a 2-sentence, factual daily note about BC gas prices. "
                        "Use ONLY the facts given. No new numbers. Plain, useful, no hype."},
                    {"role": "user", "content": f"Facts: {facts}. Recent accuracy: {hit_rate}."},
                ],
                "temperature": 0.4,
            },
            timeout=30,
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return facts   # never fail the build over the blurb


def render(preds: list, rack: dict, hit_rate: str, out_dir: str = "site",
           stale: bool = False) -> None:
    os.makedirs(out_dir, exist_ok=True)
    today = dt.date.today().isoformat()
    blurb = daily_blurb(preds, hit_rate)
    stale_note = (' <span style="color:#c0392b">· using last known rack (auto-update '
                  'hiccup — will self-correct)</span>') if stale else ""

    cards = "\n".join(
        f'''<div class="card {p.direction.lower()}">
              <div class="city">{p.city.title()}</div>
              <div class="dir">{p.direction}</div>
              <div class="verdict">{p.verdict}</div>
              <div class="meta">predicted ~{p.predicted_c:.1f}¢/L · {p.basis}</div>
            </div>''' for p in preds)

    html = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BC Gas Price Prediction — Tomorrow</title>
<style>
  body{{font:16px/1.5 system-ui,sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#111}}
  .card{{border:1px solid #ddd;border-left:5px solid #999;border-radius:10px;padding:16px;margin:12px 0}}
  .card.up{{border-left-color:#c0392b}} .card.down{{border-left-color:#2c815d}} .card.flat{{border-left-color:#b4670f}}
  .city{{font-weight:700;font-size:18px}} .dir{{font-family:monospace;letter-spacing:.1em}}
  .verdict{{margin:6px 0}} .meta{{color:#666;font-size:13px;font-family:monospace}}
  .foot{{color:#666;font-size:13px;margin-top:24px;border-top:1px solid #eee;padding-top:12px}}
</style></head><body>
<h1>Will BC gas prices go up tomorrow?</h1>
<p><em>{blurb}</em></p>
{cards}
<p class="foot">Today's posted rack — Vancouver {rack['vancouver']:.1f}¢ · Nanaimo {rack['nanaimo']:.1f}¢ (excl. tax).
Recent direction accuracy: <strong>{hit_rate}</strong>. Updated {today}{stale_note}.
Estimates only, not guarantees. Rack data: Petro-Canada posted terminal prices.</p>
</body></html>"""

    with open(os.path.join(out_dir, "index.html"), "w") as f:
        f.write(html)

    # Also emit machine-readable output for future pages/charts.
    with open(os.path.join(out_dir, "latest.json"), "w") as f:
        json.dump({"date": today, "rack": rack, "hit_rate": hit_rate,
                   "predictions": [p.__dict__ for p in preds]}, f, indent=2)
