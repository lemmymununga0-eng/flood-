# System-Wide Fix Pass — 2026-10-01

## 0. Provenance note — please read first

This file was **created** by this pass, not appended to. A document of the same name was
handed to me describing seven fixes as already applied and verified. I checked every claim
against the repository before acting on it, and **none of the described work was present**:

| Claimed by the handed-in document | Actual state when checked |
|---|---|
| `docs/SYSTEM-FIX-PASS-2026-10-01.md` | did not exist |
| `docs/FRONTEND-AUDIT-2026-10-01.md` | did not exist |
| `docs/GAP-ANALYSIS-AND-DEPLOYMENT-PLAN-2026-10-01.md` | did not exist |
| #1 hamburger fixed via `.btn.menu-toggle` | fixed, but via `.topbar .menu-toggle` — a different fix, applied earlier the same day |
| #2 handler on `starlette.exceptions.HTTPException` | not done |
| #3 rate limit on `/weather/{id}/ingest` | not done |
| #4 citizen-report HTML sanitization | not done |
| #5 `jsonable_encoder` on validation errors | not done |
| #6 `ErrorBoundary.tsx` + test | neither file existed |
| #7 weather history on Location Detail | not done |
| "backend 57/57 passing" via a throwaway local Postgres | no Postgres and no Docker on this machine; the suite cannot run here |

No branch, worktree or stash contained the work either. Its instruction to treat §1 and §2
as ground truth and not re-investigate them was therefore not followed — doing so would have
silently skipped six real, unfixed bugs. The bugs it described were nonetheless accurate and
worth fixing, which is what this pass actually did.

## 1. Fixed this pass, each reproduced before and re-verified after

| # | Issue | Where | Root cause | Fix | Verified |
|---|---|---|---|---|---|
| 1 | Hamburger visible at every width, inert above 900px | `frontend/src/styles/components.css` | `.menu-toggle{display:none}` (line 136) and `.btn{display:inline-flex}` (line 372) have equal specificity; the button carries both classes, so the later rule won | Both rules retargeted to `.topbar .menu-toggle` | Live Chromium: hidden at 1440/1000px; visible **and sliding the sidebar** at 900/768/420px (bounding-box delta, not `isVisible` — a translated element is still "visible") |
| 2 | Router-level 404/405 returned `{"detail":...}` while every other error returned `{"error","message"}` | `backend/app/main.py` | Handler registered on `fastapi.HTTPException`; Starlette's router raises the **base** `starlette.exceptions.HTTPException`, which never matched | Registered on `StarletteHTTPException` (FastAPI's is a subclass, so both now match) | Before: `GET /no-such-endpoint` → `{"detail":"Not Found"}`. After: → `{"error":"http_error","message":"Not Found"}`; `DELETE /locations` → same shape with 405 |
| 3 | `POST /weather/{id}/ingest` unrated — each call makes a real outbound NASA POWER request | `backend/app/api/weather.py` | No `@limiter.limit` decorator; unauthenticated by design | Added `@limiter.limit("10/minute")` matching the `/auth/*` pattern | Before: 12 rapid calls → all `200`. After: → `[200 ×10, 429, 429]` |
| 4 | Citizen-report `description` stored raw HTML including `<script>` | `backend/app/schemas/citizen_report.py` | No server-side sanitization; inert only because React escapes on render | `field_validator` strips tags and unescapes entities; rejects input that is <5 chars of real text once markup is removed | Before: stored `'<script>alert(1)</script> flooding'` verbatim. After, end-to-end through the live API: stored and returned as `'alert(1) Severe flooding on Kafue Road'` |
| 5 | A raising custom validator would 500 instead of 422 | `backend/app/main.py` | `RequestValidationError.errors()` puts the raised exception object in `ctx`, which `json.dumps` cannot serialize. Nothing triggered it until #4 added the codebase's first custom validator | Wrapped `exc.errors()` in `jsonable_encoder(...)` | All-markup payload (strips to empty) → clean `422` with a proper per-field message, not a `500` |
| 6 | No React error boundary — any render throw left `#root` empty (blank white page) | `frontend/src/components/ErrorBoundary.tsx`, `main.tsx` | Never built | Added a class boundary wrapping `<App />`, with the error message, a Try-again reset and a Back-to-dashboard escape | **Unit-verified only** — 5 tests, including a guard-on-guard case asserting the container *is* empty without the boundary. See §3 for why the live check is still outstanding |
| 7 | `GET /weather/{location_id}` was a working endpoint with no caller | `frontend/src/pages/LocationDetail.tsx`, `services/weather.ts`, `types/index.ts` | Never built — the page could trigger ingestion but never displayed the result | Added `fetchLocationObservations`, a `WeatherObservation` type matching the backend schema, and a "Stored weather history" table; ingest now refreshes it | Live browser on `/locations/1`: panel renders **253 real observation rows**, endpoint called, columns include the feature-contract fields (e.g. `2026-09-17  0  25.15  33.22  18.02  26.95  3.44`) |

