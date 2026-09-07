# API — FloodShield Zambia

Status: **early skeleton**, built 2026-09-07 ahead of the normal phase order at the
user's explicit request, to demonstrate a real running system on the real (small,
incomplete) data gathered in Phase 1. This is not a claim that Phase 10 (Backend) is
complete — see "What's not here yet" below. Live reference: FastAPI's auto-generated
OpenAPI/Swagger docs at `/docs` on the running backend.

## Running it locally

```bash
cd backend
cp ../.env.example ../.env   # fill in DATABASE_URL for your local Postgres
pip install -r ../requirements.txt
python3 scripts/seed_db.py     # loads real locations + the real flood-event CSV
python3 -m uvicorn app.main:app --reload --port 8000
```

Requires a running PostgreSQL instance matching `DATABASE_URL` in `.env` — this project
targets Postgres per `docs/ARCHITECTURE.md`; no SQLite substitution was needed since a
local Postgres 16 instance was available in the build environment.

## Endpoints implemented

| Method | Path | Behavior |
|---|---|---|
| GET | `/health` | Liveness check. |
| GET | `/api/v1/locations` | Real seeded locations (Lusaka, Kanyama, Ng'ombe) with coordinate-confidence and source citations. |
| GET | `/api/v1/flood-events` | The 11 real, sourced rows from `ai-engine/data/external/zambia_flood_events_log.csv`. Explicitly not a validated label — see `docs/ML-METHODOLOGY.md`. |
| GET | `/api/v1/weather/{location_id}` | Stored weather observations for a location (empty until a real ingestion succeeds). |
| POST | `/api/v1/weather/{location_id}/ingest` | Makes a **real** HTTP request to NASA POWER for that location's last 10 days. Returns `{status: "success"\|"failed", observations_stored, error_detail}` — on failure, the actual exception is surfaced, never a fabricated success or synthetic data. In this project's development sandbox this call always fails (see `docs/DATA-SOURCES.md` — egress policy + robots.txt); it is expected to succeed from an unrestricted environment. |
| GET | `/api/v1/predictions` | Real predictions only. Legitimately returns `[]` — no model has been trained (Phases 5–9 not started). |
| GET | `/api/v1/alerts` | Real dashboard alerts, persisted in Postgres. Verified end-to-end: creating one via the frontend form immediately shows up here. |
| POST | `/api/v1/alerts` | Creates a real alert row (`title`, `risk_level`, `location_id`, `message`, `audience`, `channels`). Status is always `"issued"` — no draft/scheduled workflow yet. No delivery to any external channel; `channels` is metadata only. |
| GET | `/api/v1/system-status` | Computed at request time, not hardcoded: pings the DB with `SELECT 1`, counts real `weather_observations`/`model_versions`/`alerts` rows to decide each component's status. See `docs/DATABASE.md`. |

## What's not here yet

No auth/authorization, no rate limiting, no citizen-report endpoints, no alert
delivery workflow (draft→scheduled→issued→delivered) or external provider integration,
no `RiskAssessment`/`PredictionExplanation` entities, and no automated test suite
(`backend/tests/` is still empty) — none of which the Definition of Done (governing
prompt §41) would consider satisfied. Treat this API as a development skeleton to build
on, not a finished Phase 10.
