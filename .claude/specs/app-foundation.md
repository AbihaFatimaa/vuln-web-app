# Software Specification Document (Implementation Addendum)

**Version:** 1.0.0
**Applies to:** The Vulnerable Web Application (security education lab)
**Companion documents:** `PRD.md`, `TDD.md`, `docs/EXPLOITS.md`

---

## 1. Scope

This document is an implementation addendum. It captures only the
implementation-level behavior required to reproduce the application exactly:
runtime behavior, user flows, functional behavior, visual design, form
behavior, validation, session state, data lifecycle, success/alternate paths,
edge cases, business rules, rebuild requirements, acceptance criteria, and
test cases.

Intentionally omitted — these are already fully documented in `PRD.md` and
`TDD.md` and are NOT repeated here:

- Product goals, value propositions, target audience, and user stories
- Architecture diagrams and technology stack rationale
- Vulnerability descriptions, root causes, and exploitation steps
- Database schema definitions (`users` table column semantics)
- Endpoint inventories and route tables
- OWASP severity matrices and learning outcomes

Where a discrepancy exists between this addendum and the companion
documents, the implementation-level reality recorded here governs rebuilds.
Known discrepancies are cataloged in Section 17.

---

## 2. Runtime Behavior

The following behaviors must hold for any faithful rebuild:

1. **Automatic database initialization on startup.** When the application
   process starts, the `users` table is created if it does not already exist.
   No manual schema migration step is required.
2. **Missing database file recreated automatically.** If the SQLite file is
   absent when the process boots, a new empty file is created and the schema
   is applied. The application starts successfully with a fresh, empty
   database.
3. **Data preserved across restarts.** User records persist in the SQLite
   file between process restarts. Restarting the server does not clear or
   reseed user data.
4. **Static assets available after boot.** CSS and image files are served
   from disk through a static file mount. No pre-compilation or build step
   is required; assets are resolvable immediately after the server starts.
5. **Templates loaded from disk at request time with no caching.** Each
   request that returns an HTML page re-reads the template file from the
   filesystem. There is no in-memory template cache, no template engine
   compilation, and no bundling. Edits to a template take effect on the next
   request without a server restart.
6. **Dashboard content modified via runtime string substitution before
   response.** The dashboard template is read from disk, a single
   `{{username}}` placeholder is replaced with the current session's
   username via plain string substitution, and the resulting HTML is sent.
   No escaping is applied during substitution.
7. **Authentication state based solely on session presence.** A request is
   considered authenticated if and only if the `user_id` key is present in
   the request's session object. There is no token store, no server-side
   session table, and no additional credential check on subsequent requests.

---

## 3. User Flows

### 3.1 Registration

1. User navigates to `/signup`; the `signup.html` template is read from disk
   and served as an HTML response.
2. User fills the username, email, password, and confirm-password fields.
3. Client-side validation runs on submit: password and confirm-password must
   match; if they do not, a red message is shown inline and no request is
   sent.
4. On valid input, the client sends an asynchronous `fetch` POST to `/signup`
   with `application/x-www-form-urlencoded` body.
5. The server creates the user record (hash + insert).
6. On success the server responds with a `303 See Other` redirect to
   `/login`; the client follows it and the login page is displayed.

### 3.2 Login

1. User navigates to `/login`; the `login.html` template is read from disk
   and served.
2. User fills the username and password fields.
3. The client intercepts form submission and sends an asynchronous `fetch`
   POST to `/login` with `application/x-www-form-urlencoded` body. The page
   does not reload.
4. The client processes the response:
   - If the response is a redirect, the browser is navigated to the
     redirected URL (the dashboard).
   - If the response is a JSON error body, the error message is displayed in
     the inline error area.
5. On success, the server has set the session cookie and the dashboard is
   shown.

### 3.3 Dashboard

1. Browser requests `/welcome`.
2. Server checks for `user_id` in the request session.
3. If absent, the server responds with a redirect to `/login`; the flow ends.
4. If present, the server reads `dashboard.html` from disk.
5. The server replaces the `{{username}}` placeholder with the session
   username via string substitution (no escaping).
6. The server returns the modified HTML as the response.

### 3.4 Logout

1. User clicks the logout control on the dashboard.
2. Server clears the session (removes all session keys) and sets the session
   cookie to an expired/deleted state.
3. Server responds with a redirect to `/login`.
4. Subsequent requests to `/welcome` fail the session-presence check and
   redirect back to `/login`; protected resources are inaccessible without a
   valid session.

---

## 4. Functional Requirements

### FR-01: Session Management

