# Verified Screens — FloodShield Zambia

What was actually re-verified against the real, expanded backend this build (2026-09-07,
"Complete Backend Implementation & End-to-End Integration"), and how. This supersedes
the "Verified" section of `docs/UI-UX.md` for the screens touched here; screens not
listed below are unchanged from that document and were not re-tested this round.

Method: a real Chromium browser (Playwright, headless), driving the real Vite dev
server against the real FastAPI backend and real PostgreSQL database — no mocked
network layer. Script: `e2e_check.py` (run from the session scratchpad, not committed
to the repo — it's a QA script, not application code). `document.documentElement.
scrollWidth - clientWidth === 0` checked at 1440px and 390px for every screen below.

| Screen | What was verified |
|---|---|
| `/login` | Real form submits to `POST /auth/login`; correct credentials (seeded dev admin) redirect to `/dashboard`; the sidebar then shows the real authenticated user's name and role, not a hardcoded "Admin User". |
| `/signup` *(new this build)* | Real form submits to `POST /auth/register`; a fresh account is created (always role CITIZEN) and the user is immediately authenticated. |
| `/alerts/create` | RBAC is enforced in the UI, matching the backend: an authenticated ADMIN successfully creates a real alert, visible on `/alerts` immediately after. An anonymous visitor sees an honest "requires an ADMIN, ANALYST, or OPERATOR account" message instead of the form — verified this is not just hidden but actually blocked (the backend would reject it with 401/403 regardless of UI state). |
| `/alerts` | Confirmed the newly created alert appears in the real list (no page reload needed beyond the post-create navigation). |
| `/reports` (Citizen Reports) *(rebuilt this build — was a static stub)* | A signed-up citizen submits a real report via `POST /citizen-reports`; it appears in the list immediately with status "pending". Sign-in gate verified: an anonymous visitor sees a "Sign in to submit a ground report" prompt instead of the form. |
| `/profile` *(rebuilt this build — was a static stub)* | Shows the real authenticated user's email, role, and account-creation timestamp from `GET /auth/me`; shows a "not signed in" state honestly when anonymous. |
| `/data-sources` *(rebuilt this build — was hardcoded static content)* | Now fetches `GET /data-sources` and renders the real catalog with real, currently-failing connectivity statuses (NASA POWER and DMMU/WARMA genuinely unreachable from this sandbox — see `docs/DATA-SOURCES.md`) rather than hand-written status text that could silently drift from reality. |
| `/ai-model` *(rebuilt this build — now fetches `GET /models`)* | Confirmed it renders the same honest empty state as before, but now sourced from a real (empty) API response instead of hardcoded JSX — verified by checking the network call actually fires and returns `[]`. |
| Sidebar (all authenticated routes) | Shows the real signed-in user's name/role and a working "Sign out" that clears the session and redirects to `/login`; shows a "Sign in" link when anonymous. |

## Also re-run (regression check, no screen changes)

Full backend pytest suite (42 tests: unit/api/integration/database) passes. Frontend
`tsc -b --noEmit` is clean. The pre-existing Dashboard, Risk Map, Location Detail,
Predictions, Analytics, Historical Events, and System Status screens were spot-checked
to confirm they still load correctly against the now-larger backend (new routers
registered, CORS/error-handling middleware added) — no regressions found.

## Known gap in this verification pass

No automated Playwright test file was committed to the repository (`e2e_check.py`
lives in the session scratchpad, not `frontend/tests/` or `backend/tests/`) — it was a
manual QA run, not a suite that runs in CI. Committing a maintained Playwright suite
under `frontend/tests/e2e/` is recorded as follow-up work, not done this round.
