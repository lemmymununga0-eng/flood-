# FloodShield-Zambia — Full System Audit

> **HISTORICAL RECORD — superseded.** This document was accurate when written and has
> deliberately **not** been edited, so the project's audit trail stays honest. It does not
> describe the system as it stands now: a model is trained and served, 82 districts of
> weather data are ingested, and the corrected study's verdict is `DO_NOT_DEPLOY`.
> For the current state see **`docs/CURRENT-STATE-2026-10-01.md`**.

Produced 2026-09-18. Every claim below was verified this session against actual code, an
actual live database (Supabase Postgres, connected for the first time this session), actual
running backend endpoints, and actual test-suite executions — not re-derived from prior
documentation. Where prior docs are cited, it is because a claim was cross-checked against
them and either confirmed or found stale. Nothing here is assumed true because a doc said so.

**Read this first — the single most important clarification in this document:**
The specific metrics you quoted in your audit request (Logistic Regression ROC-AUC≈0.777,
Gradient Boosting recall≈0.667, Experiment D 0.587→0.588) are real and verified — but they
belong to a **separate, non-integrated project** at `C:\Users\Humphrey\OneDrive\Desktop\flooddata\`,
which is **not part of this git repository and has zero connection to FloodShield-Zambia's
backend, frontend, or `ai-engine/` folder.** FloodShield-Zambia's own ML subsystem (`ai-engine/`)
is a separate, smaller, single-location (Lusaka-only) pipeline with its own different real
results (Section 3/4 below). If you want FloodShield-Zambia to demonstrate the flooddata
project's rigor, that work needs to be either migrated into `ai-engine/` or explicitly cited
as an external validation study — right now the two are unrelated codebases that happen to
share a research topic.

---

## 1. Project Discovery

| Area | Location | Real? |
|---|---|---|
| Frontend | `frontend/src/` (React + Vite + TypeScript) | Yes, builds and typechecks clean |
| Backend/API | `backend/app/` (FastAPI) | Yes, 21 real endpoints, all DB-backed |
| ML code | `ai-engine/src/` | Yes, real preprocessing/features/models/eval code |
| Trained models | `ai-engine/saved_models/*.joblib` | Yes, 4 real sklearn models on disk |
| Preprocessing/feature engineering | `ai-engine/src/preprocessing/`, `ai-engine/src/features/` | Yes, real, not stubs |
| Datasets | `ai-engine/data/{raw,external,processed}/` | Yes, real files, real row counts (below) |
| Database code | `backend/app/models/`, `backend/app/repositories/` | Yes, SQLAlchemy ORM |
| Migrations/schema | `backend/alembic/` | Yes, 2 real migrations, applied live this session |
| Authentication | `backend/app/api/auth.py`, `core/security.py` | Yes, real bcrypt + JWT, no mock users |
| Dashboard | `frontend/src/pages/Dashboard.tsx` | Yes, real KPIs (mostly zero data) |
| Maps | `frontend/src/pages/RiskMap.tsx` | Yes, real Leaflet + OSM, not a static image |
| Charts | — | **Does not exist.** No charting library in `package.json` |
| Alerts | `backend/app/api/alerts.py`, `frontend/src/pages/Alerts.tsx` | Yes, real dashboard-only alerts (no SMS/email) |
| Notifications | `backend/app/api/notifications.py` | Yes, real, scoped per-user |
| Configuration | `backend/app/core/config.py`, `.env`/`.env.example` | Yes; P0 fail-fast fix confirmed present |
| Tests | `backend/tests/` (49), `ai-engine/tests/` (31) | Yes, both suites **actually run this session**, both 100% pass |
| Documentation | `docs/*.md` (30+ files) | Extensive; several stale claims found and listed in Section 17 |
| Deployment config | — | **Does not exist.** No Dockerfile, no CI, confirmed absent |
| Scripts | `backend/scripts/seed_db.py`, `ai-engine/main.py`, various `.py` utilities | Yes, real, executed this session |

`backend/app/ml/` exists as a directory but **contains zero files** (confirmed via direct
listing) — a placeholder for ML integration that was never built.

---

## 2. Actual System Architecture

The requested ideal architecture (`USER → FRONTEND → BACKEND/API → DATABASE → ML PIPELINE →
MODEL → PREDICTION → RISK OUTPUT → DASHBOARD/ALERT`) does **not** exist as a connected chain.
The actual, verified architecture is two disconnected halves:

```
USER → FRONTEND → BACKEND/API → DATABASE            [fully real, fully connected]
                                     ↑
                                     |  (no connection exists here)
                                     ↓
ai-engine/ (offline, standalone) → saved_models/*.joblib   [real, but never loaded by backend]
```

- **Frontend ↔ Backend ↔ Database**: real, live, connected. Verified this session end-to-end
  (see Section 16).
- **Backend ↔ ML pipeline**: **does not exist.** `backend/app/ml/` is empty. No endpoint loads
  a `.joblib` file, calls `.predict()`, or references `ai-engine/` in any way. `GET
  /api/v1/predictions` is a real `SELECT` against an empty `predictions` table — honestly
  empty, not connected to the trained models.
- **ML pipeline is a standalone, offline batch process** (`ai-engine/main.py`), run manually,
  producing `.joblib` files and metrics files on disk that nothing in the running application
  ever reads.

Component status:

| Component | Status |
|---|---|
| Frontend | Implemented |
| Backend/API | Implemented |
| Database | Implemented (now live, see Section 9) |
| ML pipeline (standalone) | Implemented |
| Model → prediction serving | **Missing** (no code path exists at all, not even disconnected — never written) |
| Risk output → dashboard/alert | Implemented for the *display* side, fed by permanently-empty data |

---

## 3. Machine Learning Audit (`ai-engine/`)

### Data
- `ai-engine/data/raw/nasa_power_zambia.csv` — **8,766 real daily rows**, one location
  (Lusaka only — `src/config/settings.py` hardcodes `default_latitude/longitude`), 2000-01-01
  to 2023-12-31. Columns: `prectotcorr, t2m, t2m_max, t2m_min, rh2m, ws2m,
  allsky_sfc_sw_dwn, gwetroot, gwetprof`.
- `ai-engine/data/external/zambia_flood_events_log.csv` — **14 real event rows** (counted via
  CSV parsing, not raw `wc -l`), 2007–2025/2026.
- **No ENSO/IOD/climate-index data exists anywhere in `ai-engine/`** (confirmed via exhaustive
  grep — zero matches for Nino/IOD/Dipole/teleconnection). This is a real gap relative to the
  separate flooddata project, which does have this.
- A `synthetic_data_generator.py` exists and is real, but is an **explicit, labeled, opt-in
  fallback** (`--use-synthetic` CLI flag, or automatic fallback only if a live NASA POWER
  fetch fails) — confirmed the actual saved models were **not** built from it:
  `model_metadata.json` records `"data_source": "nasa_power"`.

### Preprocessing / Feature Engineering
Real, not stubs. `DataCleaner.clean()` does physical-bounds clipping + a 3-stage
ffill/bfill/interpolate fill. `FeatureEngineer.build()` adds real rolling-window statistics
(3/7/14/30-day sum/mean/max on rainfall, mean on humidity), lag features (1/2/3/7/14 days on
4 variables), temporal cyclical encodings, a rainy-season flag, and a composite soil-saturation
index. 54 total features (full list in Section 4).

**Split method**: strictly chronological index-slicing, no shuffling — confirmed correct by
reading `src/datasets/split_data.py` directly.

**New leakage finding, not previously documented**: `main.py` fits the `RobustScaler` on the
**full dataset before** the train/val/test split, not on the train split alone — so scale
statistics (median/IQR) leak from validation and test rows into the scaler used to transform
training data. This is real but minor (RobustScaler is insensitive to a small number of
outlier days), and distinct from the already-known BUG-13.

### Target / Label Construction — BUG-13 status, verified
Two label-construction paths exist in the code:
1. **Real event-based labels** (`flood_events_ingestor.py`) — marks days within a real event's
   date range as positive. Does not algorithmically weight by date precision (a
   month-imprecise event range is treated the same as a day-precise one), though the
   imprecision is recorded per-row in `confidence_notes`.
2. **Proxy labels** (`build_features.py::_add_proxy_labels()`) — a rainfall/soil-moisture
   threshold rule. **This is confirmed leaky by construction**: it flags a day positive using
   the exact same rolling-rainfall/soil-index columns that are also saved as model input
   features.

`main.py` always tries the real-label path first and only falls back to the proxy if zero real
labels are found. **Verified directly against the saved artifact** (not assumed): the current
`features.csv` has 295 of 8,752 rows positive (3.37%), which matches the real-label path's
known signature, not the proxy path's — **the currently-saved models were built from real
event labels, not the leaky proxy formula.** BUG-13's leakage is real and still present in the
`_add_proxy_labels()` function's code, but it is not what produced the models sitting in
`saved_models/` today. `docs/bug-register.md` already states this correctly; `docs/
missing-features.md` line 40 states it ambiguously enough that a reader could wrongly conclude
the current models are proxy-based — flagged as a documentation fix in Section 17.

---

## 4. Model Artifact Audit

`ai-engine/saved_models/` contains exactly: `logisticregression_model.joblib`,
`decisiontree_model.joblib`, `randomforest_model.joblib`, `gradientboosting_model.joblib`,
`scaler.joblib`, `feature_columns.json`, `model_metadata.json`. All dated 2026-09-08/09
(the real training run).

- **Designated production model**: none is formally designated — there's no "active model"
  marker or `ACTIVE_MODEL_VERSION` value set (that env var exists in config but is empty), and
  the `model_versions` DB table has 0 rows.
- **Preprocessing saved**: Yes — `scaler.joblib` (RobustScaler), `feature_columns.json` (54
  names, byte-identical to the list embedded in `model_metadata.json`).
- **Calibration saved**: **No.** No calibration artifact of any kind exists.
- **Threshold saved**: **No.** No decision-threshold value is persisted anywhere.
- **Feature order consistency**: cannot be evaluated for inference, because **no inference
  code exists at all** (`backend/app/ml/` is empty) — there is nothing that could get the
  feature order wrong or right, because nothing loads these models.
- **XGBoost / LSTM**: no `.joblib` for either. `xgboost` (3.4.1) and `shap` (0.52.0) packages
  were installed in this Python environment **today, 2026-09-18**, hours before this audit —
  but nothing has been retrained or re-explained since. Every existing metric/artifact in the
  repo predates that installation. `tensorflow` remains not installed; LSTM remains
  unexercised, consistent with prior docs.

**Verdict: NOT PRODUCTION READY** — per the audit's own stated rule, a model with no saved
threshold, no calibration, and (most importantly) zero inference code path connecting it to
the running application cannot be called production-ready, independent of how good its
offline metrics are.

---

## 5. Verification of Reported Results

| Claim | Verdict | Detail |
|---|---|---|
| LogReg ROC-AUC≈0.777, Recall≈0.889, Precision≈0.0006, F1≈0.0013, PR-AUC≈0.0014 | **VERIFIED — but from `flooddata`, not FloodShield-Zambia** | Confirmed exact match against `C:\Users\Humphrey\OneDrive\Desktop\flooddata\data\reports\experiment_results.csv` this session. Zero references to this project or its numbers exist anywhere in `ai-engine/` or its docs. |
| GradientBoosting recall≈0.667, ROC-AUC≈0.649 (post sample-weight fix) | **VERIFIED — same caveat** | Same `flooddata` project; this fix was made and verified earlier this session, in that separate folder. |
| Experiment D ROC-AUC 0.587→0.588 (coordinate correction) | **VERIFIED — same caveat** | Same `flooddata` project. |
| `ai-engine/`'s own results (implicitly assumed related) | **DIFFERENT PROJECT, DIFFERENT NUMBERS** | See below. |

**`ai-engine/`'s actual, independently-verified real results** (`ai-engine/reports/
baseline_comparison.csv`, cross-checked line-for-line against `experiments/run_005–008/
metrics.json`, which match `docs/ML-METHODOLOGY.md`'s table exactly):

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| LogisticRegression | 0.917 | 0.204 | 0.489 | 0.288 | 0.850 | 0.132 | 0.069 |
| DecisionTree | 0.903 | 0.082 | 0.178 | 0.112 | 0.553 | 0.043 | 0.082 |
| RandomForest | 0.952 | 0.050 | 0.022 | 0.031 | 0.790 | 0.072 | 0.058 |
| GradientBoosting | 0.966 | 0.000 | 0.000 | 0.000 | 0.581 | 0.039 | 0.035 |

GradientBoosting predicts all-negative (0 recall) — a real, disclosed class-imbalance problem
(`docs/bug-register.md` BUG-17/18/19), distinct from the (already fixed, in the *other*
project) GradientBoosting issue you asked about.

An older run (`experiments/run_001-004`, dated 2026-07-02) shows much higher, "too good"
scores — this is the pre-fix, leaky-proxy-label run the docs describe, kept on disk as a
historical before/after record. Its presence is a good internal consistency check, not a
contradiction.

---

## 6. Model Deployment Audit

Traced the full requested chain for `ai-engine/`'s models:

```
Frontend request → API endpoint → preprocessing → model loading → prediction →
calibration → threshold → risk classification → API response → frontend display
```

**Every step from "API endpoint" onward is missing.** `GET /api/v1/predictions` is the only
prediction-related endpoint; it performs `SELECT * FROM predictions` (real DB-backed, real
code) and returns `[]` because that table has 0 rows. There is no `POST /predict` endpoint,
no code anywhere in `backend/` that imports `joblib`, calls `.predict()`/`.predict_proba()`,
or references any file under `ai-engine/`. This was independently confirmed by (a) `backend/
app/ml/` being empty, (b) a full grep of `backend/app/` for `joblib`/`predict(`/`.pkl`/
`ai-engine` with zero hits, and (c) live-testing `GET /api/v1/predictions` against the real
database this session — real query, real empty result.

**Verdict: REAL ML exists (in `ai-engine/`, offline) — MOCK/DEMO DATA does not exist anywhere
— but there is also NO CONNECTION between the two.** The honest current state is "an empty,
real endpoint," not "a fake prediction."

---

## 7. Model Artifact Audit
See Section 4 (audited together per the artifacts' shared location).

---

## 8. Backend/API Audit

All 21 real endpoints, verified by reading every router function body in full (not just
signatures) and cross-checked against `backend/tests/`:

| Endpoint | Purpose | Implemented | Tested | Real DB | Real ML |
|---|---|---|---|---|---|
| GET /health | Liveness | Yes | No dedicated test | N/A | N/A |
| POST /auth/register | Create user | Yes | Yes | Yes | — |
| POST /auth/login | Authenticate | Yes | Yes | Yes | — |
| GET /auth/me | Caller profile | Yes | Yes | Yes | — |
| GET /locations | List locations | Yes | Yes | Yes | — |
| GET /flood-events | List events | Yes | Yes | Yes | — |
| GET /weather/{id} | List observations | Yes | Yes | Yes | — |
| POST /weather/{id}/ingest | Real NASA POWER fetch+store | Yes | Yes | Yes | — |
| GET /predictions | List predictions | Yes | Yes | Yes | **No — honestly empty** |
| GET /alerts | List alerts | Yes | Yes | Yes | — |
| POST /alerts | Create alert | Yes | Yes | Yes | — |
| GET /citizen-reports | List reports | Yes | Yes | Yes | — |
| POST /citizen-reports | Submit report | Yes | Yes | Yes | — |
| POST /citizen-reports/{id}/moderate | Moderate report | Yes | Yes | Yes | — |
| GET /models | List model versions | Yes | Yes | Yes | **No — 0 rows** |
| GET /models/{id} | Get one model version | Yes | Yes | Yes | — |
| GET /data-sources | List catalog | Yes | Yes | Yes | — |
| POST /data-sources/{id}/check | Live health check | Yes | No test found | Yes | — |
| GET /system-status | Live component health | Yes | Yes | Yes | — |
| GET /notifications | Own notifications | Yes | Yes | Yes | — |
| POST /notifications/{id}/read | Mark read | Yes | Yes | Yes | — |

19/21 have direct test coverage. Every endpoint queries the real database — zero hardcoded
responses found anywhere in `backend/app/api/`.

Live-tested this session (not just read): `/health`, `/locations`, `/flood-events`,
`/predictions`, `/system-status`, and `POST /weather/{id}/ingest` all confirmed working
against the real live Supabase database.

---

## 9. Database Audit

1. **Is PostgreSQL installed?** Not locally — this project now uses a **live, hosted Supabase
   Postgres 17.6** instance instead (wired up this session).
2. **Is the database running?** Yes — confirmed live.
3. **Can the backend connect?** Yes — confirmed via the app's own `SQLAlchemy` engine, not
   just a raw driver test.
4. **Does the schema exist?** Yes — 13 real tables, confirmed via a live
   `information_schema.tables` query: `alerts, audit_logs, citizen_reports, data_sources,
   flood_events, locations, model_versions, notifications, predictions, roles, users,
   weather_observations`, plus `alembic_version`.
5. **Can migrations run?** Yes — both real Alembic migrations applied cleanly this session
   (`927a162df6ca` is HEAD).
6. **Can the application read/write data?** Yes — verified via real seed data (3 locations,
   14 flood events, 5 roles, 4 data sources, 1 dev-admin user) and a real end-to-end weather
   ingestion (11 rows written from a live NASA POWER call).
7. **Are there database tests?** Yes — `backend/tests/database/test_constraints.py`, part of
   the 49 tests, all passing against the live DB.

Real FK relationships and indexes confirmed via live schema query (9 foreign keys, 18
indexes including 3 unique constraints on `roles.name`, `data_sources.name`,
`model_versions.version`).

**Status: no longer BLOCKED.** Previously blocked by no local PostgreSQL; resolved this
session via a real hosted Supabase database, not a workaround or mock.

---

## 10. Frontend Audit

| Feature | Exists | Notes |
|---|---|---|
| Dashboard | Yes | Real KPI cards, mostly zero-data (honest) |
| Zambia map | Yes | Real Leaflet + OpenStreetMap tiles, plots real locations. No risk-color overlay (nothing to color by) |
| Risk-level badges | Yes | 4-tier, used across Dashboard/Predictions/Alerts; RiskMap legend only, not applied to markers |
| Probability/% display | Partial | Code exists and would render a real number, but unreachable today since `/predictions` is empty |
| Location selection | Yes | Dropdown (CreateAlert) + map-click (RiskMap) |
| Date/horizon selection | **No** | Does not exist anywhere in the frontend |
| Submit/run-prediction flow | **No** | Frontend can only ever *read* predictions (`GET`); no `POST /predict`-equivalent action exists in frontend or backend |
| Historical flood visualization | Partial | Real table/card view of the 14 real events + KPI summary; no chart/timeline |
| Charts | **No** | No charting library installed at all (`package.json` confirmed) |
| Model explanation display | **No** | `AIModel.tsx` shows model metadata/metrics JSON only — no SHAP/feature-importance UI exists even conceptually |
| Alerts UI | Yes | Real list + real POST-backed creation form, role-gated |
| Responsive design | Yes | 3 real `@media` breakpoints |
| Loading states | Yes | Shared `useFetch` hook + `LoadingState` component, used on every data page |
| Error states | Yes | `ErrorState` with a real retry button, not a silent failure |

Every data-bearing feature uses **real API data** — the earlier full-codebase sweep (this
session) and this frontend-specific pass both independently found zero mock/hardcoded/fake
data anywhere in `frontend/src/`.

---

## 11. Flood Alert System

- Threshold-based automatic alerts: **NOT IMPLEMENTED** (no code triggers an alert from a risk
  score, since no risk score is ever produced).
- Location-specific alerts: Implemented (an alert is tied to a `location_id`).
- Risk-level alerts: Implemented as a manual field on alert creation (a human picks the risk
  level; it is not computed).
- SMS: **NOT IMPLEMENTED** (`TWILIO_*` env vars exist but are unused — no Twilio client code
  found anywhere).
- Email: **NOT IMPLEMENTED**.
- Push notifications: **NOT IMPLEMENTED** (in-app `notifications` table only, no push
  provider).
- Automatic alerts: **NOT IMPLEMENTED**.

The alert system that exists is a real, working, **manually-triggered, dashboard-only**
notice board — not an automated flood-warning system.

---

## 12. Real-Time / Current Weather

`ai-engine/`'s dataset is a **historical CSV pipeline** (2000–2023, downloaded once, static
on disk). The **backend**, separately, has a genuine **real-time capability**: `POST /weather/
{id}/ingest` makes a live NASA POWER API call at request time — verified working this session
(11 real observations fetched and stored for the last 10 days, live).

**Distinguish clearly**: the trained models were built entirely from the historical CSV
pipeline; the real-time ingestion endpoint exists and works, but produces data that no model
or prediction pipeline currently consumes (see Section 6). A genuine, real bug was found and
fixed this session in this real-time path: NASA POWER's `-999` "no data yet" sentinel (for
the most recent 1-3 days) was being stored as a literal reading instead of `null` — fixed in
`backend/app/integrations/weather_provider.py`.

---

## 13. Dashboard Risk Calculation

There is no risk-calculation logic to trace. The frontend never computes or displays a
model-derived risk level for any location — `RiskBadge` renders whatever `risk_level` string
already exists on a `Prediction` or `Alert` record fetched from the API. Since `predictions`
has 0 rows and every current alert is manually authored, **no risk badge shown anywhere in
the app today reflects a real model output** — they reflect either nothing (empty state) or a
human's manual choice (alert creation form). This is honest (no hardcoded fake risk value
exists), but it means "dashboard risk calculation" as a real pipeline step does not exist yet.

---

## 14. Security Audit

- **Secrets committed to repo**: None found (`git ls-files` scan for `.env`/secret-pattern
  strings returned only the safe `.env.example` template).
- **`.env` handling**: Correctly gitignored, confirmed via `git check-ignore`.
- **API keys/DB passwords**: Not committed; live Supabase credentials this session were only
  ever written to the local, gitignored `.env` files.
- **Authentication**: Real bcrypt password hashing + real JWT issuance/verification, no
  hardcoded/mock users (confirmed by reading `core/security.py`/`core/deps.py` in full).
- **Authorization**: Real DB-backed role checks (`require_roles()` reads the live user row,
  not a token claim).
- **CORS**: Real origin allowlist (not `"*"`), though `allow_methods`/`allow_headers` are
  wildcarded — acceptable but worth tightening for production.
- **SQL injection**: None found — 100% SQLAlchemy ORM/parameterized queries, only one raw
  `text()` call and it's a static literal (`SELECT 1`).
- **Command injection**: None found — zero `subprocess`/`os.system`/`eval`/`exec` calls
  anywhere in `backend/app/`.
- **Path traversal**: None found — no endpoint builds a filesystem path from request input.
- **File upload**: Not implemented at all (no attack surface, but also no feature).
- **Exposed debug endpoints**: **Real, unfixed finding** — `/docs`, `/redoc`, `/openapi.json`
  are always exposed regardless of `ENVIRONMENT`; `main.py` never conditionally disables them.
- **Sensitive info in logs**: Clean — no password/token/secret values found passed to any
  logger call.
- **P0 fix verification**: **Confirmed real and correctly wired.** `config.py`'s
  `_refuse_insecure_defaults_outside_development` validator is a live `@model_validator`
  on the `Settings` class itself (not dead code), runs on every instantiation via
  `get_settings()`, and is used throughout the app (`main.py`, `security.py`,
  `system_status.py`, etc.). Independently re-verified this session by triggering it with a
  simulated production environment and confirming it raises correctly.

---

## 15. Testing Audit

| Suite | Total | Passed | Failed | Skipped | Blocked |
|---|---:|---:|---:|---:|---:|
| Backend (`backend/tests/`) | 49 | **49** | 0 | 0 | 0 (was BLOCKED by no local Postgres; resolved via Supabase this session) |
| ai-engine (`ai-engine/tests/`) | 31 | **31** | 0 | 0 | 0 |
| Frontend | 0 | — | — | — | **BLOCKED — no test framework installed, no `test` script exists** |

Both existing suites were **actually executed this session**, not just listed. No end-to-end
(Playwright/equivalent) suite exists — all E2E verification to date (including this session's)
has been manual.

---

## 16. End-to-End Test (performed this session)

| Step | Result |
|---|---|
| 1. Start database | **Success** — live Supabase Postgres |
| 2. Run migrations | **Success** — both migrations applied |
| 3. Start backend | **Success** — on port 8010 (8000 was occupied by an unrelated local project) |
| 4. Start frontend | **Not performed this pass** (would need port 8000 freed or `VITE_API_BASE_URL` wired — known gap, see Section 17) |
| 5. Load application | Not performed (depends on step 4) |
| 6. Select a Zambian location | Not performed (depends on step 4) — but `GET /locations` confirmed 3 real seeded locations available |
| 7. Submit prediction | **Cannot be performed — no such action exists in the app** (see Section 10/13) |
| 8-13. Backend receives → model loads → features → prediction → probability → risk level | **Cannot occur — no code path exists** (see Section 6) |
| 14. Frontend displays result | N/A |

What **was** completed end-to-end this session, for real: real weather ingestion (backend →
live NASA POWER → real DB write, verified with actual stored rows), real auth flow (tested via
the 49-test suite), real CRUD across every resource type (tested via the same suite).

---

## 17. Documentation Audit — Discrepancies Found

| Doc | Claim | Actual | Type |
|---|---|---|---|
| `frontend/src/pages/About.tsx` (fixed this session) | "11 events", "NASA POWER blocked" | 14 events; NASA POWER works from this machine | Was outdated, now fixed |
| `backend/app/api/system_status.py` (fixed this session) | "NASA POWER requests ... currently blocked" | Live-verified working | Was outdated, now fixed |
| `docs/missing-features.md` line 40 | Describes proxy-label leakage as a present tense "still missing" item, without the "only when proxy path is used" caveat | Current saved models use real event labels, not the leaky proxy path (verified via row-count cross-check) | Misleading if read in isolation — not fixed this pass (audit-only) |
| `docs/missing-features.md` / `bug-register.md` / `ML-METHODOLOGY.md` | "xgboost/shap not installed" | Both now installed (today, hours before this audit) — but unexercised, so substantive conclusions still hold | Stale reason, correct conclusion — not fixed this pass |
| `docs/missing-features.md` "26-test suite" | 26 tests | Now 31 (suite grew) | Minor staleness |
| `docs/api-inventory.md`, `docs/verified-endpoints.md` | Endpoint list | Matches actual 21 endpoints exactly | **Accurate, no discrepancy** |
| No doc currently states | `main.py`'s RobustScaler is fit before the split (minor leakage) | Confirmed in code this session | **New finding, not yet documented anywhere** |
| No doc currently states | `/docs`/`/redoc`/`/openapi.json` always exposed | Confirmed in code this session | **New finding, not yet documented anywhere** |

No feature was found to be documented as complete while actually being fake/fabricated —
every discrepancy found is either stale wording or an incomplete caveat, not a false claim of
functionality.

---

## 18. Research Requirements Audit

| Requirement | Status | Evidence |
|---|---|---|
| Historical flood data integration | COMPLETED | 14 real, sourced events, `ai-engine/data/external/` |
| Meteorological data integration | COMPLETED (historical) / PARTIAL (real-time) | 8,766-row historical CSV; real-time ingestion works but is disconnected from modeling |
| Data preprocessing | COMPLETED | Real cleaning pipeline, Section 3 |
| Feature engineering | COMPLETED | Real 54-feature set, Section 3 |
| Machine-learning modelling | COMPLETED (for 4 models) / MISSING (XGBoost, LSTM) | Real trained LR/DT/RF/GB; no XGBoost or LSTM artifact exists |
| Time-aware validation | COMPLETED | Verified chronological, non-shuffled split |
| Model comparison | COMPLETED | Real 4-model comparison table, Section 5 |
| Flood-risk prediction (serving) | **MISSING** | No inference code path exists (Section 6) |
| Explainability | PARTIAL | Real, complete SHAP code exists; never executed, zero output files |
| Decision-support visualization | PARTIAL | Map/dashboard/badges are real; no chart, no explainability UI, no probability currently reachable |

---

## 19. Final Status Matrix

| Component | Status | Evidence | What Remains |
|---|---|---|---|
| Data collection | COMPLETED | 8,766 real weather rows + 14 real events, verified by direct count | — |
| Data cleaning | COMPLETED | Real `DataCleaner`, Section 3 | — |
| Flood labels | PARTIAL | Real-label path used for current models; proxy path still leaky and unfixed in code | Fix or remove `_add_proxy_labels()`'s leakage, or clearly gate it out |
| Feature engineering | COMPLETED | Real 54-feature pipeline | — |
| ML training | PARTIAL | 4 real models trained; XGBoost/LSTM missing | Train XGBoost now that it's installed; provision Python 3.11 for LSTM |
| Model evaluation | COMPLETED | Real metrics, cross-verified against saved files | — |
| Calibration | MISSING | No artifact anywhere in `ai-engine/` | Add calibration (the separate flooddata project already shows how) |
| Model artifact | PARTIAL | Models+scaler+features saved; no threshold/calibration; no designated "active" model | Register one in `model_versions`; save a threshold |
| API | COMPLETED | 21 real, DB-backed, mostly-tested endpoints | Add tests for `/health` and `POST /data-sources/{id}/check` |
| Database | COMPLETED | Live Supabase, real schema/migrations/data, 49/49 tests pass | — |
| Frontend | COMPLETED (as a real, honest UI) | Real components, zero mock data | Charts, date/horizon picker, explainability UI don't exist |
| Dashboard | COMPLETED | Real KPIs | Data will stay empty until ML is wired |
| Map | COMPLETED | Real Leaflet map | No risk-color overlay (needs real predictions to color by) |
| Alerts | PARTIAL | Real manual/dashboard alerts | SMS/email/automatic triggering all NOT IMPLEMENTED |
| Security | PARTIAL | No injection/secret issues found; P0 fixed | `/docs` always exposed; CORS methods/headers wildcarded |
| Testing | COMPLETED (backend+ai-engine) / MISSING (frontend/E2E) | 80/80 real tests pass | Add frontend test framework; add a real E2E suite |
| Documentation | PARTIAL | Mostly accurate; several stale/ambiguous claims listed in Section 17 | Apply Section 17's fixes |
| Deployment | MISSING | No Dockerfile/CI/process supervision anywhere | Entire deployment story still to be built |
| End-to-end integration | **MISSING** | Traced in Section 16 — the chain breaks at "backend has no ML code path" | This is the single largest remaining gap |

---

## 20. Priority List

### P0 — Blocking (prevents demonstration)
- No prediction-serving code exists at all (Section 6) — without this, "demonstrate the
  system end-to-end" cannot include an actual prediction, only static/empty screens.
- `/docs`, `/redoc`, `/openapi.json` always exposed (quick fix, real security gap).

### P1 — Important (should be done before final submission)
- Wire at least one `ai-engine/` model into the backend (load `.joblib`, add a real inference
  endpoint, register it in `model_versions`) — even an honestly-labeled "research-grade,
  low-precision" model beats a permanently-empty endpoint for a demo.
- Add calibration + a documented decision threshold to whichever model is wired in (mirror the
  method already proven in the separate flooddata project).
- Fix `docs/missing-features.md` line 40's ambiguity (Section 17).
- Add a `VITE_API_BASE_URL` env override so frontend/backend can run on non-default ports/hosts
  without a rebuild (also unblocks the frontend E2E step skipped in Section 16).
- Fix the RobustScaler leakage (fit on train split only) — small effort, real methodological
  correctness improvement, directly relevant to "final-year research rigor."
- Decide, explicitly, whether the flooddata project's more rigorous pipeline should be migrated
  into `ai-engine/` — right now a reader of this repo alone would never discover that work
  exists.

### P2 — Optional
- SHAP execution + saved output (code already exists, just never run).
- XGBoost training (now that the package is installed).
- Charting library + a real trends/analytics view.
- Date/horizon picker in the frontend.
- SMS/email alert delivery.
- Dockerfile / CI pipeline / process supervision.
- Frontend automated tests, a real E2E suite.
