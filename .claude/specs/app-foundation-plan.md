# Implementation Plan: Vulnerable Web Application (app-foundation)

**Version:** 1.0.0
**Status:** Approved for implementation
**Inputs read:** `PRD.md`, `TDD.md`, `.claude/specs/app-foundation.md`

---

## Purpose

This document is a step-by-step implementation plan for producing the
intentionally vulnerable web application described in `PRD.md` and `TDD.md`,
built to the implementation behavior and visual design captured in
`.claude/specs/app-foundation.md`. It is a planning artifact only.

The application is a security education lab (DVWA/WebGoat style) that must
contain exactly these 8 deliberate vulnerabilities:

1. **SQL Injection** in login and signup via string concatenation
2. **Stored XSS** via unescaped username rendered on the dashboard
3. **Reflected XSS** via unescaped query parameter in the search response
4. **Session Hijacking** via a hardcoded weak session secret key
5. **Weak Password Storage** via unsalted MD5 hashing
6. **Exposed Database** via an unauthenticated `/download/db` endpoint
7. **No Rate Limiting** on any endpoint
8. **CSRF** via missing token validation on all forms

> **Ethical note:** These vulnerabilities are INTENTIONAL for education. The
> application must never be deployed to production or used against systems
> without authorization. The plan records the flawed implementation as
> specified; remediation is documented separately in `docs/EXPLOITS.md`.

> **Implementation constraint for all phases:** Every SQL query in
> `auth_service.py` and `routes/auth.py` MUST be built via string
> concatenation (never parameterized queries). This is the root cause of the
> SQL Injection vulnerability and must be preserved.

---

## Phase 1: Project Structure

Create the directory skeleton and packaging metadata. No logic yet.

### 1.1 Backend directory structure

Create these files (empty `__init__.py` files are literally empty):

```
backend/
├── pyproject.toml
└── app/
    ├── main.py                     # Application entry point (Phase 6)
    ├── __init__.py                 # empty
    ├── core/
    │   ├── __init__.py             # empty
    │   └── security.py             # Password hashing (Phase 3)
    ├── db/
    │   ├── __init__.py             # empty
    │   └── session.py              # SQLite connection layer (Phase 2)
    ├── services/
    │   ├── __init__.py             # empty
    │   └── auth_service.py         # Auth business logic (Phase 4)
    └── api/
        ├── __init__.py             # empty
        └── routes/
            ├── __init__.py         # empty
            └── auth.py             # HTTP route handlers (Phase 5)
```

### 1.2 `backend/pyproject.toml`

Use the **hatchling** build system. Declare these dependencies:

| Package | Constraint | Purpose |
|---------|-----------|---------|
| `fastapi` | `>=0.109.0` | Web framework and routing |
| `uvicorn` | `>=0.27.0` | ASGI server |
| `python-multipart` | `>=0.0.6` | Form parameter parsing |
| `itsdangerous` | `>=2.0.0` | Session cookie signing |

Include `pytest` as an **optional dev dependency** under
`[project.optional-dependencies].dev` (no runtime tests are required by the
product, only the verification steps in Phase 10).

### 1.3 Frontend directory structure

The `frontend/static/images/` directory already contains the three logo files
(`PUCIT_Logo.png`, `blue-logo-scl2.png`, `excaliat-logo.png`). Create:

```
frontend/
├── templates/
│   ├── login.html                  # (Phase 7)
│   ├── signup.html                 # (Phase 7)
│   └── dashboard.html              # (Phase 7)
└── static/
    ├── css/
    │   └── styles.css              # (Phase 8)
    └── images/                     # logo files (already present)
```

### 1.4 Deliverable

The complete skeleton shown above, with empty module markers and the
`pyproject.toml` metadata. Nothing functional yet.

---

## Phase 2: Database Layer

**File to create:** `backend/app/db/session.py`

### 2.1 Connection factory

- Compute `DB_PATH` pointing to `vulnerable_app.db` at the **project root**.
- `get_db()` returns a `sqlite3.Connection` opened on `DB_PATH` with:
  - `check_same_thread=False` (connection shared across threads)
  - `conn.row_factory = sqlite3.Row` (dict-style column access)

### 2.2 Schema initialization

`init_db()` executes with `CREATE TABLE IF NOT EXISTS`:

```sql
CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email    TEXT,
    password TEXT
);
```

- Commits and closes the connection.
- Idempotent: safe to run on every startup.

### 2.3 Key implementation details

- `username TEXT UNIQUE` is the database-level uniqueness mechanism (see
  Business Rule 6 in the spec).
- No connection pooling; one connection opened per call.
- The schema definition (column semantics) is documented in `TDD.md`; do not
  duplicate rationale here.

---

## Phase 3: Security Utilities

**File to create:** `backend/app/core/security.py`

