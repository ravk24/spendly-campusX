# Spec: Registration

## Overview

Turn the static `/register` page into a working sign-up flow. The route currently renders `register.html` and ignores form submissions; this step adds POST handling that validates the submitted name, email, and password, hashes the password with werkzeug, inserts the new user into the existing `users` table, and sends the user to the login page with a success message. This is the first step that writes user input to the database, so it establishes the house patterns for form validation, error re-rendering, and parameterised inserts that later steps (login, expenses) will copy. Deliberately **out of scope**: sessions, `SECRET_KEY`, flash messages, and auto-login after registration — those arrive with Step 3 (login/logout). The success message is passed via a query parameter instead.

## Depends on

- Step 1 — Database Setup (`users` table, `get_db()`, connection lifecycle). Complete.

## Routes

- `POST /register` — process the sign-up form; on failure re-render `register.html` with an `error` string and the submitted values; on success redirect to `url_for('login', registered=1)` — public
- `GET /register` — unchanged behavior (renders the form), but the route declaration gains `methods=["GET", "POST"]` — public

No other new routes.

## Database changes

No database changes. The `users` table from Step 1 already has everything needed (`name`, `email` UNIQUE COLLATE NOCASE, `password_hash`, `created_at` default).

## Templates

- **Create:** none
- **Modify:**
  - `templates/register.html` — add `value="{{ name or '' }}"` / `value="{{ email or '' }}"` to the name and email inputs so a failed submission does not wipe what the user typed. The password input stays empty on re-render. The `{% if error %}` block already exists — do not change it.
  - `templates/login.html` — above the `{% if error %}` block, add `{% if request.args.get('registered') %}<div class="auth-success">Account created. Sign in to continue.</div>{% endif %}`.

## Files to change

- `app.py` — rework the `register()` route: add `methods=["GET", "POST"]`, import `request`, `redirect`, `url_for` from flask, import `generate_password_hash` from `werkzeug.security`, and implement the POST branch.
- `templates/register.html` — value repopulation (above).
- `templates/login.html` — success banner (above).
- `static/css/style.css` — add `.auth-success` to the existing `/* Auth pages */` section, mirroring `.auth-error`'s shape but using the green tokens (`--accent` family), not new literal colors.

## Files to create

None.

## New dependencies

No new dependencies. `werkzeug` ships with Flask and is already used in `database/db.py`.

## Validation rules (server-side, in this order)

1. Read `name`, `email`, `password` from `request.form` (`.get(..., "")`).
2. Normalise: `name.strip()`, `email.strip().lower()`. Never trim the password.
3. All three present and non-empty → else error `"All fields are required."`
4. Email contains `"@"` with non-empty text either side (simple check — no regex, no email libraries) → else `"Enter a valid email address."`
5. Password length ≥ 8 (matches the form placeholder "Min. 8 characters") → else `"Password must be at least 8 characters."`
6. Insert with a parameterised query. Catch `sqlite3.IntegrityError` from the UNIQUE constraint → `"That email is already registered."` Do **not** pre-check with a SELECT; the constraint is the source of truth (avoids the check-then-insert race and matches the Step 1 schema's intent).

On any error: `render_template("register.html", error=<msg>, name=<submitted name>, email=<submitted email>)` with HTTP 200. On success: commit, then `redirect(url_for("login", registered=1))`.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` from `database.db`.
- Parameterised queries only (`?` placeholders); never f-strings/`%`/`.format()` in SQL.
- Password hashed with `werkzeug.security.generate_password_hash` (library default method, same as the seed).
- Email stored lowercase and stripped, consistent with `seed_db()`.
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html` (both touched templates already do; keep it that way).
- Do not add `SECRET_KEY`, `session`, or `flash` in this step.
- Do not touch the other placeholder routes or `database/db.py`.
- Keep the endpoint name `register` — `base.html` and `login.html` link to it via `url_for`.

## Definition of done

- [ ] App starts (`./venv/Scripts/python.exe app.py`) and `GET /register` still renders the form.
- [ ] Submitting valid details (e.g. `Asha Rao / asha@example.com / password123`) redirects to `/login?registered=1`, which shows the green "Account created" banner.
- [ ] `SELECT name, email, password_hash FROM users WHERE email='asha@example.com'` shows the row with a hash, not the plaintext password, and the email lowercased even if submitted as `ASHA@Example.com`.
- [ ] Submitting the same email again (any casing, e.g. `Asha@EXAMPLE.com`) re-renders the form with "That email is already registered." and the name/email fields still populated.
- [ ] Submitting a 7-character password re-renders with the password-length error; empty fields re-render with the required-fields error (test with `curl -X POST` since the browser's `required`/`minlength` won't exercise the server side).
- [ ] `GET /login` without the query param shows no success banner.
- [ ] Grep `app.py`: no f-strings or `%`/`.format()` inside SQL strings; no `session`, `flash`, or `secret_key` anywhere.
- [ ] `.auth-success` styles use only `var(--…)` tokens.
