# Project Requirements Matrix — FloodShield Zambia

Evidence-based mapping of requirement → screen → API → service → DB → ML → tests → status, produced
2026-09-07 as part of the full codebase audit (`docs/AUDIT-REPORT-2026-09-07.md`). Status taxonomy:
**COMPLETE** (implemented and verified working), **PARTIAL** (implemented but with real gaps),
**IMPLEMENTED BUT UNVERIFIED** (code exists, correct-looking, never observed succeeding live),
**MOCKED/HARDCODED** (fake/static data presented as real), **MISSING**, **BLOCKED** (environment
constraint, not a code defect), **N/A**. No row below is marked COMPLETE on the basis of a file
existing — each was checked against a live request, a passing test, or direct code read.

## Frontend screens

| Screen | Route | Backend-driven? | Auth/RBAC handled? | Loading/empty/error states | Status |
|---|---|---|---|---|---|
| Landing | `/` | N/A (static) | N/A | N/A | COMPLETE |
| Login | `/login` | Yes — real `POST /auth/login` | N/A | Yes, verified live | COMPLETE |
| Signup | `/signup` | Yes — real `POST /auth/register` | N/A | Yes | COMPLETE |
| About | `/about` | N/A (static) | N/A | N/A | PARTIAL — contains stale/false content (BUG-01) |
| Dashboard | `/dashboard` | Yes | Auth-gated route | Yes | COMPLETE |
| Risk Map | `/risk-map` | Yes (locations) | Auth-gated route | Yes; OSM tiles never load (BLOCKED — sandbox egress) | PARTIAL |
| Location Detail | `/location/:id` | Yes | Auth-gated route | Yes | COMPLETE |
| Predictions | `/predictions` | Yes — honestly empty (`[]`, no model) | Auth-gated route | Yes, honest empty state | COMPLETE (as an empty-state screen; the underlying feature is MISSING — see ML/AI section) |
| Analytics | `/analytics` | No real aggregate data source | Auth-gated route | Honest stub, not fabricated | PARTIAL (honest stub) |
| Historical Events | `/historical-events` | Yes — 11 real sourced rows | Auth-gated route | Yes | COMPLETE |
| Historical Event Detail | `/historical-events/:id` | Yes | Auth-gated route | Yes | COMPLETE |
| Alerts | `/alerts` | Yes | Auth-gated route | Yes | COMPLETE |
| Create Alert | `/alerts/create` | Yes — RBAC (ADMIN/ANALYST/OPERATOR) | Verified live: denies anonymous, allows correct role | Yes | COMPLETE |
| Citizen Reports | `/reports` | Yes — real submit/list/moderate | Sign-in gated for submit; RBAC for moderate | Yes | COMPLETE |
| AI Model | `/ai-model` | Yes — real (empty) `/models` registry | Auth-gated route | Yes, honest empty state | COMPLETE (as an empty-state screen; underlying registry is MISSING — see ML/AI) |
| Data Sources | `/data-sources` | Yes — real catalog + live health checks | Auth-gated route | Yes | COMPLETE |
| System Status | `/system-status` | Yes — computed at request time | Auth-gated route | Yes | COMPLETE |
| Notifications | `/notifications` | No event source generates any | Auth-gated route | Honest stub | PARTIAL (honest stub) |
| Settings | `/settings` | Partial | Auth-gated route | Yes | PARTIAL |
| Profile | `/profile` | Yes — real `GET /auth/me` | Auth-gated route | Yes | COMPLETE |
| 404 / not-found | any unknown route | N/A | N/A | Verified live, renders correctly | COMPLETE |
| React error boundary | N/A | N/A | N/A | N/A | MISSING |
| How-It-Works / Methodology (standalone) | — | — | — | — | MISSING (folded into About) |
| Prediction Detail (single item) | — | — | — | — | MISSING |
| Citizen Report Detail (single item) | — | — | — | — | MISSING |
| Data Quality | — | — | — | — | MISSING |
| Dark/light theme toggle | — | — | — | — | MISSING (dark-only by design) |

## API endpoints (19 live)

See `docs/verified-endpoints.md` for the full method/path/auth/status table with live-probe evidence.

## Database (11 tables)

See `docs/database-schema.md` for full columns; every table's schema is COMPLETE and Alembic-migrated.
Population status: `roles`, `users`, `locations`, `flood_events`, `data_sources` — COMPLETE (real seed
data). `alerts`, `citizen_reports`, `audit_logs` — COMPLETE (real, live-created rows). `weather_observations`
— PARTIAL (schema complete, populated only by a never-yet-successful NASA POWER call — BLOCKED).
`model_versions`, `predictions` — MISSING population (schema-only, 0 rows; no model exists to populate them).