### 3.1 Functions

Implement two functions using `hashlib.md5` **without salt** (this is
Vulnerability #5 - Weak Password Storage):

- `hash_password(password: str) -> str`
  - Returns the MD5 hexdigest of the UTF-8-encoded password.
- `verify_password(plain: str, hashed: str) -> bool`
  - Hashes `plain` with the same MD5 routine and compares hexdigests.

### 3.2 Key implementation details

- No salt, no pepper, no key-derivation function (deliberate).
- Hexadecimal digest returned/stored (64-char hex for MD5 is actually 32
  chars - use the hexdigest format produced by `hashlib.md5`).
- This module is a thin wrapper; the intentional weakness must not be
  "fixed" during implementation.

---

## Phase 4: Business Logic

**File to create:** `backend/app/services/auth_service.py`

Import `hash_password` from `core.security` and `get_db` from `db.session`.

### 4.1 `signup(username, email, password)`

1. Receives `username`, `email`, `password` (from `Form` params in Phase 5).
2. Validates that all three fields are present and non-empty.
3. Hashes the password with `hash_password()`.
4. Builds the INSERT query via **STRING CONCATENATION** (Vulnerability #1):

   ```python
   "INSERT INTO users (username, email, password) VALUES ('"
   + username + "', '" + email + "', '" + hashed + "')"
   ```

5. Executes and commits.
6. On success: returns `RedirectResponse` to `/login`.
7. Catches the UNIQUE constraint exception: returns "Username already exists"
   as an HTML error response (status 400) with a link back to `/signup`.

### 4.2 `login(request, username, password)`

1. Receives the `request` object plus `username`, `password`.
2. Validates that fields are present.
3. Hashes the supplied password with `hash_password()`.
4. Builds the SELECT query via **STRING CONCATENATION** (Vulnerability #1):

   ```python
   "SELECT * FROM users WHERE username = '"
   + username + "' AND password = '" + hashed + "'"
   ```

5. Executes and fetches one row.
6. **On match:** writes `user_id`, `username`, `email` into
   `request.session`; returns `JSONResponse({"success": true, "redirect":
   "/welcome"})` so the frontend JS can navigate with
   `window.location.href`.
7. **On failure:** returns `JSONResponse` with status `401` and an `error`
   message (e.g. "Invalid username or password") so the frontend JS can show
   the error inline without a page reload.

### 4.3 Key implementation details

- Response formats differ between the two functions (registration = HTML
  errors/redirects; login = JSON) - this is a deliberate, documented behavior
  (Business Rule 4 in the spec).
- The concatenated queries are the single source of Vulnerability #1; do not
  refactor them into parameterized queries.

---

## Phase 5: Route Handlers

**File to create:** `backend/app/api/routes/auth.py`

Define a single `APIRouter`. Import `FileResponse`, `HTMLResponse`,
`RedirectResponse`, `Request`, `Form`, `get_db`/`DB_PATH`, and the
`signup`/`login` service functions. Resolve `TEMPLATES_DIR` to
`frontend/templates/`.

### 5.1 Route registry

| Method | Path | Handler behavior |
|--------|------|------------------|
| GET | `/` | `RedirectResponse` to `/signup` (302) |
| GET | `/signup` | Read `signup.html` from disk; return `HTMLResponse` |
| POST | `/signup` | Extract `username`, `email`, `password` via `Form(...)`; call `auth_service.signup()` |
| GET | `/login` | Read `login.html` from disk; return `HTMLResponse` |
| POST | `/login` | Extract `username`, `password` via `Form(...)`; call `auth_service.login()` passing the `request` object |
| GET | `/download/db` | `FileResponse` serving `vulnerable_app.db` with **NO authentication check** (Vulnerability #6) |
| GET | `/search?q=` | See 5.2 (Vulnerability #3) |
| GET | `/welcome` | See 5.3 (Vulnerability #2) |
| GET | `/logout` | `request.session.clear()`; `RedirectResponse` to `/login` |

### 5.2 `GET /search?q=`

- Accept optional `q` query parameter.
- Build SQL via **STRING CONCATENATION** with `LIKE` patterns:

  ```python
  "SELECT username, email FROM users WHERE username LIKE '%"
  + q + "%' OR email LIKE '%" + q + "%'"
  ```

- Return an `HTMLResponse` that lists matching users.
- The `q` value is **interpolated into the HTML response without escaping**
  (Vulnerability #3 - Reflected XSS).
- Wrap execution in a try/except; on exception return an error string that
  exposes `str(e)` (information leakage, consistent with the vulnerable
  design).

### 5.3 `GET /welcome`

- Check `'user_id' in request.session`; if missing, `RedirectResponse` to
  `/login`.
- Read `dashboard.html` from disk.
- Perform `html.replace('{{username}}', username)` using the session's
  username - **no HTML escaping** (Vulnerability #2 - Stored XSS sink).
- Return the substituted HTML as `HTMLResponse`.

### 5.4 Key implementation details

- Templates are read from disk on every request; no caching.
- The `/download/db` endpoint must not call any auth logic.
- No CSRF tokens are generated or validated on any POST route (Vulnerability
  #8) and no rate-limiting middleware exists (Vulnerability #7).

---

## Phase 6: Application Entry Point

**File to create:** `backend/app/main.py`

### 6.1 Import path fix

At the top of `main.py`, insert the `backend/` directory into `sys.path`
before importing the `app` package, so `app` resolves correctly regardless of
launch directory, for example:

- `uv run backend/app/main.py` from the project root, or
- `python app/main.py` from `backend/`.

### 6.2 Application setup

1. Import `FastAPI` and `StaticFiles`.
2. Create the app: `app = FastAPI(title=..., docs_url=None, redoc_url=None)`.
3. Add `SessionMiddleware` with **hardcoded**
   `SECRET_KEY = "super-secret-key-12345"` (Vulnerability #4 - Session
   Hijacking).
4. `app.include_router(auth_router)`.
5. Mount static directories:
   - `/static/css` -> `frontend/static/css`
   - `/static/images` -> `frontend/static/images`
6. Call `init_db()` at module level (schema applied on import).

### 6.3 Server bootstrap

```python
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3001))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

- Default port 3001; overridable via the `PORT` environment variable.

### 6.4 Key implementation details

- The hardcoded secret must not be read from an environment variable (it is
  intentionally fixed in source).
- `init_db()` at module level guarantees the schema exists before the server
  accepts requests.

---

## Phase 7: Frontend Templates

**Files to create:**
- `frontend/templates/login.html`
- `frontend/templates/signup.html`
- `frontend/templates/dashboard.html`

### 7.1 Shared header (all three pages)

A fixed header with the app title on the **left** and the three organizational
logos on the **right** (rendered ~54x54px), styled per the spec (Section 5.2).

### 7.2 `login.html`

- Split-screen layout: left decorative panel (deep blue gradient with
  Security Lab content, badge, welcome heading, description, bullet list,
  ~7% opacity white circles), right white panel with the login form
  (max width ~400px).
- Form fields: username, password.
- Client-side JS: on submit, use `fetch()` to POST `/login` with `FormData`
  (content type `application/x-www-form-urlencoded`).
- Process the JSON response:
  - On success (`data.success`): navigate with `window.location.href =
    data.redirect` (to `/welcome`).
  - On failure: render `data.error` in the inline error area; no page
    reload.

### 7.3 `signup.html`

- Same split-screen layout (identical gradient and decorative circles).
- Standard HTML form: `action="/signup"` `method="POST"`.
- Four fields: `username`, `email`, `password`, `confirm_password`.
- Client-side JS validates password match **before submit**; on mismatch
  shows an inline error span below the confirm field and aborts submission.

### 7.4 `dashboard.html`

- Blue gradient banner: "Security Vulnerability Lab" title, subtitle, and on
  the right "Logged in as {{username}}" plus a logout button (links to
  `/logout`).
- The `{{username}}` placeholder is the substitution target for
  Vulnerability #2.
- Content area (max ~1100px centered):
  - Mission card (section title + description).
  - "Vulnerabilities to Discover" section: 8 vulnerability cards in a
    two-column grid, each with a colored pill tag and description.
  - Three process step cards (Find, Exploit, Mitigate) with circular
    numbered badges on a `#1a237e` background.

### 7.5 Key implementation details

- Login uses async fetch (no reload); signup uses a standard form post.
- All pages link `/static/css/styles.css` and reference the logo files under
  `/static/images/`.

---

## Phase 8: Styling

**File to create:** `frontend/static/css/styles.css`

Implement the complete visual design specification from the spec document
(Section 5), including:

- Global design system: font stack, typography scale (main titles 2rem/800,
  section titles 1.4rem/700, form titles 1.7rem/700, card titles 0.95rem/700,
  body 0.9rem/400, labels 0.82rem/600, buttons 1rem/600).
- Primary colors: `#1a237e`, `#3949ab`, `#283593`, `#0f172a`, `#eef1f8`,
  `#ffffff`.
- Text colors: `#1e293b`, `#475569`, `#64748b`, `#c5cae9`, `#1a237e`.
- Border radius: inputs 8px, buttons 8px, cards 10-12px, status tags 6px.
- Shadows: header `0 2px 10px rgba(26,35,126,0.08)`, card hover
  `0 4px 16px rgba(26,35,126,0.10)`, input focus glow
  `0 0 0 3px rgba(57,73,171,0.12)`.
- Shared header: fixed, 70px, white, bottom border, subtle shadow.
- Login/signup split-screen: left gradient `#0d1b5e -> #1a237e -> #283593`,
  right white panel.
- Input styling: `#f8f9ff` background, 1.5px solid `#c5cae9` border, focus
  to `#3949ab` with blue glow.
- Error messages: light red background, red border, dark red text.
- Dashboard: `#eef1f8` body, hero banner gradient `#1a237e -> #3949ab`,
  mission card, two-column vuln card grid with tag colors (SQLi=yellow,
  XSS=red, Session=purple, Brute=orange, Crypto=green, Exposed=blue,
  CSRF=pink), process step cards with `#1a237e` background and circular
  numbered badges.
- Responsive: split-screen stacks vertically on mobile, dashboard cards
  single-column, process steps vertical, header logos shrink.

---

## Phase 9: CLAUDE.md

**File to create:** `CLAUDE.md` at the project root.

Document, for future agents and contributors:

1. **Project context** - what the app is and its educational purpose.
2. **Development commands** - dependency install, running the server
   (`python -m app.main` from `backend/` or via `uv`), port configuration.
3. **Architecture overview** - the layered structure (routes -> services ->
   db/core) and where each layer lives.
4. **Vulnerability map** - the 8 intentional flaws and their exact file
   locations.
5. **Frontend-backend integration** - how the templates, fetch-based login,
   and static mounts connect to the backend routes.
6. **Security education context** - warnings about ethical use, no
   production deployment.
7. **Specification hierarchy** - the relationship between `PRD.md`, `TDD.md`,
   `.claude/specs/app-foundation.md`, and this plan.

---

## Phase 10: Testing and Validation

No test files are created; validation is manual/scripted against the running
app per the spec's Section 16 test cases.

### 10.1 Startup verification

1. Install dependencies (`pip install -r requirements.txt` or `uv sync`).
2. Start the app (`python -m app.main` from `backend/`).
3. Confirm the server binds to `0.0.0.0:3001` and the `users` table is
   created (auto DB init).
4. Verify all pages load with HTTP 200:
   - `/login`
   - `/signup`
   - `/welcome` (redirects to `/login` when unauthenticated)
5. Verify static assets load: `/static/css/styles.css`,
   `/static/images/PUCIT_Logo.png`.

### 10.2 Functional flows

6. **Signup end-to-end:** submit a valid unique username -> redirected to
   `/login`. Submit a duplicate username -> "Username already exists" error.
   Mismatched passwords -> inline error, no request.
7. **Login end-to-end:** correct credentials -> redirect to `/welcome`.
   Incorrect credentials -> JSON 401 error shown inline without reload.
8. **Session protection:** unauthenticated `/welcome` redirects to `/login`;
   authenticated request renders the dashboard with the username injected.
9. **Logout:** clears the session; `/welcome` redirects to `/login`
   afterwards.

### 10.3 Vulnerability spot-checks

10. **`/download/db`** serves the SQLite file without authentication
    (Vulnerability #6).
11. **`/search`** reflects the `q` parameter unescaped in the HTML response
    (Vulnerability #3); confirm `str(e)` is exposed on a malformed query.
12. **SQL injection** - the login `' OR '1'='1' --` payload bypasses
    authentication (Vulnerability #1).
13. **Stored XSS** - a username containing markup is rendered unescaped on
    the dashboard (Vulnerability #2).
14. **Session secret** - the hardcoded key is present in source
    (Vulnerability #4); MD5 hashes visible in the downloaded DB
    (Vulnerability #5); rapid repeated logins are not throttled
    (Vulnerability #7); POSTs succeed with no CSRF token (Vulnerability #8).

### 10.4 Persistence

15. Create a user, restart the server, log in again - the record persists.

### 10.5 Acceptance

Cross-check results against Acceptance Criteria AC-01 through AC-06 and test
cases TC-01 through TC-15 in the spec (Sections 15-16).

---

## Deliverables Summary

| Phase | Artifact(s) |
|-------|-------------|
| 1 | Backend skeleton + `backend/pyproject.toml`; frontend template/static directories |
| 2 | `backend/app/db/session.py` |
| 3 | `backend/app/core/security.py` |
| 4 | `backend/app/services/auth_service.py` |
| 5 | `backend/app/api/routes/auth.py` |
| 6 | `backend/app/main.py` |
| 7 | `frontend/templates/login.html`, `signup.html`, `dashboard.html` |
| 8 | `frontend/static/css/styles.css` |
| 9 | `CLAUDE.md` |
| 10 | Verification run (no files) |

All 8 intentional vulnerabilities are realized across Phases 3-6 by design;
string concatenation in SQL construction is the explicit implementation
constraint for `auth_service.py` and `routes/auth.py`.

---

**Plan End**
