# Architecture — FloodShield Zambia

Status: draft, Phase 0 (no code implemented yet — this describes the target
architecture the repository is scaffolded for, not a running system).

> **Note (2026-09-08):** this "Phase 0" framing is stale — a real, running backend and
> frontend have existed since before this note was added (see
> `docs/AUDIT-REPORT-2026-09-08.md` for the current, evidence-based state of the whole
> project). The Backend/Frontend tree diagrams below have been updated in place to
> reflect the actual current structure, including a Phase 1 architecture-alignment pass
> that added a `repositories/`/`integrations/` layering to the backend and a
> `constants.ts`/`providers.tsx`/named-layouts structure to the frontend. The rest of
> this document (AI engine section, database entity list, deployment section) still
> describes target/planned state, not current state — treat those sections as
> aspirational until cross-checked against the audit report.

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
    api/            # FastAPI routers (predictions, weather, locations, alerts, reports)
    models/         # ORM models (SQLAlchemy)
    schemas/        # Pydantic request/response schemas
    services/       # orchestration only — no direct DB or HTTP calls (delegates below)
    repositories/   # DB persistence, one class per aggregate (WeatherObservationRepository,
                    # DataSourceRepository) — the only code that calls db.add()/db.commit()
    integrations/   # external I/O behind a swappable interface (WeatherProvider ->
                    # NasaPowerWeatherProvider in production, MockWeatherProvider in tests;
                    # HttpHealthChecker for data-source connectivity probes)
    database/       # session/engine setup
    ml/             # model loader + inference wrapper (loads ai-engine/models/ artifacts) —
                    # still empty; not wired up until a later phase (see AUDIT-REPORT-2026-09-08.md)
    core/           # config, security, logging
  tests/
    support/        # test-only doubles (e.g. MockWeatherProvider), never imported by app/
```

Responsibilities: prediction endpoints, weather ingestion trigger/schedule, model
inference (via a saved artifact, never retraining), database access, auth (if required),
alert orchestration, request validation, and auto-generated OpenAPI/Swagger docs.
`services/` never touches a DB session or makes an HTTP call directly — it calls into
`repositories/` (persistence) and `integrations/` (external I/O), both of which are
FastAPI dependencies so tests can override them without a real database or network call
(the same `app.dependency_overrides` mechanism already used for `get_db`). No `tasks/`
layer exists yet because nothing in the app currently runs on a schedule — weather
ingestion and data-source checks are both purely request-triggered.

## Frontend

```text
frontend/
  src/
    components/   pages/   hooks/   types/   context/
    constants.ts   # single source of truth for the role set + primary nav (previously
                    # duplicated across types/index.ts and context/AuthContext.tsx)
    providers.tsx   # composes app-wide providers (currently just AuthProvider)
    layouts/
      PublicLayout.tsx     # Landing, About
      AuthLayout.tsx       # Login, Signup
      DashboardLayout.tsx  # the 13 authenticated-app routes (sidebar + topbar), formerly AppShell
    services/
      http.ts        # shared fetch/token/ApiError plumbing
      api.ts         # re-export barrel over the domain files below (kept so existing
                      # page imports don't need to change)
      auth.ts  locations.ts  floodEvents.ts  predictions.ts  weather.ts  alerts.ts
      citizenReports.ts  models.ts  dataSources.ts  systemStatus.ts
  tests/
```

React + TypeScript is the production UI. It talks to the backend over the documented API
contract only. Every screen implements loading / success / empty / error / validation
states — no screen may render a blank page or a fabricated statistic when data is
unavailable (governing prompt, sections 29, 36). `PublicLayout`/`AuthLayout` are
intentionally inert passthroughs today (no visual change from before this split) — they
exist so public/auth pages have a named layout slot to receive real chrome later without
another routing refactor.

## Database

PostgreSQL is the source of truth for persistent application state — not the frontend.
Candidate entities (to be finalized in `docs/DATABASE.md` once schema work begins):
`Location, WeatherObservation, Prediction, RiskAssessment, FloodEvent, Alert,
CitizenReport, ModelVersion, PredictionExplanation, SystemUser`.

**Update (2026-09-08, Phase 2):** the real schema (`docs/database-schema.md`) now has 12
tables, including a real `notifications` table added this phase. **Scope note:**
notifications are only generated for citizen-report moderation (notifying the original
reporter) — `Alert.audience` is a free-text field, not a set of real user ids, so alert
issuance deliberately does not generate notifications yet; doing so without a real
targeting mechanism would mean fabricating one. Predictions and data-source sync have
the same gap for the same reason. This is a scope decision, not an oversight — see
`docs/missing-features.md` for the full list of what's still not covered.

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
