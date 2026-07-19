# Spec: SQLite Data Layer for Spendly (v2 — Audited)

## 1. Overview

Replace the stub in `database/db.py` with a working SQLite implementation. This establishes the data layer foundation for Spendly. All future features (authentication, profile, expense tracking) depend on this being correctly implemented.

**Changes from v1:** resolved DB filename ambiguity, added connection lifecycle management, fixed invalid SQLite default syntax, added DB-level enforcement of categories and amounts, made email uniqueness case-insensitive, made seed data deterministic, defined FK delete behavior, added index, made Definition of Done verifiable.

## 2. Depends on

Nothing — this is the first step.

## 3. Routes

No new routes. Existing placeholder routes in `app.py` remain unchanged.

## 4. Database

**Filename:** `spendly.db` in project root. _(v1 said "spendly.db or expense_tracker.db" — a spec must not offer choices.)_

### A. `users`

| Column        | Type    | Constraints                            |
| ------------- | ------- | -------------------------------------- |
| id            | INTEGER | PRIMARY KEY AUTOINCREMENT              |
| name          | TEXT    | NOT NULL                               |
| email         | TEXT    | NOT NULL, UNIQUE **COLLATE NOCASE**    |
| password_hash | TEXT    | NOT NULL                               |
| created_at    | TEXT    | NOT NULL DEFAULT **(datetime('now'))** |

Notes:

- `COLLATE NOCASE` on email prevents `Demo@spendly.com` and `demo@spendly.com` coexisting. Application code must additionally lowercase + strip emails before insert.
- Expression defaults in SQLite **require parentheses**: `DEFAULT (datetime('now'))`. `DEFAULT datetime('now')` is a syntax error.
- `datetime('now')` is UTC. All timestamps in this system are UTC; document this for future steps.

### B. `expenses`