## ML/AI pipeline (per `docs/ML-METHODOLOGY.md`'s 9 stages)

| Stage | Status | Evidence |
|---|---|---|
| Data collection | PARTIAL | 11 real sourced flood events exist; no negative-class construction |
| Data cleaning | MISSING | No code exists |
| Feature engineering | MISSING | No code exists |
| Model training (XGBoost) | MISSING | `xgboost` not installed, not imported anywhere |
| Model training (LSTM) | MISSING | `tensorflow` not installed, not imported anywhere |
| Model evaluation | MISSING | No metrics exist anywhere in the repo or DB |
| Explainability (SHAP) | MISSING | `shap` not installed; zero SHAP code found; one honest doc comment acknowledges the gap |
| Model packaging/registry | MISSING | `model_versions` table is real but has 0 rows; no artifact exists |
| Inference (serving) | COMPLETE (as an honest no-op) | `/predictions` correctly returns `[]` rather than fabricating output |

## Testing

42/42 backend pytest tests passing (verified live, `docs/AUDIT-REPORT-2026-09-07.md` Section 13).
Zero automated frontend tests exist. Endpoint coverage gaps: `/weather/*`, `/data-sources/{id}/check`.

## Overall

No item in this matrix is marked COMPLETE solely because a file with a matching name exists — every
COMPLETE mark corresponds to a live-verified request/response, a passing automated test, or direct,
line-level code confirmation performed during this audit.

---

## Update — 2026-09-08 re-audit

Full evidence in `docs/AUDIT-REPORT-2026-09-08.md`. Two corrections and one full replacement:

**Correction 1 — screen count.** Recounted directly from `frontend/src/App.tsx:31-56`: **21 routes
exist, not 22.** The frontend screens table above is otherwise still accurate (routes, backend
wiring, auth/RBAC framing) except: "Auth-gated route" should be read as "public route with
page-content gating in 2 cases (`CreateAlert`, `Profile`)" for the other 14 — no router-level
route guard exists (`AppShell.tsx` renders its `Outlet` unconditionally). This is consistent with
the backend's own design (the underlying `GET` endpoints are public), not a new vulnerability, but
it means the table above overstates enforcement at the frontend layer specifically.

**Correction 2 — Settings row.** Add: `Settings.tsx` contains a stale-content bug (`docs/bug-register.md`
BUG-10), the same class of issue as the already-known About.tsx PARTIAL rating.

**Full replacement — ML/AI pipeline table.** The 9-stage table below replaces the one above; the
old one described empty scaffolding that no longer exists.

| Stage | Status | Evidence |
|---|---|---|
| Data collection | PARTIAL | 11 real sourced flood events exist but are **not loaded** by the pipeline (filename mismatch, `docs/bug-register.md` BUG-12); the one run that happened used 100% synthetic weather instead |
| Data cleaning | COMPLETE (as code, executed) | `ai-engine/src/preprocessing/` — real, ran successfully on the synthetic dataset |
| Feature engineering | COMPLETE (as code, executed), with a critical caveat | `ai-engine/src/features/build_features.py` — real rolling/lag/cyclical features; but the proxy-label function derives labels from these same feature columns (leakage, BUG-13) |
| Model training (XGBoost) | BLOCKED | Real code exists, gated behind an availability flag; `xgboost` not installed; never trained |
| Model training (LSTM) | BLOCKED | Real Keras architecture exists; `tensorflow` cannot install on the current Python 3.14 interpreter (requires 3.11); never trained |
| Model training (baselines: LogReg/DecisionTree/RandomForest/GradientBoosting) | COMPLETE (as code, executed) — **IMPLEMENTED BUT SCIENTIFICALLY INVALID as evaluated** | 4 real `.joblib` artifacts exist in `ai-engine/saved_models/`; trained on synthetic data + leaky proxy labels — see caveat above |
| Model evaluation | COMPLETE (as code, executed) — same leakage caveat applies to the numbers produced | `ai-engine/src/evaluation/metrics.py`, `ai-engine/reports/baseline_comparison.csv` |
| Explainability (SHAP) | BLOCKED | Real, complete implementation exists (`ai-engine/src/explainability/explain_models.py`); `shap` not installed; never executed |
| Model packaging/registry | PARTIAL | 4 real files exist on disk (`saved_models/`); `model_versions` DB table still schema-only, 0 rows — trained models were never registered into the running application |
| Inference (serving) | COMPLETE (as an honest no-op) | Unchanged — `/predictions` correctly returns `[]` since no model has been registered for serving |

**Testing update:** the backend's 42/42 test claim could not be re-executed this session
(environment gap — no Postgres, `slowapi` missing; not a code regression). **New:** 26/26
`ai-engine` unit tests confirmed passing live this session.

