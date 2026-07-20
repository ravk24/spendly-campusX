# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Spendly — a Flask expense tracker built as a **teaching scaffold**. The landing/auth/legal pages are finished; the actual expense features are deliberately unimplemented stubs that a student fills in step by step. `app.py` has a "Placeholder routes — students will implement these" section where each stub returns a plain string naming the step it belongs to (`/logout` → Step 3, `/profile` → Step 4, `/expenses/add` → Step 7, etc.). `database/db.py` is a comment block specifying the three functions Step 1 expects (`get_db()`, `init_db()`, `seed_db()`), and `static/js/main.js` is an empty placeholder.

Because of this, **do not implement the stubbed steps unless explicitly asked** — the empty state is the curriculum. When asked to build one, follow the contract written in the placeholder comment rather than inventing a different shape.

## Commands

The venv is committed-adjacent but gitignored; use its interpreter directly (Windows layout — `Scripts`, not `bin`):

```shell
./venv/Scripts/python.exe -m pip install -q -r requirements.txt
./venv/Scripts/python.exe app.py          # dev server, debug on, http://127.0.0.1:5001
./venv/Scripts/python.exe -m pytest                          # all tests
./venv/Scripts/python.exe -m pytest path/to/test_x.py::test_name   # single test
```

Port is **5001**, not Flask's default 5000. There is no test suite yet — `pytest` and `pytest-flask` are in `requirements.txt` for the steps that add one.

To kill a stale server before restarting:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Pages are verified visually by screenshotting with headless Edge (see `.claude/settings.local.json` for the allowlisted invocations):

```shell
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --disable-gpu --no-sandbox \
  --user-data-dir="$TEMP/claude/edgeprof" --screenshot="<scratchpad>/page.png" \
  --window-size=1200,1500 --hide-scrollbars "http://127.0.0.1:5001/"
```

## Architecture

Single-module Flask app — every route lives in `app.py`, all of them currently `render_template` only. There is no app factory, no blueprints, no ORM; the intended data layer is raw `sqlite3` via `database/db.py` against `expense_tracker.db` (gitignored, created at runtime).

Templates all extend `base.html`, which owns the navbar, footer, font preconnects, the global stylesheet, and `main.js`. Blocks available: `title`, `head`, `content`, `scripts`. Cross-page links go through `url_for('<endpoint>')` — adding a route means the nav/footer can reference it by endpoint name, so keep endpoint names stable.

`static/css/style.css` is a single hand-written stylesheet (~690 lines), no build step, no framework. It opens with a `:root` design-token block (`--ink*` text, `--paper*` surfaces, `--accent` green / `--accent-2` amber, `--font-display` DM Serif Display for headings, `--font-body` DM Sans, plus radius and width tokens) and is then split into banner-commented sections (`Navbar`, `Hero`, `Buttons`, `Features section`, `Video modal`, …). New styling should reuse the tokens and land in the matching section rather than introducing new literal colors.

Page-specific JavaScript goes inline in that template's `{% block scripts %}` — the landing page's video modal is the working example of the house style: an IIFE, `data-modal-open` / `data-modal-close` hooks instead of ad-hoc IDs, and `src` set from `data-src` on open then removed on close so the iframe never preloads and playback actually stops. `main.js` is for behavior that is genuinely global.

The `misc/` directory is gitignored scratch (screenshots, etc.) — nothing there is part of the app.
