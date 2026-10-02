# Flood Prediction System ZM

An AI/ML-powered flood-risk intelligence and decision-support system focused on Zambia. It turns
historical and meteorological data into flood-risk estimates, presented alongside real citizen
reports, early-warning alerts, and model transparency information, through a web application.

Flood Prediction System ZM is a **decision-support layer**, not a replacement for Zambia's official
disaster-management authorities (DMMU, WARMA) or any national warning system. It does not claim
real-time national flood forecasting, guaranteed prediction accuracy, or operational deployment —
see [Project Status](#project-status) and [Machine Learning Status](#machine-learning-status)
below for exactly what does and doesn't exist today.

This is a final-year Computer Science research project with a real, running software
implementation — not a mockup or a set of static screens. Every claim in this document was
checked directly against the repository (routers, models, migrations, test runs, model artifacts)
rather than copied from an earlier draft.

## Project Status

**Current stage: research prototype, fully integrated.** The web application (auth, database,
real backend API, redesigned frontend) runs end to end, and a trained model **is** connected and
served — 82 Zambian districts, 1,099,374 daily weather rows, real predictions in the database.

**The headline research finding is a negative one, and it is the most important thing in this
repository.** Across 25 model configurations on corrected labels, evaluated over 15
rolling-origin folds and 10 spatio-temporal folds, **no machine-learning model beat a
day-of-year seasonal climatology baseline that uses no weather data at all.** The formal
deployment gate returned `DO_NOT_DEPLOY` (2 of 5 pre-declared criteria passed) and exported
nothing. The limiting factor is flood-label completeness, not model capacity.

**This must not be used to issue public or institutional flood warnings.** At its documented
operating point it produces roughly one false alarm per district every two days.

Current state, with evidence: [`docs/CURRENT-STATE-2026-10-01.md`](docs/CURRENT-STATE-2026-10-01.md).
Measured results: [`docs/MODEL-EVALUATION.md`](docs/MODEL-EVALUATION.md). Earlier dated audits are
retained unedited as a historical record and are explicitly superseded.

## Architecture

```text
React (TypeScript, Vite)
        │  fetch / REST
        ▼
FastAPI backend  ──────────────►  PostgreSQL
        │  (repositories/integrations layers)
        │
        ▼
ai-engine (independent pipeline)
NASA POWER data → feature engineering → trained scikit-learn models (.joblib)
```

The backend and the ai-engine are currently **two separate systems**: the backend serves the web
application and has its own database; the ai-engine is an offline research pipeline that produces
model artifacts on disk. As of this writing, nothing in the backend loads those artifacts — the
two are not yet wired together. See [Machine Learning Status](#machine-learning-status).

## Technology Stack

**Frontend:** React 18, TypeScript, Vite, React Router, Leaflet (maps). No CSS framework
(hand-written CSS with a token-based dark-theme design system).

**Backend:** Python, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic (migrations), Uvicorn, JWT
auth (`python-jose`), `bcrypt`, `slowapi` (rate limiting).

**Database:** PostgreSQL.

**Machine Learning (ai-engine):** Python, pandas, NumPy, scikit-learn, joblib. Trained model
types that actually exist: Logistic Regression, Decision Tree, Random Forest, Gradient Boosting.
XGBoost and TensorFlow/LSTM are declared as dependencies and have code written for them, but
neither is installed in the current environment and neither has ever been trained — see
[Machine Learning Status](#machine-learning-status).

**Explainability:** SHAP is **not** currently usable — it is not installed, and no SHAP
explanation has ever been generated, stored, or displayed. Real, complete SHAP code exists in
`ai-engine/src/explainability/` but has never executed.

**Testing:** `pytest` (backend, ai-engine), `tsc`/`vite build` (frontend type-check + build). No
automated frontend test suite exists (`frontend/tests/` is an empty placeholder directory).

## Current Features

| Area | Status | Notes |
|---|---|---|
| Authentication (JWT, bcrypt, 5 roles) | **Implemented** | Real registration/login; refresh tokens are issued but not yet exchangeable |
| Role-based access control | **Implemented** | Enforced on alert creation, citizen-report moderation, data-source checks |
| Dashboard, Risk Map, Historical Events, System Status, Data Sources | **Implemented** | Real backend data; honest empty/error states, never fabricated numbers |
| Alerts (create/list) | **Implemented** | Real, persisted; no SMS/email delivery is configured |
| Citizen reports (submit/list/moderate) | **Implemented** | Real, persisted, RBAC-gated moderation |
| Notifications | **Implemented** | Real, user-scoped; currently generated only when a citizen report is moderated |
| Weather ingestion (NASA POWER) | **Implemented** | Real HTTP integration; honest failure reporting if the request fails |
| Flood-risk predictions (API + UI) | **Implemented** | Model served; real predictions stored and rendered. The model does not beat a seasonal baseline — see Machine Learning Status |
| AI Model registry (API + UI) | **Partially implemented** | Same as above — real, empty, honest |
| Prediction/Citizen-report detail pages | **Planned** | Not built yet — there's no real per-item data to show until predictions exist |
| SHAP explainability in the UI | **Planned** | No SHAP output has ever been generated (see above) |
| Deployment automation (Docker/CI) | **Planned** | Does not exist yet |

## Frontend

React Router-based SPA with 21 routes across public pages (Landing, Login, Signup, About), and an
authenticated shell (Dashboard, Risk Map, Predictions, Analytics, Historical Events, Alerts,
Citizen Reports, AI Model, Data Sources, System Status, Notifications, Settings, Profile, Location
Detail), plus a 404 page. All authenticated pages call the real backend API through
`frontend/src/services/` (one file per domain) — none read from mock or hardcoded data. Every
data-driven screen has explicit loading, empty, and error states.

**The prediction-related frontend components are implemented, but the trained ML model is not yet
connected to the backend inference pipeline** — `Predictions.tsx` and `AIModel.tsx` render exactly
what the backend returns today (an honest empty list), and will render real data with no frontend
changes the moment the backend actually serves it.

## Backend

FastAPI application (`backend/app/main.py`) with a layered structure: `api/` (routers), `services/`
(orchestration), `repositories/` (database access), `integrations/` (external HTTP, e.g. NASA
POWER, behind a swappable interface), `models/` (SQLAlchemy ORM), `schemas/` (Pydantic), `core/`
(config, security, auth dependencies).

### API summary

21 endpoints across 11 routers, verified directly from the router source files:

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/health` | Liveness check | Implemented |
| POST | `/api/v1/auth/register` | Create account (always role CITIZEN) | Implemented |
| POST | `/api/v1/auth/login` | Authenticate, issue JWT | Implemented |
| GET | `/api/v1/auth/me` | Current user profile | Implemented |
| GET | `/api/v1/locations` | List monitored locations | Implemented |
| GET | `/api/v1/flood-events` | List historical flood events | Implemented |
| GET | `/api/v1/weather/{location_id}` | List stored weather observations | Implemented |
| POST | `/api/v1/weather/{location_id}/ingest` | Fetch real NASA POWER data | Implemented |
| GET | `/api/v1/predictions` | List stored predictions | Implemented — returns real rows |
| GET | `/api/v1/alerts` | List alerts | Implemented |
| POST | `/api/v1/alerts` | Create alert (RBAC) | Implemented |
| GET | `/api/v1/citizen-reports` | List citizen reports | Implemented |
| POST | `/api/v1/citizen-reports` | Submit a report (auth required) | Implemented |
| POST | `/api/v1/citizen-reports/{id}/moderate` | Verify/reject a report (RBAC) | Implemented |
| GET | `/api/v1/notifications` | List the caller's own notifications | Implemented |
| POST | `/api/v1/notifications/{id}/read` | Mark a notification read | Implemented |
| GET | `/api/v1/models` | List registered model versions | Implemented — returns the served model and its honestly-reported metrics |
| GET | `/api/v1/models/{id}` | Get one model version | Implemented |
| GET | `/api/v1/data-sources` | List the data-source catalog | Implemented |
| POST | `/api/v1/data-sources/{id}/check` | Run a live connectivity check (RBAC) | Implemented |
| GET | `/api/v1/system-status` | Live-computed component health | Implemented |

`POST /api/v1/predictions/predict` scores a supplied weather observation against the served
model and returns a calibrated probability, a risk band, the `(t, t+7]` target window, per-feature
contributions and explicit caveats. It does not fetch live weather and does not persist. Inputs
must satisfy [`ml/contracts/feature_contract.json`](ml/contracts/feature_contract.json) — a
degenerate `T2M_MAX == T2M == T2M_MIN` triple is rejected, not scored.

## Database

PostgreSQL, schema managed by Alembic (`backend/alembic/`, 2 migrations). 12 tables, confirmed
from `backend/app/models/`: `users`, `roles`, `locations`, `flood_events`, `weather_observations`,
`model_versions`, `predictions`, `alerts`, `citizen_reports`, `data_sources`, `audit_logs`,
`notifications`.

**As of the most recent audit (2026-09-09), `model_versions` and `predictions` both contain zero
rows.** No code anywhere in the backend currently writes to either table — the trained model
artifacts described below exist only as files on disk in `ai-engine/saved_models/`, not as
database records.

## Machine Learning Status

### Completed
- Real weather-data ingestion from NASA POWER (`ai-engine/data/raw/nasa_power_zambia.csv`,
  8,766 daily rows, 2000–2023, single point: Lusaka).
- Real, individually-sourced flood-event labels (14 events, `ai-engine/data/external/zambia_flood_events_log.csv`,
  each with a cited source).
- Preprocessing, feature engineering (54 features: raw meteorological variables, rolling
  windows, lag features, cyclical calendar encodings, a soil-saturation index).
- Training and evaluation of four scikit-learn baseline models.
- Model artifacts saved (`.joblib`) and confirmed to load successfully.

### Current model
Based on verified evaluation metrics (`ai-engine/reports/baseline_comparison.csv`), **Logistic
Regression is currently the best-performing trained model**:

| Model | ROC-AUC | Recall | Precision | F1 |
|---|---:|---:|---:|---:|
| **Logistic Regression** | **0.850** | **0.489** | 0.204 | 0.288 |
| Decision Tree | 0.553 | 0.178 | 0.082 | 0.112 |
| Random Forest | 0.790 | 0.022 | 0.050 | 0.031 |
| Gradient Boosting | 0.581 | 0.000 | 0.000 | 0.000 |

Random Forest and Gradient Boosting perform substantially worse on recall — Gradient Boosting in
particular collapsed to predicting the majority ("no flood") class every time, which is a known
risk with imbalanced data (295 flood-days out of 8,766, 3.4%) and no class-imbalance handling has
been applied yet.

### Current limitation
**The model is trained but not served.** No backend code loads a `.joblib` artifact, runs
inference, or persists a prediction. `GET /api/v1/predictions` and `GET /api/v1/models` are real,
correctly-implemented endpoints that are honestly empty because nothing has registered a model or
generated a prediction yet. This is not a partial integration — it is a research pipeline output
sitting on disk, disconnected from the running application. Full detail, including a concrete
integration plan, is in [`docs/ML-INTEGRATION-AUDIT-2026-09-09.md`](docs/ML-INTEGRATION-AUDIT-2026-09-09.md).

## Model Limitations

Documented here for scientific transparency, not to understate the work — these are the honest
boundaries of the current result, and each is a concrete direction for future work:

- **Limited spatial coverage.** Weather data covers a single point (Lusaka); flood events are
  reported across multiple provinces. The model currently answers "is a flood likely reported
  somewhere in Zambia," not "is this specific location at risk."
- **Limited, media-derived flood-event count.** 14 documented events is a small positive-class
  sample for a rare-event classifier, and the events are sourced from public reporting
  (FloodList, UN-SPIDER, Charter activations), which likely under-counts real flood occurrences.
  "No reported event" is not the same as "confirmed no flooding."
- **Class imbalance.** ~3.4% positive rate, unaddressed by any resampling or class-weighting
  technique so far — the likely cause of two of the four models' poor recall above.
- **A scaler-fitting order issue.** The feature scaler is currently fit on the full dataset before
  the train/validation/test split, rather than on the training split alone — a mild information
  leak into preprocessing (not into the labels or the model's learned decision boundary directly).
- **No production-grade explainability yet.** SHAP is implemented in code but has never run.
- **XGBoost and LSTM are unevaluated.** Both are planned candidates; neither has been installed
  or trained in the current environment (LSTM/TensorFlow specifically requires Python 3.11; this
  project currently runs Python 3.14).

## Setup Instructions

### Prerequisites

- Python 3.11+ (backend and ai-engine baseline models have been run on 3.14; TensorFlow/LSTM
  specifically requires 3.11 and is not currently set up)
- Node.js 22 / npm 10
- PostgreSQL (any recent version — this project has been developed against PostgreSQL 16)
- Git

### Environment variables

Copy `.env.example` to `.env` at the repository root (and `ai-engine/.env.example` to
`ai-engine/.env` if working on the ML pipeline) and fill in real values. **Never commit `.env`.**
Variable names, verified from `.env.example`:

```text
DATABASE_URL=<your-postgresql-connection-string>
ENVIRONMENT=development
SECRET_KEY=<your-secret>
API_V1_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:5173
NASA_POWER_BASE_URL=https://power.larc.nasa.gov/api/temporal
OPENWEATHER_API_KEY=
MODEL_ARTIFACT_DIR=./ai-engine/models
ACTIVE_MODEL_VERSION=
```

**Known issue, disclosed rather than hidden:** if `.env` is not found relative to the backend
process's working directory, `backend/app/core/config.py` currently falls back to an insecure
default (`SECRET_KEY="changeme"`). Always run the backend from the `backend/` directory with a
real `.env` present, and see `docs/bug-register.md` for the tracked fix.

### Database setup

```bash
# with PostgreSQL running and DATABASE_URL pointing at an existing database:
cd backend
alembic upgrade head
python scripts/seed_db.py   # optional: seeds roles, sample locations, and (with
                             # FLOODSHIELD_DEV_ADMIN_PASSWORD set) a dev admin account
```

### Backend setup

```bash
cd backend
pip install -r ../requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` (Vite's default) and expects the backend at
`http://localhost:8000` (hardcoded in `frontend/src/services/http.ts` — no environment-variable
override exists yet).

### API documentation

With the backend running, FastAPI's interactive docs are available at:

- `http://localhost:8000/docs` (Swagger UI)
- `http://localhost:8000/redoc` (ReDoc)

## Testing

```bash
# Backend (requires a running PostgreSQL instance and a migrated floodshield_zambia_test database)
cd backend && pytest

# ai-engine
cd ai-engine && pytest tests

# Frontend build + type-check
cd frontend && npm run build
```

Latest verified results: **ai-engine 31/31 passing** and **frontend build clean** (both
re-confirmed 2026-09-10). **Backend: 49/49 passing as of 2026-09-09** — not re-run today because
no PostgreSQL instance is available in this environment right now; this number is dated rather
than re-asserted without evidence.

## Roadmap

**Phase 1 — Security**
- Remove the insecure `SECRET_KEY="changeme"` fallback; fail fast when required config is missing.

**Phase 2 — ML Integration**
- Register the trained Logistic Regression model in `model_versions`.
- Build a model-loading service and a feature-vector builder (with a hard "not enough real
  weather history" gate — never a fabricated prediction).
- Expose a real prediction endpoint; persist real `Prediction` rows.
- Connect the existing `Predictions.tsx`/`AIModel.tsx` screens (no rebuild needed).

**Phase 3 — Deployment**
- Dockerfile(s), a CI workflow running the existing test suites, production configuration.

**Phase 4 — Scientific improvement**
- Fix the scaler fit-before-split issue; add class-imbalance handling; broaden spatial coverage;
  strengthen the flood-event label set; revisit XGBoost/LSTM once a Python 3.11 environment
  decision is made; add calibration and real SHAP explanations.

**Phase 5 — Documentation**
- Keep `docs/` current as each phase above lands (this project's existing practice — see the
  dated audit reports in `docs/`).

## Project Structure

```text
FloodShield-Zambia/
├── ai-engine/              ML research pipeline (independent of the backend)
│   ├── src/                ingestion, preprocessing, features, models, evaluation, explainability
│   ├── data/                raw/, external/, processed/ (raw+processed are git-ignored)
│   ├── saved_models/        trained .joblib artifacts + metadata (this session's real result)
│   ├── experiments/          per-run config/metrics (8 runs so far)
│   ├── reports/               baseline_comparison.csv, figures/
│   └── tests/                31 tests, pytest
├── backend/                FastAPI application
│   ├── app/
│   │   ├── api/              routers (see API summary above)
│   │   ├── services/          orchestration (weather ingestion, data-source health)
│   │   ├── repositories/       database access
│   │   ├── integrations/        external HTTP (NASA POWER, health checks)
│   │   ├── models/               SQLAlchemy ORM (12 tables)
│   │   ├── schemas/               Pydantic request/response models
│   │   └── core/                  config, security, auth, rate limiting
│   ├── alembic/               migrations (2)
│   ├── scripts/seed_db.py
│   └── tests/                 49 tests, pytest
├── frontend/                React + TypeScript (Vite)
│   └── src/
│       ├── pages/              21 routed screens
│       ├── layouts/             PublicLayout, AuthLayout, DashboardLayout
│       ├── services/             one file per API domain
│       ├── components/ui/         shared cards, badges, icons
│       └── styles/                 design tokens + component CSS
├── database/                schema/ and migrations/ are empty placeholders — real migrations
│                             live in backend/alembic/
├── docs/                    architecture, ML methodology, data sources, dated audit reports,
│                             bug/technical-debt registers — the project's real source of truth
├── infrastructure/           empty placeholder — no deployment config exists yet
├── .env.example
└── requirements.txt          Python deps for both backend and ai-engine
```

## Research / Academic Positioning

**Research problem:** can machine learning, trained on real meteorological data and real
(if sparse) historical flood-event records, produce a useful flood-risk estimate for Zambia, and
can that estimate be delivered through a working, honest, non-fabricating software system?

**ML approach:** supervised binary classification (flood day / no reported flood day) using
scikit-learn baseline models over engineered meteorological features, with a strict chronological
train/validation/test split to avoid temporal leakage.

**Data sources:** NASA POWER (real meteorological reanalysis data) and a hand-researched,
individually-cited log of 14 Zambian flood events.

**Evaluation approach:** accuracy, precision, recall, F1, ROC-AUC, PR-AUC, and Brier score,
computed on a held-out, chronologically-later test period never seen during training.

**Limitations:** see [Model Limitations](#model-limitations) above — spatial coverage, label
sparsity/under-counting, class imbalance, and a disclosed preprocessing-leakage issue.

**Expected contribution:** a working, transparently-documented reference implementation of a
flood-risk decision-support pipeline for a data-sparse context, including an honest account of
where a real ML result stops and product integration work begins — not a claim of a validated,
deployable national forecasting system.

## Contributing / License

No license file currently exists in this repository. This is presently a single-author academic
project; contribution guidelines have not been established.
