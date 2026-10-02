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
| `weather_observations` | `POST /api/v1/weather/{id}/ingest`, `backend/scripts/populate_real_data.py` | Only ever populated by a real successful NASA POWER fetch, never seeded with placeholder values. Carries `temperature_max_c`, `temperature_min_c` and `wind_speed_10m_ms` as of migration `b4c1a7e92f30`; rows ingested before it hold NULL there and are skipped by inference rather than substituted. |
| `model_versions` | `backend/scripts/register_model.py` | Holds the registered served model and its honestly-reported metrics, including the corrected study's finding that it does not beat a seasonal baseline. |
| `predictions` | `backend/scripts/populate_real_data.py` | Real model output over real weather. Each row records `observation_date`, the `(t, t+7]` target window, the feature-contract version and a staleness flag, so a stored prediction can be checked against what actually happened. |
| `alerts` | `POST /api/v1/alerts` (real, via the Create Alert screen) | Genuinely persisted. No workflow states beyond a fixed `"issued"` status — see `docs/API.md`. |

## Not yet implemented

`RiskAssessment`, `FloodEvent`-as-remote-sensing-product, `CitizenReport`,
`PredictionExplanation`, `SystemUser` from the candidate entity list in
`docs/ARCHITECTURE.md` — added when the phases that need them (Citizen Reporting, Auth)
actually begin. No indexes beyond primary/unique keys have been tuned; this is a
development skeleton, not a performance-reviewed schema.