---

## Update — Phase 2: Database + backend (2026-09-08)

**Notifications screen** (`frontend/src/pages/Notifications.tsx`, row 32 above): status
corrected from PARTIAL (honest stub) to **COMPLETE for its actual, narrower scope** — it now
fetches real, backend-persisted notifications via `GET /api/v1/notifications` (auth-required,
scoped to the calling user) and supports marking one read via `POST /notifications/{id}/read`.
Verified live end-to-end this session: a citizen submitted a real report, an admin moderated it,
and the citizen's `/notifications` page showed the real resulting notification with a working
"Mark read" action — not a code-read assumption. **Scope caveat, not a partial-completion bug:**
only citizen-report moderation generates notifications; alert issuance, new predictions, and
data-source sync still don't, because none of those events has a real per-user recipient to
target (see `docs/ARCHITECTURE.md`'s 2026-09-08 scope note and `docs/missing-features.md`).

**Database**: `notifications` added as a 12th table (`backend/alembic/versions/927a162df6ca_add_notifications_table.py`), re-verified via a real `alembic upgrade head` run against the local dev
database, not just a code read.

**Testing**: 49/49 backend tests passing (the 45 from the Phase 1 pass, plus 4 new tests covering
notification creation-on-moderation, user-scoping, and mark-read ownership), re-executed live this
session.

---

## Update — Real training run on real data (2026-09-09)

**ML/AI pipeline table, corrected again — this is the biggest jump yet.** Following research that
added 3 pre-2020 flood events (now 14 total, giving the training split real positive examples for
the first time — see `docs/bug-register.md` BUG-16), NASA POWER was tested from the real developer
machine and found reachable (previous "blocked" findings were specific to sandboxed cloud
sessions, not this project's code — see `docs/DATA-SOURCES.md`'s 2026-09-09 update). `main.py` was
then run for real, producing:

| Stage | Status | Evidence |
|---|---|---|
| Data collection | **COMPLETE (real, executed)** | Real NASA POWER data for Lusaka, 2000-2023 (8,766 rows), verified via a live API call, saved to `ai-engine/data/raw/nasa_power_zambia.csv` |
| Data cleaning | COMPLETE (unchanged) | Ran successfully against the real data |
| Feature engineering | COMPLETE (unchanged) | Ran successfully against the real data; no leakage this run since real (not proxy) labels were used |
| Model training (baselines) | **COMPLETE, real result** | 4 models trained on real weather + real labels; results in `docs/ML-METHODOLOGY.md`'s 2026-09-09 update — modest but genuine (Logistic Regression ROC-AUC 0.850, recall 0.489) |
| Model training (XGBoost/LSTM) | BLOCKED (unchanged) | Still requires Python 3.11 |
| Model evaluation | **COMPLETE, real result** | No leakage caveat applies to this run — real, independent labels |
| Explainability (SHAP) | BLOCKED (unchanged) | `shap` still not installed |
| Model packaging/registry | PARTIAL (unchanged) | New real artifacts exist on disk; still not registered into the running backend's `model_versions` table |
| Inference (serving) | COMPLETE (unchanged, as an honest no-op) | `/predictions` still correctly returns `[]` — these new artifacts are not yet wired to the backend |

**New, real limitations from this run** (not fabrication, not leakage — see BUG-17/18/19):
single-point (Lusaka-only) weather vs. multi-province real events; a national-level, not
location-specific, label; and unhandled class imbalance in the tree-ensemble baselines.

---

## Update — Phase 3: Data pipeline (2026-09-08)

**"Data collection" row in the ML/AI pipeline table above, corrected again:** the filename-mismatch
bug (BUG-12) plus two bugs hiding behind it (BUG-14: malformed CSV row silently crashing the
parser; BUG-15: missing `end_date` silently zeroing 9 of 11 events) are now fixed and covered by
4 new passing tests (`ai-engine/tests/test_flood_events_ingestor.py`; ai-engine suite now 30/30).
The real 11-event flood log now loads correctly and produces correct daily labels — **verified
live**: 52 real positive flood-days recognized (up from 43), across the correct dates.

**New status, more precise than "PARTIAL — not loaded":** real-event data loading is now
**COMPLETE (as code, executed)** — but real-event-based *training* remains **BLOCKED (data)**,
not PARTIAL: measured directly, all 52 positive days fall in validation (7) or test (45); **zero**
fall in the training split under this project's own correct chronological split, because all 11
real events postdate 2020. No further code change can fix this — see `docs/bug-register.md`
BUG-16 and `docs/ML-METHODOLOGY.md`'s update for the two legitimate paths forward (more/older
event records, or a non-chronological validation strategy), neither implemented.
