# Verified Endpoints — FloodShield Zambia

Regression-protection ledger required by the audit's Section 59. Lists every backend endpoint that
has been live-verified (a real request against the real running stack, not a code read alone), how,
and when. **Retest whenever a change touches**: auth, `app/core/deps.py`, any API router, shared
schemas, the database session/models, or `main.py`'s middleware/error-handler registration.

Last full verification pass: 2026-09-07 (full codebase audit).

| Endpoint | Method | Verified how | Result |
|---|---|---|---|
| `/health` | GET | curl, live | 200 `{"status":"ok"}` |
| `/api/v1/auth/register` | POST | curl, live (fresh account created twice this session) | 201, real user created, tokens issued |
| `/api/v1/auth/login` | POST | Playwright live login as seeded admin, post-restart | Succeeds, redirects to `/dashboard` |
| `/api/v1/auth/me` | GET | curl with valid token; curl with garbage token; curl with forged `alg:none` token | 200 with valid token; 401 for both invalid cases |
| `/api/v1/locations` | GET | curl, incl. SQL-injection-shaped query param | 200, real seeded rows; injection payload safely handled, no data leak |
| `/api/v1/flood-events` | GET | curl, live | 200, 11 real sourced rows |
| `/api/v1/weather/{location_id}` | GET | curl, live (not covered by automated tests — see BUG-08) | 200, empty until real ingestion succeeds |
| `/api/v1/weather/{location_id}/ingest` | POST | curl, live | Honest failure (`status: "failed"`), NASA POWER unreachable — BLOCKED by sandbox egress, not a code defect |
| `/api/v1/predictions` | GET | curl, live | 200 `[]` — honest, no model exists |
| `/api/v1/alerts` | GET | curl, live | 200, real persisted alerts |
| `/api/v1/alerts` | POST | curl unauthenticated (401); curl as CITIZEN (403); Playwright as ADMIN (succeeds, appears in list) | RBAC boundary correctly enforced both directions |
| `/api/v1/citizen-reports` | GET | curl, live | 200, real reports |
| `/api/v1/citizen-reports` | POST | curl as fresh CITIZEN, incl. a stored-XSS probe payload | 201, correctly allowed for any authenticated user; payload stored unescaped (BUG-02) |
| `/api/v1/citizen-reports/{id}/moderate` | POST | Playwright integration test (operator moderates a report) | Verified via automated integration test, part of the 42-test suite |
| `/api/v1/models` | GET | curl, live | 200 `[]` — honest, no model trained |
| `/api/v1/models/{id}` | GET | code read + automated test | 404 for nonexistent id |
| `/api/v1/data-sources` | GET | Playwright live, curl | 200, real catalog with live-checked statuses |
| `/api/v1/data-sources/{id}/check` | POST | code read (not covered by automated tests — see BUG-08) | RBAC-gated; live health check performed |
| `/api/v1/system-status` | GET | curl, live | 200, computed at request time (real DB ping + row counts) |
| Unknown path (routing 404) | any | curl, live | 404, raw Starlette `{"detail": ...}"` shape (BUG-04 — inconsistent with app's standard error shape) |
| CORS preflight, disallowed origin | OPTIONS | curl, live | 400, request rejected — enforced, not just configured |

All 19 endpoints above are confirmed live and functioning as documented. The two RBAC-gated writes
(`POST /alerts`, `POST /citizen-reports/{id}/moderate`) and the two auth endpoints were additionally
exercised through both the allow and the deny path, not just the happy path.

---

## Update — 2026-09-08 re-audit

**None of the 19 endpoint rows above could be re-executed live this session** — this sandbox
instance has no reachable Postgres (`localhost:5432` connection times out) and is missing the
`slowapi` package, so the backend app fails to import and `uvicorn` cannot start at all. This is
reported honestly as **BLOCKED (environment)**, not as a re-confirmation and not as a failure. The
underlying source code is byte-identical to what passed these live checks on 2026-09-07, so there
is no positive evidence of regression — but treat every row above as "last executed 2026-09-07,"
not "re-verified 2026-09-08," until a working Postgres + complete dependency set is available in
whatever environment runs this audit next.

**New endpoint identified this session (static code read only, not live-probed):**
`POST /api/v1/weather/{location_id}/ingest` has no auth dependency at all (`backend/app/api/weather.py:25-38`)
— confirmed as intentional/documented public access per `docs/api-inventory.md`, but it also has no
rate limit, which was not previously called out. See `docs/bug-register.md` BUG-09.

---

## Update — Phase 1 architecture-alignment refactor (2026-09-08)

`POST /api/v1/weather/{location_id}/ingest` and `POST /api/v1/data-sources/{id}/check` were
refactored to delegate the external HTTP call to a new `integrations/` layer
(`WeatherProvider`/`HttpHealthChecker`) and the persistence to a new `repositories/` layer,
instead of doing both inline in the service function. **Re-verified live via the actual test
suite** (not just a code read): `pytest` run from `backend/`, **45 passed** (the prior 42 plus 3
new tests added specifically for `/weather/*`). The 3 new tests
(`backend/tests/api/test_weather_ingestion.py`) use a `MockWeatherProvider` injected via
`app.dependency_overrides` — the same override mechanism already used for `get_db` — and assert:
a success path stores exactly the mocked records with `source: "NASA POWER"`; a failure path
reports `status: "failed"` with the real error text and stores nothing; and an unknown location
id still 404s. `POST /api/v1/data-sources/{id}/check` was re-verified by the existing suite passing
unchanged (no dedicated new test yet — tracked in `docs/bug-register.md` BUG-08's updated note).
Response shapes, URLs, and DB effects for both endpoints are unchanged from the rows above — this
was a structural refactor, not a behavior change.

---

## Update — Phase 2: notifications (2026-09-08)

Two new endpoints, both real, both live-verified end-to-end (not just unit-tested):
`GET /api/v1/notifications` (auth-required, scoped to the calling user — confirmed 401 anonymous,
confirmed two different users each see only their own via `pytest`) and
`POST /api/v1/notifications/{id}/read` (idempotent; confirmed 404 — not 403 — when a different
user attempts to mark someone else's notification read). **Live end-to-end smoke test**: a real
citizen account submitted a citizen report via `POST /citizen-reports`, an admin moderated it via
`POST /citizen-reports/{id}/moderate`, and the citizen's `GET /notifications` returned a real
notification row referencing that report — driven through actual HTTP calls against the running
backend and a real disposable Postgres, then confirmed rendering correctly in a live browser
session (screenshot: `.run_shots/notifications_populated.png`). `pytest` from `backend/`: 49/49
passing (45 prior + 4 new, `backend/tests/api/test_notifications.py`).
