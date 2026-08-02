from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core.security import hash_password
from app.db.session import get_db


def signup(username: str, email: str, password: str):
    """Register a new user account.

    Returns a RedirectResponse to /login on success (standard form POST flow).
    """
    if not (username and email and password):
        return HTMLResponse(
            "<h3>All fields are required</h3><a href='/signup'>Try again</a>",
            status_code=400,
        )

    hashed = hash_password(password)
    conn = get_db()
    try:
        # VULN-1 (SQL Injection): raw string concatenation. The username and
        # email fields are inserted directly into the query, so crafted input
        # can alter the SQL being executed.
        conn.execute(
            "INSERT INTO users (username, email, password) VALUES ('"
            + username
            + "', '"
            + email
            + "', '"
            + hashed
            + "')"
        )
        conn.commit()
    except Exception:
        conn.close()
        # VULN-8 (CSRF) / info leakage: reveals whether the username exists.
        return HTMLResponse(
            "<h3>Username already exists!</h3><a href='/signup'>Try again</a>",
            status_code=400,
        )
    conn.close()
    return RedirectResponse("/login", status_code=303)


def login(request: Request, username: str, password: str):
    """Authenticate a user and establish a session.

    Returns a JSONResponse so the login form can handle the result with
    fetch() client-side, without a page reload.
    """
    if not (username and password):
        return JSONResponse({"error": "Username and password are required"}, status_code=401)

    hashed = hash_password(password)
    conn = get_db()
    # VULN-1 (SQL Injection): string concatenation in the WHERE clause.
    # Payloads like `' OR '1'='1' --` bypass the password check entirely.
    query = (
        "SELECT * FROM users WHERE username = '"
        + username
        + "' AND password = '"
        + hashed
        + "'"
    )
    row = conn.execute(query).fetchone()
    conn.close()

    if row:
        request.session["user_id"] = row["id"]
        request.session["username"] = row["username"]
        request.session["email"] = row["email"]
        return JSONResponse({"success": True, "redirect": "/welcome"})
    return JSONResponse({"error": "Invalid username or password"}, status_code=401)
