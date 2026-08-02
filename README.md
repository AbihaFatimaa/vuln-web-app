# Vulnerable Web Application - Security Lab

An intentionally insecure web application built for hands-on security education.
It demonstrates **8 real-world web security flaws** based on the OWASP Top 10.
Use it to practice identifying, exploiting, and then fixing common vulnerabilities
in a safe, controlled environment.

> **WARNING: This application is deliberately insecure.**
> It must never be deployed to production, exposed to the public internet,
> or used against systems you do not own or have explicit permission to test.
> Educational use only.

---

## Quick Start

Prerequisites: Python 3.9+, pip/uv.

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt
# or: uv sync

# 2. Run the application
python -m app.main

# 3. Open the app
# http://localhost:3001
```

The port is configurable via the `PORT` environment variable (default `3001`).

---

## Project Structure

```
.
├── backend/
│   └── app/
│       ├── main.py                 # Entry point (weak session secret - VULN-4)
│       ├── core/
│       │   └── security.py         # MD5 password hashing (VULN-5)
│       ├── db/
│       │   └── session.py          # SQLite connection & schema
│       ├── services/
│       │   └── auth_service.py     # Auth logic, raw SQL concatenation (VULN-1)
│       └── api/
│           └── routes/
│               └── auth.py         # HTTP routes (VULN-2/3/6/7/8)
├── frontend/
│   ├── templates/                  # login.html, signup.html, dashboard.html
│   └── static/                     # styles.css, university logos
├── docs/
│   └── EXPLOITS.md                 # Step-by-step exploitation guide
└── PRD.md, TDD.md                  # Product and technical design docs
```

---

## The 8 Intentional Vulnerabilities

| # | Vulnerability | OWASP Category | Location | Severity |
|---|---------------|----------------|----------|----------|
| 1 | SQL Injection | A03 Injection | `services/auth_service.py` | Critical |
| 2 | Stored XSS | A03 Injection | `api/routes/auth.py` dashboard render | High |
| 3 | Reflected XSS | A03 Injection | `api/routes/auth.py` search endpoint | High |
| 4 | Session Hijacking | A07 ID/Auth Failures | `main.py` hardcoded secret | High |
| 5 | Weak Password Storage | A02 Crypto Failures | `core/security.py` MD5 | High |
| 6 | Exposed Database | A01 Broken Access Control | `api/routes/auth.py` `/download/db` | Critical |
| 7 | No Rate Limiting | A07 ID/Auth Failures | (global, missing) | Medium |
| 8 | CSRF | A01 Broken Access Control | (all POST endpoints) | Medium |

See `docs/EXPLOITS.md` for the full walkthrough of each vulnerability,
including root cause and remediation.

---

## API Endpoints

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/` | Redirect to signup | No |
| GET | `/signup` | Registration form | No |
| POST | `/signup` | Create account | No |
| GET | `/login` | Login form | No |
| POST | `/login` | Authenticate | No |
| GET | `/welcome` | Protected dashboard | Yes |
| GET | `/logout` | End session | No |
| GET | `/search?q=...` | Search users | No (vulnerable) |
| GET | `/download/db` | Download SQLite database | No (vulnerable) |

---

## Database

- SQLite file: `backend/vulnerable_app.db` (created automatically on first run)
- Delete the file and restart to reset all data.

Inspect stored data:

```bash
python -c "import sqlite3; c=sqlite3.connect('vulnerable_app.db'); [print(r) for r in c.execute('SELECT * FROM users')]; c.close()"
```

---

## License & Ethical Use

Provided strictly for education. Unauthorized access to computer systems is
illegal. Only test systems you own or have explicit permission to test.
The authors are not responsible for misuse.
