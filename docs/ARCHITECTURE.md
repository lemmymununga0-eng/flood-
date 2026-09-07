# Architecture — FloodShield Zambia

Status: draft, Phase 0 (no code implemented yet — this describes the target
architecture the repository is scaffolded for, not a running system).

## Three-component architecture

```text
             FLOODSHIELD ZAMBIA
                   |
       +-----------+-----------+
       |           |           |
       v           v           v
   AI ENGINE    BACKEND     FRONTEND
       |           |           |
       v           v           v
   ML Models    FastAPI      React
   Features     Database     Dashboard
   XAI          Services     Maps
   Evaluation   Alerts       Analytics
```

The three components communicate through defined interfaces only:

```text
Frontend  -->  Backend API  -->  AI Inference Service  -->  Model
```

The frontend never talks to the model directly. The AI engine trains models and produces
versioned artifacts; the backend loads those artifacts for inference. **Training and
inference are separate processes — the API never retrains a model inside a request**
(governing prompt, sections 18, 50).

## AI engine

```text
ai-engine/
  src/
    data/            # ingestion clients (NASA POWER, etc.)
    preprocessing/    # cleaning, validation, missing-data handling
    features/         # feature engineering (lags, rolling windows, accumulation)
    models/            # model definitions / training entry points
    evaluation/        # metrics, chronological CV, comparison reporting
    explainability/    # SHAP / feature-importance generation
    inference/         # batch/offline inference helpers used by the backend's ml/ layer
    utils/
  data/
    raw/ interim/ processed/ features/ external/
  models/              # versioned artifacts: model + scaler + metadata per version
  experiments/         # experiment tracking records
  reports/             # evaluation reports, comparison tables
  tests/
```

`data/raw/` is immutable — nothing overwrites it in place; every transformation produces
a new derived file under `interim/`, `processed/`, or `features/` with recorded
provenance (source, retrieval date, coordinates, date range, variables, units,
transformations, dataset version). See `docs/DATA-PIPELINE.md` (stub) once Phase 2 begins.

## Backend

```text
backend/
  app/
    api/        # FastAPI routers (predictions, weather, locations, alerts, reports)
    models/     # ORM models (SQLAlchemy)
    schemas/    # Pydantic request/response schemas
    services/   # business logic (risk engine, alert orchestration)
    database/   # session/engine setup
    ml/         # model loader + inference wrapper (loads ai-engine/models/ artifacts)
    core/       # config, security, logging
  tests/
```

Responsibilities: prediction endpoints, weather ingestion trigger/schedule, model
inference (via a saved artifact, never retraining), database access, auth (if required),
alert orchestration, request validation, and auto-generated OpenAPI/Swagger docs.

## Frontend

```text
frontend/
  src/
    components/  pages/  services/  hooks/  types/  layouts/
  tests/
```

React + TypeScript is the production UI. It talks to the backend over the documented API
contract only. Every screen implements loading / success / empty / error / validation
states — no screen may render a blank page or a fabricated statistic when data is
unavailable (governing prompt, sections 29, 36).

## Database

PostgreSQL is the source of truth for persistent application state — not the frontend.
Candidate entities (to be finalized in `docs/DATABASE.md` once schema work begins):
`Location, WeatherObservation, Prediction, RiskAssessment, FloodEvent, Alert,
CitizenReport, ModelVersion, PredictionExplanation, SystemUser`.

## API contract (draft — fields subject to change until Phase 10)

A prediction response is expected to carry only fields the implementation actually
supports, at minimum:

```text
location
timestamp
prediction_probability
risk_level
model_version
prediction_horizon
explanation
```

## Alerts

```text
Risk Engine  -->  Alert Service  -->  Notification Provider (e.g. Twilio)
```

The Alert Service is isolated so that a notification-provider outage never stops
prediction serving; failures are logged and surfaced honestly in the UI (never a fake
"SMS sent" confirmation).

## Deployment (planned, Phase 15)

Docker-based, environment-variable configuration via `.env` (never committed), free/
low-cost hosting preferred (section 55). No deployment infrastructure exists yet.
