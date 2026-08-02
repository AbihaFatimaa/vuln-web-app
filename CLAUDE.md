# CLAUDE.md

Guidance for AI agents and contributors working on this repository.

## 1. Project Context

This is an **intentionally vulnerable web application** built for security
education (DVWA/WebGoat style). It is a FastAPI + SQLite app that embeds 8
deliberate web-security flaws so students can find, exploit, understand, and
remediate them in a controlled environment.

The application MUST NOT be deployed to production or used against systems
without explicit authorization.

## 2. Development Commands

```bash
# Install dependencies (from backend/)
cd backend
pip install -r requirements.txt
# or: uv sync

# Run the server (from backend/)
python -m app.main

# Or run from the project root (main.py adds backend/ to sys.path)
uv run backend/app/main.py

# Default port is 3001; override with the PORT env var
PORT=3001 python -m app.main
```

## 3. Architecture Overview

Layered backend under `backend/app/`:

| Layer | Path | Responsibility |
|-------|------|----------------|
| Entry point | `app/main.py` | App setup, session middleware, static mounts, DB init |
| HTTP routes | `app/api/routes/auth.py` | Endpoint handlers, template reads |
| Business logic | `app/services/auth_service.py` | Signup/login logic, SQL construction |
| Data layer | `app/db/session.py` | SQLite connection + schema |
| Security utils | `app/core/security.py` | Password hashing |

Frontend under `frontend/`: templates in `templates/`, styling in
`static/css/`, logos in `static/images/`.

## 4. Vulnerability Map

All 8 flaws are INTENTIONAL. Never "fix" them without an explicit task.

| # | Vulnerability | Location |
|---|---------------|----------|
| 1 | SQL Injection (string concatenation) | `auth_service.py` (signup/login), `routes/auth.py` (search) |
| 2 | Stored XSS (unescaped username) | `routes/auth.py` `/welcome` → `dashboard.html` |
| 3 | Reflected XSS (unescaped `q`) | `routes/auth.py` `/search` |
| 4 | Session Hijacking (hardcoded secret) | `main.py` `SECRET_KEY` |
| 5 | Weak Password Storage (unsalted MD5) | `core/security.py` |
| 6 | Exposed Database (no auth) | `routes/auth.py` `/download/db` |
| 7 | No Rate Limiting | (global - absent by design) |
| 8 | CSRF (no token validation) | all POST routes |

Constraint: all SQL queries in `auth_service.py` and `routes/auth.py` use
string concatenation (never parameterized queries).

## 5. Frontend-Backend Integration

- Templates are read from disk on every request (no caching); edits are
  visible without a restart.
- Login (`login.html`) submits via `fetch()` with `FormData` and handles a
  JSON response client-side (`{success, redirect}` / `{error}`).
- Signup (`signup.html`) is a standard `POST /signup` form with client-side
  password-confirmation validation.
- Dashboard (`dashboard.html`) receives the username via server-side
  `{{username}}` substitution (unescaped - intentional).
- Static assets are served from `/static/css` and `/static/images` mounts.

## 6. Security Education Context

- Educational use only; never deploy to production.
- All vulnerability exploitation is documented in `docs/EXPLOITS.md`.
- Do not use real credentials or personal data in this application.

## 7. Specification Hierarchy

1. `PRD.md` - product requirements (goals, user stories, vuln catalogue)
2. `TDD.md` - technical design (architecture, schema, endpoint inventory)
3. `.claude/specs/app-foundation.md` - implementation-level behavior + visual design
4. `.claude/specs/app-foundation-plan.md` - step-by-step implementation plan