| Column      | Type    | Constraints                                                                                                |
| ----------- | ------- | ---------------------------------------------------------------------------------------------------------- |
| id          | INTEGER | PRIMARY KEY AUTOINCREMENT                                                                                  |
| user_id     | INTEGER | NOT NULL, FOREIGN KEY → users(id) **ON DELETE CASCADE**                                                    |
| amount      | REAL    | NOT NULL, **CHECK (amount > 0)**                                                                           |
| category    | TEXT    | NOT NULL, **CHECK (category IN ('Food','Transport','Bills','Health','Entertainment','Shopping','Other'))** |
| date        | TEXT    | NOT NULL, **CHECK (date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')**                               |
| description | TEXT    | NULL                                                                                                       |
| created_at  | TEXT    | NOT NULL DEFAULT (datetime('now'))                                                                         |

Index:

```sql
CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date);
```

Notes:

- **ON DELETE CASCADE**: deleting a user removes their expenses. (v1 left this undefined.)
- The category CHECK enforces the fixed list at the DB level, not just by convention.
- The date GLOB CHECK enforces `YYYY-MM-DD` shape at the DB level.
- **Known limitation — REAL for money:** floats can introduce rounding errors. Retained for simplicity per v1, with mitigation: application code MUST round amounts to 2 decimal places before insert, and all display code must format with 2 decimals. If precision issues surface, migrate to INTEGER cents in a future step.

## 5. Functions to Implement (`database/db.py`)

### A. `get_db()`

- Uses Flask's `g` object: if `g.db` exists, return it; otherwise open a connection to `spendly.db` in project root, store on `g`, and return it. _(v1 opened a new connection per call with no owner to close it — a connection leak.)_
- On every new connection, set:
  - `row_factory = sqlite3.Row`
  - `PRAGMA foreign_keys = ON` (per-connection in SQLite; never assume it persists)

### B. `close_db(e=None)` _(new in v2)_

- Pops `g.db` and closes it if present.
- Registered via `app.teardown_appcontext(close_db)` so every request/app-context cleanly closes its connection.

### C. `init_db()`

- Creates both tables and the index using `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`.
- Idempotent: safe to call multiple times; must not fail on repeated runs.

### D. `seed_db()`

- Idempotency check: `SELECT 1 FROM users WHERE email = 'demo@spendly.com'` — if the row exists, return early. _(v1 checked "any users exist", which couples seeding to unrelated data.)_
- Insert demo user:
  - name: `Demo User`
  - email: `demo@spendly.com` (stored lowercase)
  - password: `demo123`, hashed via `werkzeug.security.generate_password_hash` (library default method; do not pass a custom method)
- Insert exactly these 8 expenses (deterministic; dates are day-of-current-month computed as `YYYY-MM-` + fixed day, capped at 28 so it works in February):

| #   | amount  | category      | day | description       |
| --- | ------- | ------------- | --- | ----------------- |
| 1   | 450.00  | Food          | 02  | Groceries         |
| 2   | 120.00  | Transport     | 04  | Metro card top-up |
| 3   | 1500.00 | Bills         | 05  | Electricity bill  |
| 4   | 600.00  | Health        | 08  | Pharmacy          |
| 5   | 350.00  | Entertainment | 11  | Movie night       |
| 6   | 999.00  | Shopping      | 15  | Headphones        |
| 7   | 200.00  | Other         | 18  | NULL              |
| 8   | 275.00  | Food          | 21  | Dinner out        |

_(v1 said "dates spread across current month" — non-deterministic and untestable. This table covers all 7 categories, includes one NULL description, and is reproducible.)_

- All inserts in a single transaction; commit once at the end. If the seed fails midway, nothing is committed.

## 6. Changes to `app.py`

- Import `get_db`, `init_db`, `seed_db`, `close_db` from `database.db`.
- Register teardown: `app.teardown_appcontext(close_db)`.
- At module level, immediately after app creation:

```python
with app.app_context():
    init_db()
    seed_db()
```

Notes:

- Do **not** use `before_first_request` — removed in Flask 2.3+.
- Known limitation: under multi-worker servers (e.g., gunicorn) each worker runs this block; `IF NOT EXISTS` and the seed idempotency check make it safe, though a race on first-ever boot is theoretically possible. Acceptable for this project stage; note for production hardening.

## 7. Files to Change

- `database/db.py` — implement all four functions
- `app.py` — imports, teardown registration, startup block

## 8. Files to Create

None.

## 9. Dependencies

No new pip packages. Use `sqlite3` (standard library) and `werkzeug.security` (already installed).

## 10. Categories (Fixed List)

Exactly: `Food`, `Transport`, `Bills`, `Health`, `Entertainment`, `Shopping`, `Other` — enforced by the CHECK constraint in Section 4.

## 11. Rules for Implementation

- No ORMs (no SQLAlchemy).
- Parameterized queries only (`?` placeholders). Never build SQL with string formatting or f-strings.
- `PRAGMA foreign_keys = ON` on every connection (it is per-connection in SQLite).
- Round amounts to 2 decimal places before insert.
- Normalize emails (lowercase, strip) before insert.
- Dates always `YYYY-MM-DD`.
- `seed_db()` must be idempotent per the demo-email check.
- All seed inserts in one transaction.

## 12. Expected Behavior

- `get_db()` returns a connection with dict-like row access and FK enforcement, reused within an app context, and closed automatically at context teardown.
- `init_db()` creates schema safely and is repeat-safe.
- `seed_db()` inserts demo data exactly once, regardless of how many times it runs.
- Database enforces: unique case-insensitive email, valid FK relationships, positive amounts, valid category values, date format.

## 13. Error Handling Expectations

- Duplicate email (any casing) → `sqlite3.IntegrityError` (UNIQUE).
- Expense with invalid `user_id` → `sqlite3.IntegrityError` (FK).
- Category outside the fixed list → `sqlite3.IntegrityError` (CHECK).
- Non-positive amount → `sqlite3.IntegrityError` (CHECK).
- Do not swallow exceptions in `db.py`; let them propagate for debugging.

## 14. Definition of Done (verifiable)

- [ ] `spendly.db` exists after `python app.py` starts.
- [ ] `sqlite3 spendly.db ".schema"` shows both tables with all constraints and the index.
- [ ] `SELECT email, password_hash FROM users` shows the demo user with a hash (not `demo123` plaintext).
- [ ] `SELECT COUNT(*) FROM expenses` returns 8; `SELECT COUNT(DISTINCT category) FROM expenses` returns 7.
- [ ] Restarting the app twice → counts unchanged (still 1 user, 8 expenses).
- [ ] `INSERT INTO users (name,email,password_hash) VALUES ('X','DEMO@SPENDLY.COM','x')` fails with UNIQUE violation.
- [ ] `INSERT INTO expenses (user_id,amount,category,date) VALUES (999,10,'Food','2026-07-01')` fails with FK violation.
- [ ] `INSERT INTO expenses (user_id,amount,category,date) VALUES (1,10,'Gadgets','2026-07-01')` fails with CHECK violation.
- [ ] Grep `db.py` and `app.py`: no f-strings or `%`/`.format()` inside SQL strings.
- [ ] App starts and serves existing placeholder routes without errors.
