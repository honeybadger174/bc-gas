# BC Gas Predictor — setup (no coding required)

This runs itself and publishes a free public webpage that predicts whether
Vancouver and Victoria gas prices will go up or down tomorrow. Once it's set up,
**you do nothing** — it updates every morning on its own.

Your whole job is a one-time, click-only setup. There is **no code to write and
nothing to edit.** (I wrote all the code; if it ever breaks, send me the error
message and I'll fix it.)

---

## What you'll do once (~20 minutes of clicking)

You need one free account — GitHub. It will both store the app and host the
website for free. No credit card.

**1. Make a free GitHub account** → github.com → Sign up.

**2. Create the repository from these files**
   - On GitHub, click the **+** (top right) → **New repository**.
   - Name it (e.g. `bc-gas`), set it to **Public**, click **Create repository**.
   - On the new repo page, click **uploading an existing file**.
   - Drag in *all* the files from this folder (keep the folder structure), then
     click **Commit changes**.

**3. Give it permission to update itself**
   - In the repo: **Settings** → **Actions** → **General**.
   - Under *Workflow permissions*, choose **Read and write permissions** → **Save**.

**4. Turn on the free website**
   - **Settings** → **Pages**.
   - Under *Source*, choose **GitHub Actions**. That's it — no other options.

**5. Do the first run**
   - Click the **Actions** tab → **daily-rack-loop** (left side) → **Run workflow**.
   - Wait ~2 minutes. A green check ✓ means it worked.
   - Your live page appears at: `https://<your-username>.github.io/<repo-name>/`

Done. From now on it runs by itself every morning around 6 AM Pacific.

---

## What happens after that (nothing, by you)

- Every morning it fetches the Petro-Canada rack, predicts tomorrow's move for
  both cities, and republishes the page. Hands-free.
- If the automatic fetch ever hiccups, the page **keeps showing the last known
  number** (with a small note) instead of going blank.
- If GitHub ever emails you that a run failed, **forward it to me** — that's a
  maintenance job, not something you need to learn.

## The only two dials you might ever want (both optional)

In `model.py`, near the top, two plain-English numbers:
- `UP_PASS` / `DOWN_PASS` — how fast price rises vs. drops reach the pump.
- `SEED_MARKUP` — a rough "rack-to-pump" gap for each city.

You can ignore these entirely to start. If predictions feel off later, tell me
and I'll adjust them for you.

---

*Predictions are estimates, not guarantees. Before adding ads or going big,
we'll check the data-provider terms.*
