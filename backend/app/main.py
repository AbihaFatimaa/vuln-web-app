import os
import sys

# Add the backend/ directory to sys.path so the 'app' package resolves
# correctly regardless of which directory the script is launched from
# (e.g. `uv run backend/app/main.py` from the project root, or
# `python app/main.py` from backend/).
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes.auth import router as auth_router
from app.db.session import init_db

# VULN-4 (Session Hijacking):
# Hardcoded, predictable session-signing secret. Anyone who reads the source
# can forge session cookies and hijack any user's session.
SECRET_KEY = "super-secret-key-12345"

app = FastAPI(title="Vulnerable Web Application - Security Lab", docs_url=None, redoc_url=None)

# VULN-8 (CSRF): SessionMiddleware defaults do not set SameSite=strict and
# no CSRF token validation is performed on any POST endpoint.
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_STATIC = os.path.join(PROJECT_ROOT, "frontend", "static")

app.mount(
    "/static/css",
    StaticFiles(directory=os.path.join(FRONTEND_STATIC, "css")),
    name="static-css",
)
app.mount(
    "/static/images",
    StaticFiles(directory=os.path.join(FRONTEND_STATIC, "images")),
    name="static-images",
)

app.include_router(auth_router)

# Schema is applied at import time so the database exists before the server
# accepts any request.
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3001))
    # VULN-7 (No Rate Limiting): no throttling middleware anywhere in the app.
    uvicorn.run(app, host="0.0.0.0", port=port)
