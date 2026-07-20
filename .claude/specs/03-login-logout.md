# Spec: Login and Logout

## Overview

Turn the static `/login` page into a working sign-in flow and replace the `/logout` stub with a real session teardown. This is the step that introduces sessions to Spendly: `SECRET_KEY` is configured, a successful login stores the user's id and name in Flask's signed session cookie, the navbar switches between logged-out links (Sign in / Get started) and logged-in links (greeting + Log out), and `/logout` clears the session. Login verifies credentials against the `users` table created in Step 1 using the same normalisation and hashing conventions Step 2 established for registration. Deliberately **out of scope**: a `login_required` decorator and protecting the expense routes (arrives with the steps that implement them), "remember me", password reset, and any change to the `/register` flow.

## Depends on

- Step 1 — Database Setup (`users` table, `get_db()`). Complete.
- Step 2 — Registration (users exist with werkzeug password hashes; login page already shows the `registered=1` success banner). Complete.

## Routes

- `POST /login` — process the sign-in form; on failure re-render `login.html` with an `error` string and the submitted email; on success store the user in `session` and redirect to `url_for('profile')` — public
- `GET /login` — unchanged rendering, but the route declaration gains `methods=["GET", "POST"]`; if the visitor is already logged in, redirect to `url_for('profile')` instead of rendering the form — public
- `GET /logout` — replace the Step 3 placeholder body: clear the session and redirect to `url_for('landing')` — public (safe to hit while logged out; it just redirects)

Note: `/profile` is still the Step 4 stub, so after login the browser lands on the plain "Profile page — coming in Step 4" string. That is expected and is how the redirect is verified; do not implement the profile page in this step.

No other new routes.

## Database changes

No database changes. Login only reads `users` (`id`, `name`, `email`, `password_hash`).

## Templates

- **Create:** none
- **Modify:**
  - `templates/login.html` — add `value="{{ email or '' }}"` to the email input so a failed submission keeps the typed email (mirror of Step 2's register repopulation). The password input stays empty on re-render. The existing `{% if error %}` and `registered` banner blocks are already correct — do not change them. Change `action="/login"` to `action="{{ url_for('login') }}"` to match the house `url_for` convention.
  - `templates/base.html` — in `.nav-links`, branch on the session: when `session.get('user_id')` is set, render `<span class="nav-user">Hi, {{ session['user_name'] }}</span>` and `<a href="{{ url_for('logout') }}" class="nav-cta">Log out</a>`; otherwise keep the existing Sign in / Get started links exactly as they are. (`session` is available in Jinja templates by default — no context processor needed.)

## Files to change

- `app.py` — set `app.config["SECRET_KEY"]` (see rules), rework `login()` (add `methods=["GET", "POST"]`, implement the POST branch, add the already-logged-in redirect on GET), replace the `logout()` placeholder body, add `session` and `check_password_hash` imports.
- `templates/login.html` — email repopulation + `url_for` action (above).
- `templates/base.html` — session-aware navbar (above).
- `static/css/style.css` — add `.nav-user` to the existing `/* Navbar */` section (muted inline text next to the nav links, e.g. `color: var(--ink-soft)` or whichever muted ink token the section already uses). Reuse tokens only; the Log out link reuses `.nav-cta` unchanged.

## Files to create

None.

## New dependencies

No new dependencies. `session` ships with Flask; `check_password_hash` ships with werkzeug.

## Login logic (server-side, in this order)

1. GET: if `session.get("user_id")` → `redirect(url_for("profile"))`, else render the form as today.
2. POST: read `email`, `password` from `request.form` (`.get(..., "")`); normalise `email.strip().lower()`, never trim the password.
3. Both present and non-empty → else error `"All fields are required."`
4. `SELECT id, name, password_hash FROM users WHERE email = ?` (parameterised). If no row **or** `check_password_hash` fails → the same generic error `"Invalid email or password."` — never reveal which of the two was wrong.
5. On success: `session.clear()`, then set `session["user_id"]` (int) and `session["user_name"]` (the user's `name`), then `redirect(url_for("profile"))`.
6. On any error: `render_template("login.html", error=<msg>, email=<submitted email>)` with HTTP 200.

`logout()`: `session.clear()` then `redirect(url_for("landing"))` — no flash, no query param.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` from `database.db`.
- Parameterised queries only (`?` placeholders); never f-strings/`%`/`.format()` in SQL.
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plaintext or re-hash to compare.
- `SECRET_KEY` via `os.environ.get("SPENDLY_SECRET_KEY", "dev-only-change-me")` set right after `app = Flask(__name__)` — an env override with an obviously-dev fallback, never a bare hardcoded production-looking secret.
- One generic failure message for bad email and bad password alike (no user enumeration).
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html` (touched templates already do; keep it that way).
- Keep endpoint names `login` and `logout` stable — `base.html` and `register.html` reference them via `url_for`.
- Do not touch `/register`, the other placeholder routes, or `database/db.py`.
- No `flash()` in this step — errors render inline via the existing `auth-error` block, matching Step 2's pattern.

## Definition of done

- [ ] App starts (`./venv/Scripts/python.exe app.py`); `GET /login` renders the form unchanged, and the navbar still shows Sign in / Get started.
- [ ] Logging in as the seed user (`demo@spendly.com` / `demo123`) redirects to `/profile` (the Step 4 stub string), and the navbar on any page now shows "Hi, Demo User" and a Log out link instead of Sign in / Get started.
- [ ] Email casing/whitespace doesn't matter: ` DEMO@Spendly.com ` with the right password also logs in.
- [ ] Wrong password and unknown email both re-render the form with the identical "Invalid email or password." message, with the email field still populated and the password field empty.
- [ ] Empty fields (test with `curl -X POST`, since the browser's `required` blocks this client-side) re-render with "All fields are required."
- [ ] While logged in, `GET /login` redirects to `/profile` instead of showing the form.
- [ ] `GET /logout` returns to the landing page with the logged-out navbar; visiting `/logout` while already logged out also just redirects (no error).
- [ ] The session survives a page navigation (cookie-based) — browse to `/terms` after login and the navbar still shows the greeting.
- [ ] Grep `app.py`: no f-strings or `%`/`.format()` inside SQL strings; no plaintext password comparison; `check_password_hash` used.
- [ ] `.nav-user` styles use only `var(--…)` tokens.