- Sessions are managed via signed client-side cookies handled by the web
  framework's session middleware.
- A session is created when a valid login completes; the keys `user_id`,
  `username`, and `email` are stored in the session.
- A session is destroyed on logout by clearing all session data.
- Authentication checks are based solely on the presence of `user_id` in the
  session.

### FR-02: Dynamic User Context

- The dashboard must display the authenticated user's username.
- The username is injected into the dashboard HTML by replacing the literal
  placeholder `{{username}}` with the session's `username` value at request
  time, before the response is returned.
- The substitution must be a plain string replacement with no HTML escaping.

### FR-03: Route Protection

- The `/welcome` route is protected. Any request without `user_id` in the
  session is redirected to `/login`.
- A successful login must result in a redirect to `/welcome`.
- A successful logout must result in a redirect to `/login`.

### FR-04: Error Handling

- Failed registration (duplicate username) returns an HTML error response
  with status 400 containing a "Username already exists!" message and a link
  back to signup.
- Failed login returns a JSON response with status 401 containing an `error`
  field ("Invalid username or password").
- Client-side form logic must surface these errors in the page without a
  full reload where applicable.

### FR-05: Search Processing

- A `/search` endpoint accepts a `q` query parameter.
- It queries user records matching `q` against both the username and email
  fields using `LIKE` patterns.
- Results are rendered as an HTML response: a heading that echoes the query
  parameter, and a list of matching users.
- The query parameter is interpolated into the response with no escaping.

### FR-06: Persistence

- User records persist in a SQLite file on disk.
- The database file and its contents survive process restarts.
- A missing database file is recreated automatically on the next startup with
  the schema applied.

---

## 5. Complete Visual Design Specification

### 5.1 Global Design System

#### 5.1.1 Typography

- Font stack: `Segoe UI`, `system-ui`, `-apple-system`, `sans-serif`.
- No webfonts are loaded; the system font stack renders everywhere.

#### 5.1.2 Typography Scale

| Element | Size | Weight |
|---------|------|--------|
| Main titles (hero/welcome heading) | 2rem | 800 |
| Section titles | 1.4rem | 700 |
| Form titles | 1.7rem | 700 |
| Card titles | 0.95rem | 700 |
| Body text | 0.9rem | 400 |
| Form labels | 0.82rem | 600 |
| Buttons | 1rem | 600 |

#### 5.1.3 Primary Colors

| Role | Hex |
|------|-----|
| Primary dark (buttons, brand) | `#1a237e` |
| Primary (accents, links) | `#3949ab` |
| Primary darker (hover) | `#283593` |
| Ink (near-black text) | `#0f172a` |
| Page background | `#eef1f8` |
| Surfaces (cards, panels) | `#ffffff` |

#### 5.1.4 Text Colors

| Role | Hex |
|------|-----|
| Body text | `#1e293b` |
| Secondary text | `#475569` |
| Muted text | `#64748b` |
| Input borders | `#c5cae9` |
| Brand/link text | `#1a237e` |

#### 5.1.5 Border Radius

| Element | Radius |
|---------|--------|
| Inputs | 8px |
| Buttons | 8px |
| Cards | 10-12px |
| Status tags (pills) | 6px |

#### 5.1.6 Shadows

| Element | Shadow |
|---------|--------|
| Header | `0 2px 10px rgba(26, 35, 126, 0.08)` |
| Card hover | `0 4px 16px rgba(26, 35, 126, 0.10)` |
| Input focus glow | `0 0 0 3px rgba(57, 73, 171, 0.12)` |

### 5.2 Shared Header (all pages)

- Fixed position, pinned to the top of the viewport.
- Height: 70px.
- Background: white.
- Bottom border: 1px (subtle) and the header shadow listed above.
- Layout: app title on the left; three organizational logos on the right.
- Logos are rendered at 54x54px each, displayed side by side with spacing.

### 5.3 Login Page

- Two-column, 50/50 split-screen layout.

#### 5.3.1 Left Panel (decorative)

- Deep blue vertical gradient: `#0d1b5e` → `#1a237e` → `#283593`.
- Contains, top to bottom:
  - A badge label (small uppercase pill).
  - Welcome heading (2rem / 800, white).
  - Description paragraph.
  - Bullet list of items.
- Decorative overlays: two semi-transparent white circles at approximately
  7% opacity, positioned as large circles partially off-canvas.

#### 5.3.2 Right Panel (form)

- Background: white.
- Centered form container, maximum width 400px.
- Contains, top to bottom:
  - Form title (1.7rem / 700).
  - Subtitle line.
  - Username field.
  - Password field.
  - Error message area (hidden until a login error occurs).
  - Full-width login button: `#1a237e` background, white text.
  - Signup link beneath the button.

