import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.db.session import DB_PATH, get_db
from app.services.auth_service import login, signup

router = APIRouter()

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    )
)
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "frontend", "templates")


def _render_template(name: str) -> HTMLResponse:
    """Read a template from disk on every request; no caching."""
    with open(os.path.join(TEMPLATES_DIR, name), encoding="utf-8") as f:
        return HTMLResponse(f.read())


@router.get("/", response_class=HTMLResponse)
def index():
    """Redirect root path to the signup page."""
    return RedirectResponse("/signup", status_code=302)


@router.get("/signup", response_class=HTMLResponse)
def signup_page():
    return _render_template("signup.html")


@router.post("/signup")
def signup_post(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    # VULN-8 (CSRF): no CSRF token is validated on this state-changing POST.
    # VULN-7 (No Rate Limiting): unlimited signup attempts.
    return signup(username, email, password)


@router.get("/login", response_class=HTMLResponse)
def login_page():
    return _render_template("login.html")


@router.post("/login")
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    # VULN-8 (CSRF): no CSRF token validation.
    # VULN-7 (No Rate Limiting): unlimited login attempts allow brute force.
    return login(request, username, password)


@router.get("/download/db")
def download_db():
    """Serve the raw SQLite database file to anyone.

    VULN-6 (Exposed Database): no authentication check on this endpoint.
    A single GET request leaks every user record and password hash.
    """
    return FileResponse(
        DB_PATH,
        media_type="application/octet-stream",
        filename="vulnerable_app.db",
    )


@router.get("/search", response_class=HTMLResponse)
def search_user(q: str = ""):
    """Search users by username or email.

    VULN-3 (Reflected XSS): the raw `q` parameter is interpolated directly
    into the HTML response without any escaping, so a URL such as
    /search?q=<script>alert(1)</script> executes immediately in the browser.
    """
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT username, email FROM users"
            " WHERE username LIKE '%" + q + "%' OR email LIKE '%" + q + "%'"
        ).fetchall()
        conn.close()
    except Exception as e:
        # Information leakage: the raw exception string is exposed.
        return HTMLResponse("<h2>Search error</h2><pre>" + str(e) + "</pre>")

    html = "<h2>Search results for: " + q + "</h2><ul>"
    for row in rows:
        html += f"<li>{row[0]} ({row[1]})</li>"
    html += "</ul><a href='/welcome'>Back to dashboard</a>"
    return HTMLResponse(html)


@router.get("/welcome", response_class=HTMLResponse)
def welcome_page(request: Request):
    """Protected dashboard, reachable only with an active session."""
    if "user_id" not in request.session:
        return RedirectResponse("/login")

    with open(os.path.join(TEMPLATES_DIR, "dashboard.html"), encoding="utf-8") as f:
        content = f.read()

    # VULN-2 (Stored XSS): the username is substituted into the page with a
    # blind string replace and no HTML escaping. A username containing a
    # <script> payload persists in the database and executes in the browser
    # of anyone who views this dashboard.
    content = content.replace("{{username}}", request.session.get("username", ""))
    return HTMLResponse(content)


@router.get("/logout")
def logout(request: Request):
    """Clear the session and redirect to login."""
    request.session.clear()
    return RedirectResponse("/login")
