# Database — FloodShield Zambia

Status: **early skeleton**, built 2026-09-07 ahead of the normal phase order (see
`docs/API.md` for context). Real PostgreSQL 16, matching the target architecture — no
SQLite substitution. No formal migrations yet (`alembic` is not wired up); tables are
created by `Base.metadata.create_all()` on backend startup, which is fine for this
skeleton stage but is not the production migration path.

## Tables implemented

| Table | Populated by | Notes |
|---|---|---|
| `locations` | `backend/scripts/seed_db.py` | 3 real rows: Lusaka (city), Kanyama compound, Ng'ombe settlement. Coordinates are city-approximate, not surveyed — see `coordinate_confidence` column. |
| `flood_events` | `backend/scripts/seed_db.py`, from `ai-engine/data/external/zambia_flood_events_log.csv` | 11 real, sourced rows. Not a validated label — see `docs/ML-METHODOLOGY.md`. |
| `weather_observations` | `POST /api/v1/weather/{id}/ingest` only | Empty by default; only ever populated by a real successful NASA POWER fetch, never seeded with placeholder values. |
| `model_versions`, `predictions` | Nothing yet | Exist as schema only — no model has been trained (Phases 5–9 not started), so these are legitimately empty. |

## Not yet implemented

`RiskAssessment`, `FloodEvent`-as-remote-sensing-product, `Alert`, `CitizenReport`,
`PredictionExplanation`, `SystemUser` from the candidate entity list in
`docs/ARCHITECTURE.md` — added when the phases that need them (Alerts, Citizen
Reporting, Auth) actually begin. No indexes beyond primary/unique keys have been tuned;
this is a development skeleton, not a performance-reviewed schema.