#### 5.3.3 Input Styling

- Background: `#f8f9ff`.
- Border: 1.5px solid `#c5cae9`.
- Border radius: 8px.
- Focus state: border changes to `#3949ab` and a blue glow (the focus shadow
  listed in 5.1.6) is applied.

#### 5.3.4 Error Message Styling

- Light red background.
- Red border.
- Dark red text.

### 5.4 Signup Page

- Structurally identical to the login page: same 50/50 split, same gradient
  on the left panel, same decorative circle overlays.
- Form contains, top to bottom:
  - Username field.
  - Email field.
  - Password field.
  - Confirm password field.
- Password-mismatch behavior: red text is displayed directly below the
  confirm field; no page reload occurs.
- Button: full-width, `#1a237e` background, white text.

### 5.5 Dashboard

#### 5.5.1 Page Background

- Body background: `#eef1f8`.

#### 5.5.2 Hero Banner

- Positioned directly beneath the fixed header.
- Gradient: `#1a237e` → `#3949ab`.
- Two-section layout:
  - Left section: page title (2rem / 800) and a subtitle line.
  - Right section: the logged-in username and a semi-transparent white
    logout button (white text on a translucent white overlay).

#### 5.5.3 Content Area

- Centered container, maximum width 1100px.
- Padding around and between sections.

#### 5.5.4 Mission Card

- White card with rounded corners and the card border.
- Contains a section title (1.4rem / 700) and a description paragraph.

#### 5.5.5 "Vulnerabilities to Discover" Section

- Uppercase, small, bold header above the grid.
- Two-column grid of 8 vulnerability cards.
- Each card: white background, rounded corners (10-12px), light border,
  hover shadow (5.1.6), colored pill tag, card title (0.95rem / 700), and a
  description.

#### 5.5.6 Vulnerability Tag Colors

| Tag | Color |
|-----|-------|
| SQLi | yellow |
| XSS | red |
| Session | purple |
| Brute | orange |
| Crypto | green |
| Exposed | blue |
| CSRF | pink |

#### 5.5.7 Process Step Cards

- Three step cards in a row: Find, Exploit, Mitigate.
- Background: `#1a237e`.
- Each card has a circular numbered badge and white text.

### 5.6 Responsive Behavior

- Desktop: auth pages render as a two-column split-screen; dashboard content
  uses the two-column card grid.
- Mobile (narrow viewport):
  - Auth pages stack vertically: the decorative left panel renders above the
    form panel.
  - Dashboard cards collapse to a single column.
  - Process step cards stack vertically.
  - Header logos shrink to fit the narrower viewport.

---

## 6. Form Specifications

### 6.1 Registration Form

- 4 inputs: username, email, password, confirm password.
- All inputs required (HTML required attribute and client-side enforcement).
- Client-side password-confirmation check runs before any request is sent:
  if password and confirm-password differ, an error message is displayed
  below the confirm field and the submit is aborted.
- On success the server responds with a redirect to `/login`.
- On duplicate username the server responds with an HTML error (status 400).

### 6.2 Login Form

- 2 inputs: username, password.
- Submitted via an asynchronous `fetch` request (no page reload).
- Success (redirect) is handled by navigating the browser to the target URL.
- Failure (JSON error body, status 401) is handled by rendering the `error`
  value in the inline error area.

---

## 7. Validation Rules

| Form | Rule |
|------|------|
| Registration | Username, email, and password are required. |
| Registration | Username uniqueness is enforced at the database level (unique constraint); a duplicate insert fails and is reported as an error. |
| Login | Username and password are required. |
| Search | The query parameter is required to produce results; behavior with an empty query is handled as defined in AP-04. |

---

## 8. Session State Model

### 8.1 Stored Values

| Key | Source | Used for |
|-----|--------|----------|
| `user_id` | users.id at login | Route protection / identity |
| `username` | users.username at login | Dashboard greeting substitution |
| `email` | users.email at login | (available but not rendered) |

### 8.2 Lifecycle

- **Creation:** after a successful login, all three keys are written to the
  session and a session cookie is issued.
- **Usage:** during each request to a protected route, the presence of
  `user_id` is checked; `username` is read to render the dashboard.
- **Destruction:** on logout, the session is cleared and the session cookie
  is expired.

---

## 9. Data Lifecycle Rules

- **Creation:** a user record is created during registration; it is the only
  write operation in the application.
- **Modification:** there is no workflow for editing or updating user
  records; records are immutable after creation.
