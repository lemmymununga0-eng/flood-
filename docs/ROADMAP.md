# Roadmap — FloodShield Zambia

Phases as defined by the governing prompt (`prompts/MASTER-PROMPT-01-...md`, section 48).
Each phase is only marked complete once implemented **and** tested (Definition of Done,
section 41) — not merely scaffolded.

| Phase | Name | Status |
|---|---|---|
| 0 | Discovery | **Complete** — repository was empty; scaffold + documentation foundation created 2026-09-07. |
| 1 | Research & Data | **In progress** (started 2026-09-07). NASA POWER endpoint/params confirmed from docs (live request confirmed blocked in this environment — needs an environment that can reach the API directly, e.g. Phase 2 development). A first hand-compiled, sourced flood-event log (11 events, 2020–2026) now exists at `ai-engine/data/external/zambia_flood_events_log.csv`. Kanyama and Ng'ombe upgraded to independently-verified candidate locations. Flood-label decision (event-log-based vs. proxy) and final geographic scope still open. |
| 2 | Data Ingestion | Not started |
| 3 | Preprocessing | Not started |
| 4 | Feature Engineering | Not started |
| 5 | Baseline Models | Not started |
| 6 | Time-Series Model (LSTM) | Not started |
| 7 | Model Evaluation | Not started |
| 8 | Explainable AI | Not started |
| 9 | Model Packaging | Not started |
| 10 | Backend | **Substantially expanded** (2026-09-07 "Complete Backend Implementation" build): real JWT auth, RBAC, Alembic migrations, citizen reports, model registry, data-source catalog, audit log, standardized error format, pagination, rate limiting. Still not 100% against §41 — see `docs/backend-architecture.md`, "Not yet built" (no SHAP, no alert delivery, no admin role-management UI). |
| 11 | Database | **Expanded to 11 tables**, real Alembic migrations (no more `create_all()`). See `docs/database-schema.md`. |
| 12 | Frontend | **Expanded**: real login/signup, RBAC-aware UI, citizen reports and AI-model/data-sources screens now backend-driven instead of stubs/static content. See `docs/verified-screens.md`. |
| 13 | Alerts | Core create/list done (Phase 12 note below); delivery to an external channel (SMS/email) still not started — no provider configured. |
| 14 | Testing | Ongoing per-phase from Phase 1 onward. The 2026-09-07 backend build added a real automated suite: 42 pytest tests (unit/api/integration/database) against a real Postgres test database — see `docs/backend-architecture.md`, "Testing". Frontend still has no automated test suite (manual Playwright QA only, not committed to the repo). |
| 15 | Deployment | Not started |

## Note: backend implementation & end-to-end integration build (2026-09-07, third request)

A 79-section master prompt asked for a full production-grade backend. Delivered this
round: real JWT auth + bcrypt password hashing + 5-role RBAC enforced via FastAPI
dependencies; Alembic migrations replacing `Base.metadata.create_all()`; an expanded
schema (`users`, `roles`, `citizen_reports`, `data_sources`, `audit_logs`, plus
`is_active`/`registered_at` added to `model_versions`); new endpoints for citizen
reports (submit/list/moderate), the model registry, and the data-source catalog (with
real live connectivity checks — see `docs/DATA-SOURCES.md`); a consistent
`{"error", "message"}` error shape across every endpoint; pagination/filtering on list
endpoints; rate limiting on `/auth/*`; CORS confirmed already non-wildcard; a real
pytest suite (42 tests, 4 categories, run against a separate real Postgres test
database); and frontend integration — real Login/Signup, RBAC-aware Create Alert,
Citizen Reports rebuilt from a stub into a real form, AI Model and Data Sources
rebuilt from static/stub content into real API-backed screens — all re-verified with
Playwright against the real running stack (see `docs/verified-screens.md`). Required
docs produced: `docs/backend/frontend-integration-matrix.md` (the Phase 0 audit,
written before any code changed), `docs/api-inventory.md`, `docs/database-schema.md`,
`docs/backend-architecture.md`, `docs/verified-screens.md`. Deliberately not built
this round (recorded, not hidden): SHAP explanations (no trained model), alert
delivery to an external channel, an admin role-management UI, a refresh-token
exchange endpoint, and a committed (CI-running) Playwright suite. See
`docs/PROJECT-MEMORY.md` for the decisions behind the scope cuts.