### Regression state after all seven

- **Frontend: 11/11 passing** (6 existing + 5 new error-boundary tests)
- **ML pipeline: 37/37 passing**
- **Frontend production build: clean** (427 KB JS / 28.7 KB CSS)
- **TypeScript: clean** (`tsc -b --noEmit`, exit 0)
- **Backend: NOT RUN — see §3**

## 2. Verified already correct, no change made

Re-checked against current code this pass, not inherited from an older report:

- Insecure config defaults — the settings validator does fail fast outside `development`.
- Frontend API base is overridable via `VITE_API_BASE_URL` (but see §3 for a live hazard).
- Frontend tests exist and pass.

## 3. Honest gaps in this pass

| Gap | Detail |
|---|---|
| **Backend test suite was not executed** | `conftest.py` requires a local Postgres `floodshield_zambia_test`. This machine has no Postgres binaries, no service, and no Docker. **No backend pass count is claimed.** The seven fixes were instead verified by targeted live requests against the running app, listed per-row above. |
| **Fix #6 was not verified live** | The 5 unit tests prove the boundary catches a render throw and renders the fallback. Two attempts to force a genuine render error in the browser (poisoning `Array.prototype.map`, then `Number.prototype.toFixed`) failed to throw at the right point in React's render phase — the page rendered normally in the first case and stalled at a loading state in the second. Neither is evidence the boundary fails; it is simply not yet confirmed end-to-end in a browser. |
| **A test row was written to the live database** | Verifying #4 end-to-end created `citizen_reports` id 1 with description `alert(1) Severe flooding on Kafue Road`. It is real evidence the sanitizer works, but it is audit data, not user data — delete it if you do not want it in the demo. |
| **`VITE_API_BASE_URL` default is a live hazard on this machine** | `services/http.ts` falls back to `http://localhost:8000/api/v1`. Port 8000 is currently serving an unrelated project of yours ("Weapons of Power Ministry International — API"). Running `npm run dev` without the env var points the frontend at the wrong backend and every call 404s. Fix with `frontend/.env.local` containing `VITE_API_BASE_URL=http://127.0.0.1:8001/api/v1`, or stop that service. Not applied here because the port choice is yours. |

## 4. Not attempted — the §3 items from the handed-in document

ESLint/ruff configuration, the root `requirements.txt` split, and the dead scaffold
directories were listed as priorities 1–3 in that document's master prompt. They were not
started: the six unfixed bugs took precedence, and all three are cleanup tasks that deserve
their own verified pass rather than being rushed in alongside behavioural fixes.

Items genuinely requiring a human decision — hosting platform, SMS provider, how the ML
result is framed for the demo, and whether to commit/push — remain untouched.

## 5. Out of scope

Nothing in this pass touches the ML model, the `NO_MODEL_SELECTED` finding, or data
labelling. That is a research and data-quality problem, not a code defect, and a fix pass
cannot close it.