- **Deletion:** there is no workflow for deleting user records.
- **Recovery:** there is no workflow for recovering deleted or lost records;
  a record persists until the database file is replaced or reset externally.

---

## 10. Success Paths

### SP-01: Successful Registration

1. User submits a valid, unique username with a matching password pair.
2. Server hashes the password and inserts the row.
3. Server responds with a redirect to `/login`.
4. Login page is displayed.

### SP-02: Successful Login

1. User submits an existing username with the correct password.
2. Server verifies the credentials and establishes a session.
3. Server responds with a redirect to `/welcome`.
4. Dashboard is displayed with the user's username injected.

### SP-03: Successful Dashboard Access

1. Authenticated user requests `/welcome`.
2. Session contains `user_id`.
3. Template is read from disk, username is substituted, response is returned.

### SP-04: Successful Logout

1. User requests `/logout`.
2. Session is cleared and cookie expired.
3. Server redirects to `/login`.
4. `/welcome` becomes inaccessible without a session.

---

## 11. Alternate Paths

### AP-01: Duplicate Username During Registration

- Client validation passes (password match ok), the POST is sent.
- The database unique constraint rejects the insert.
- Server returns an HTML error (status 400) stating the username already
  exists, with a link back to signup.
- No user record is created.

### AP-02: Invalid Credentials During Login

- Client sends the login POST.
- No row matches the username/password combination.
- Server returns a JSON error body (status 401) with an `error` message.
- Client renders the message in the inline error area; no redirect occurs.

### AP-03: Unauthorized Dashboard Access

- A request to `/welcome` arrives without `user_id` in the session.
- Server responds with a redirect to `/login`.
- The dashboard content is never rendered.

### AP-04: Empty Search Query

- A request to `/search` with an empty or missing `q` parameter is processed.
- The query matches broadly or returns the empty-query rendering per the
  search endpoint behavior; the query value is still echoed unescaped in the
  response heading.

---

## 12. Edge Cases

| ID | Edge Case | Expected Behavior |
|----|-----------|-------------------|
| EC-01 | Username already exists | Insert fails via unique constraint; 400 HTML error returned; no record created. |
| EC-02 | Empty registration data | Required-field validation prevents submission client-side; server also requires the fields. |
| EC-03 | Empty login data | Required-field validation prevents submission client-side; server also requires the fields. |
| EC-04 | Missing session on protected route | Redirect to `/login`; dashboard not rendered. |
| EC-05 | Corrupted/invalid session cookie | Session middleware rejects the signature; the request is treated as unauthenticated; protected routes redirect to `/login`. |
| EC-06 | Missing template file | The route attempts to read the template from disk; the request fails at read time (no cached fallback exists). |
| EC-07 | Missing database file | Recreated automatically on startup with schema applied; app boots normally. |
| EC-08 | Application restart | Data preserved in the SQLite file; schema re-applied idempotently; no reseeding. |

---

## 13. Business Rules

1. **Authentication depends on session presence.** A request is
   authenticated if and only if `user_id` exists in the session; no other
   credential verification occurs on subsequent requests.
2. **Dashboard requires runtime substitution.** The dashboard is not a
   static page; the `{{username}}` placeholder must be replaced at request
   time for the page to be meaningful.
3. **User records are immutable after creation.** No update or delete
   workflow exists; the database is write-once per user.
4. **Login and registration use different response formats.** Registration
   returns HTML errors (400), login returns JSON errors (401).
5. **Template updates are visible without restart.** Because templates are
   read from disk per request, edits render on the next request.
6. **The database constraint is the primary uniqueness mechanism.** Client
   and service-layer checks do not guarantee uniqueness; the SQLite unique
   constraint is what actually enforces it.

---

## 14. Rebuild Requirements

A compatible implementation must reproduce all of the following:

1. Auto-create the `users` table on startup and recreate a missing database
   file automatically.
2. Persist user data across restarts without reseeding.
3. Serve static assets from disk immediately after boot.
4. Read HTML templates from disk on every request, with no caching.
5. Substitute `{{username}}` into the dashboard via unescaped runtime string
   replacement.
6. Gate `/welcome` on session presence of `user_id`; redirect to `/login`
   otherwise.
7. Register users with a hash + insert; return a 303 redirect to `/login` on
   success and an HTML 400 error on duplicate username.
8. Log in users with a hash comparison query; return a 303 redirect to
   `/welcome` on success and a JSON 401 on failure.
9. Clear the session and redirect to `/login` on logout.
10. Render search results as an HTML page echoing the unescaped query
    parameter and matching username/email rows.