## Note: full UI redesign built (2026-09-07, same day, second request)

The user then supplied a detailed UI specification (dark design system, 26-screen
list) asking to recreate a reference dashboard mockup as a real, functional app. Built:
the full design-token system, a persistent/collapsible app shell, and ~20 of the 26
named screens — every one that could be backed by real data or an honest empty state.
Added real backend support for it: an `alerts` table with working create/list (verified
end-to-end: a form submission produces a real row that appears immediately), and a
`/system-status` endpoint that computes each component's status at request time (DB
ping, real row counts) rather than hardcoding "Operational." Deferred: Signup, separate
How-It-Works/Methodology pages (folded into About), Prediction/Citizen-Report detail
pages (no data yet to show), Data Quality, a React error boundary, and role-based
permissions. See `docs/UI-UX.md` for the full screen-by-screen account, including one
real responsive bug found (mobile tables had no card fallback rendered) and fixed
during QA.

## Note: Phases 10–12 built early (2026-09-07)

The user explicitly asked to "run the app" and, when asked to clarify given nothing was
buildable yet, chose to have a minimal real backend+frontend stood up immediately rather
than wait for the full phase order. What exists now: a FastAPI backend against a real
local PostgreSQL 16 database, seeded with the real location list and the real 11-row
flood-event log (no synthetic data), a `/weather/{id}/ingest` endpoint that makes a
genuine NASA POWER request and reports honest success/failure, a `/predictions` endpoint
that correctly returns empty (no model exists), and a React+TypeScript dashboard
rendering all of it with real loading/success/empty/error states — screenshotted via
headless Chromium to confirm it actually runs. See `docs/API.md`, `docs/DATABASE.md`,
and `docs/UI-UX.md` for exactly what is and is not implemented. This does **not**
retroactively satisfy the Definition of Done for Phases 10–12 (no auth, no tests, no
alerts, no citizen reports, no trained model to predict from) and does not change the
fact that Phase 1's flood-label decision is still open — Phase 2+ ingestion/modelling
work should still wait on that decision per the note below.

## Progress log (Phase 1)

**2026-09-07:**
1. ~~Verify NASA POWER API access~~ — **as far as this environment allows, done.**
   Confirmed endpoint pattern, required/optional parameters, formats, and rate-limit
   behavior against NASA's own docs. Two independent attempts at a live JSON request
   both failed structurally (sandbox egress policy, then robots.txt) rather than
   transiently — this cloud session cannot complete this step. **Still needed:** the
   actual live verification, which now belongs to Phase 2 (first real ingestion run in
   an environment that can reach `power.larc.nasa.gov` directly).
2. ~~Investigate flood-event ground truth~~ — **turned into a real artifact.**
   DMMU (Office of the Vice President) and WARMA are Zambia's confirmed authoritative
   bodies (DMMU's own site remains unreachable — retry or contact directly); a
   hand-compiled log of 11 sourced flood events (2020–2026) now exists at
   `ai-engine/data/external/zambia_flood_events_log.csv`, built from FloodList,
   UN-SPIDER, and Charter-activation reporting. **Still needed:** decide whether this
   becomes the primary label (with a constructed negative class) or a validation check
   against a rainfall-accumulation proxy instead — see `docs/ML-METHODOLOGY.md`.
3. ~~Narrow geographic scope~~ — **partially done.** Kanyama compound and Ng'ombe
   settlement (both Lusaka) are now independently verified via peer-reviewed/graduate
   research as flood-affected, not just named by the prompt. **Still needed:** commit to
   the final 1–3 MVP locations and confirm NASA POWER's grid resolution can usefully
   distinguish them.

## Remaining steps (Phase 1)

4. Write `docs/DATA-DICTIONARY.md` once a source and variable set are confirmed.
5. Decide the flood-label methodology and record the decision (not just the candidates)
   in `docs/PROJECT-MEMORY.md`.
6. Commit to final geographic scope.

Do not begin Phase 2 (ingestion code) until item 5 has a documented working answer —
building ingestion around the wrong target variable would waste the phase.
