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

---

## Update — 2026-09-08 re-audit

No frontend source changed since this table was produced (confirmed via byte-identical build
output), so every screen above is unchanged by non-regression. **No browser-automation tool was
available in this session's audit pass**, so none of the live-navigation rows above were
re-executed — they remain "last verified 2026-09-07," not re-confirmed today. Static-code
inspection this session (route list, component reads, CSS breakpoints) found no evidence
contradicting any row above, plus two new items not previously in this ledger:

- `Settings.tsx` carries the same class of stale-content bug as `About.tsx` (see
  `docs/bug-register.md` BUG-10) — not a regression, just not previously caught.
- Screen count corrected to 21/26 registered routes (was reported as "22" previously) —
  see `docs/project-requirements-matrix.md`'s 2026-09-08 update for the corrected list.

---

## Update — Phase 1 architecture-alignment refactor (2026-09-08)

Re-screenshotted Dashboard, Login, and Create Alert (via puppeteer-core driving the local Chrome
install, against the same live local backend/Postgres/frontend stack already running this
session) immediately after the backend `repositories/`+`integrations/` split and the frontend
`constants.ts`/layouts/`services/` split described in `docs/ARCHITECTURE.md`'s 2026-09-08 note.
**Result: no visual regression** — all three screenshots are pixel-identical to the ones taken
earlier in this same session, before the refactor. This is a live re-verification, not a
code-read assumption.

---

## Update — Phase 2: Notifications screen goes live (2026-09-08)

`/notifications` (`frontend/src/pages/Notifications.tsx`) was previously an honest static stub
(no fetch, hardcoded `EmptyState`). Re-verified live this session as a real, backend-driven
screen: a citizen account submitted a citizen report, an admin moderated it via the real
`/reports` moderation flow, and — without any manual data seeding — the citizen's `/notifications`
page rendered the real resulting notification card ("Your report was verified", the real review
note text, an "Unread" badge, a real timestamp, and a working "Mark read" button), confirmed via
a live puppeteer-core + local-Chrome screenshot (`.run_shots/notifications_populated.png`). This
is the first screen in this project to go from "honest stub" to "real data" purely through backend
work in this session, without any frontend-only mocking.

---

## Update — UI foundation pass (2026-09-08)

Landing, Login, Signup, About, Dashboard, and Risk Map were restyled to the new "Premium
Professional Dark Mode" token system (see `docs/UI-UX.md`'s 2026-09-08 update for full detail).
**Re-verified live** via puppeteer-core + local Chrome at three widths — 1440px (desktop), 800px
(tablet), 390px (mobile) — screenshots saved under `.run_shots/redesign/`:

| Screen | 1440px | 800px | 390px | Notes |
|---|---|---|---|---|
| Landing | done | done | done | New hero SVG visual, icon-chip feature row |
| Login | done | done | done | New split-panel layout; panel collapses to single column at or below 900px per CSS |
| Signup | build-checked | - | - | Same pattern as Login, not separately re-screenshotted |
| Dashboard | done | done | done | New icon KPI cards, new real "Recent warnings" card, sidebar icons + avatar all render correctly |
| Risk Map | done | - | done | New two-column legend/map layout; map column stacks below legend at or below 900px, real marker click opens the new side panel |
| About | build-checked | - | - | Icon chips + real methodology pipeline diagram, not separately re-screenshotted at other widths |

This widens this repo's breakpoint coverage beyond the previously-recorded 2/8 (1440px/390px) —
now includes a tablet-width (~800px) check for the two most layout-complex screens (Dashboard,
Login). Full 8-breakpoint coverage remains an open item, tracked as before.
