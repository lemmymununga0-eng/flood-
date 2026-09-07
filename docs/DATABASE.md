# Database — FloodShield Zambia

Status: expanded 2026-09-07 to 11 tables with real Alembic migrations (`alembic`
is now wired up — `Base.metadata.create_all()` was removed from backend startup).
**The full, current schema lives in `docs/database-schema.md` — this file is kept for
history; treat database-schema.md as authoritative.** Real PostgreSQL 16, matching the
target architecture — no SQLite substitution.

## Tables implemented

| Table | Populated by | Notes |
|---|---|---|
| `locations` | `backend/scripts/seed_db.py` | 3 real rows: Lusaka (city), Kanyama compound, Ng'ombe settlement. Coordinates are city-approximate, not surveyed — see `coordinate_confidence` column. |
| `flood_events` | `backend/scripts/seed_db.py`, from `ai-engine/data/external/zambia_flood_events_log.csv` | 11 real, sourced rows. Not a validated label — see `docs/ML-METHODOLOGY.md`. |
| `weather_observations` | `POST /api/v1/weather/{id}/ingest` only | Empty by default; only ever populated by a real successful NASA POWER fetch, never seeded with placeholder values. |
| `model_versions`, `predictions` | Nothing yet | Exist as schema only — no model has been trained (Phases 5–9 not started), so these are legitimately empty. |
| `alerts` | `POST /api/v1/alerts` (real, via the Create Alert screen) | Genuinely persisted. No workflow states beyond a fixed `"issued"` status — see `docs/API.md`. |

## Not yet implemented

`RiskAssessment`, `FloodEvent`-as-remote-sensing-product, `CitizenReport`,
`PredictionExplanation`, `SystemUser` from the candidate entity list in
`docs/ARCHITECTURE.md` — added when the phases that need them (Citizen Reporting, Auth)
actually begin. No indexes beyond primary/unique keys have been tuned; this is a
development skeleton, not a performance-reviewed schema.