11. Implement the full visual design of Section 5 (header, split-screen auth
    pages, hero banner, mission card, vulnerability grid with tag colors,
    process step cards, responsive behavior).
12. Implement client-side password-confirmation for registration and
    fetch-based submission for login.
13. Store `user_id`, `username`, and `email` in the session at login.

---

## 15. Acceptance Criteria

### AC-01: Registration

- Submitting a valid unique username with matching passwords creates an
  account and redirects to `/login`.
- Submitting an existing username returns the duplicate-username error and
  creates nothing.
- Mismatched passwords are rejected client-side without a request.

### AC-02: Login

- Correct credentials create a session and redirect to `/welcome`.
- Incorrect credentials return a JSON error displayed inline; no redirect.

### AC-03: Dashboard

- An authenticated user sees the dashboard with their username substituted
  into the page.
- An unauthenticated request to `/welcome` redirects to `/login`.

### AC-04: Logout

- Logout clears the session and redirects to `/login`.
- After logout, `/welcome` redirects to `/login`.

### AC-05: Search

- `/search?q=<term>` returns an HTML page echoing the query and listing
  matching users.
- The echoed query appears unescaped in the response.

### AC-06: Persistence

- User records survive a server restart.
- A deleted/missing database file is recreated on the next startup.

---

## 16. Test Cases

| ID | Scenario | Steps | Expected Result |
|----|----------|-------|-----------------|
| TC-01 | Successful registration | Submit unique username, email, matching passwords | 303 redirect to `/login`; no error shown |
| TC-02 | Duplicate username registration | Submit a username that already exists | 400 HTML error "Username already exists!"; no new record |
| TC-03 | Password mismatch (registration) | Submit mismatched password and confirm | Red error below confirm field; no network request |
| TC-04 | Empty registration fields | Submit form with missing fields | Client blocks submission; required fields flagged |
| TC-05 | Successful login | Submit existing username + correct password | 303 redirect to `/welcome`; session cookie set |
| TC-06 | Invalid login credentials | Submit unknown user or wrong password | JSON 401 error shown inline; no redirect |
| TC-07 | Empty login fields | Submit login with missing fields | Client blocks submission; required fields flagged |
| TC-08 | Authenticated dashboard | Request `/welcome` with valid session | 200; page contains the substituted username |
| TC-09 | Unauthenticated dashboard | Request `/welcome` without session | Redirect to `/login` |
| TC-10 | Dashboard with malicious username | Log in as a user whose username contains markup | Username rendered unescaped into the dashboard HTML |
| TC-11 | Logout | Request `/logout` with active session | Session cleared; redirect to `/login` |
| TC-12 | Protected access after logout | Request `/welcome` after logout | Redirect to `/login` |
| TC-13 | Search with query | Request `/search?q=alice` | HTML page lists matching users |
| TC-14 | Search empty query | Request `/search?q=` | Page renders with empty echo and no matches |
| TC-15 | Persistence across restart | Create user, restart server, log in | User record still present; login succeeds |

---

## 17. Documentation Gaps

The following are discrepancies between `PRD.md` / `TDD.md` and the actual
implementation reality.

1. **Run command is wrong in both docs.** PRD Appendix B and TDD section 6.2
   instruct running `python app/main.py` from `backend/`. This fails with
   `ModuleNotFoundError: No module named 'app'` because running a file
   directly does not place the `backend/` directory on `sys.path`. The
   working invocation is `python -m app.main` executed from `backend/`.

2. **Database file location differs from the documented path.** PRD (10.2)
   and TDD (3.1.4, 6.4) state the SQLite file is stored at the "project
   root" as `vulnerable_app.db`. The path helper in `db/session.py` computes
   its base directory three levels above the module file, which resolves to
   the `backend/` directory. The actual file is
   `backend/vulnerable_app.db`.

3. **The documented stored-XSS payload breaks the vulnerable INSERT.** PRD
   VULN-2 documents the exploit payload `<img src=x onerror=alert('XSS')>`
   for signup. That payload contains single quotes, which terminate the
   vulnerable string-concatenated INSERT in `auth_service.py` early and cause
   a 400 error rather than a stored user. Only payloads without single quotes
   (for example `<script>alert(1)</script>`) survive signup and demonstrate
   the stored XSS.

4. **The `SECRET_KEY` environment-variable override does not exist.** TDD
   section 6.3 documents a `SECRET_KEY` environment variable that overrides
   the session secret. The implementation hardcodes the value in `main.py`
   and never reads `SECRET_KEY` from the environment, so the documented
   configuration knob is non-functional.

---

**Document End**
