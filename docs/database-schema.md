# Database Schema — FloodShield Zambia

Real PostgreSQL 16, schema managed by Alembic migrations
(`backend/alembic/versions/`) — not `Base.metadata.create_all()` (removed this
build). 12 tables (added `notifications` in the Phase 2 architecture-alignment pass,
2026-09-08). See `docs/DATABASE.md` for the earlier, smaller skeleton account;
this document supersedes it with the full current schema.

| Table | Purpose | Populated by |
|---|---|---|
| `roles` | The 5 fixed RBAC roles. | `scripts/seed_db.py`, once. |
| `users` | Real accounts, bcrypt-hashed passwords. | `POST /auth/register`, `scripts/seed_db.py` (one dev admin, opt-in via `FLOODSHIELD_DEV_ADMIN_PASSWORD`). |
| `locations` | Monitored locations. | `scripts/seed_db.py` (3 real, sourced rows). |
| `flood_events` | Sourced historical flood events. | `scripts/seed_db.py`, from the 11-row CSV. |
| `weather_observations` | Real weather data. | `POST /weather/{id}/ingest` only — empty until a real NASA POWER fetch succeeds. |
| `model_versions` | The model registry. | Nothing yet — Phase 9 (Model Packaging) not started. |
| `predictions` | Model-generated risk predictions. | Nothing yet — no trained model. |
| `alerts` | Dashboard early-warning alerts. | `POST /alerts` (ADMIN/ANALYST/OPERATOR only, this build). |
| `citizen_reports` | Citizen-submitted ground observations. | `POST /citizen-reports` (any authenticated user). |
| `data_sources` | Catalog of external data dependencies + live health. | `scripts/seed_db.py` (catalog rows); `POST /data-sources/{id}/check` (live status). |
| `audit_logs` | Append-only security-relevant action log. | Written at the point of the action (login, register, alert issued, report moderated). |
| `notifications` *(new 2026-09-08)* | Real, user-scoped notifications. | `POST /citizen-reports/{id}/moderate` only, via `notify_user()` — notifies the report's `reporter_user_id`. Alert issuance does **not** generate notifications (no per-user targeting mechanism exists for `alerts.audience`, which is free text) — see `docs/ARCHITECTURE.md`'s scope note. |

## Columns

**`roles`**: `id` PK, `name` (unique: ADMIN/ANALYST/OPERATOR/RESEARCHER/CITIZEN), `description`.

**`users`**: `id` PK, `email` (unique, indexed), `hashed_password`, `full_name`,
`role_id` → `roles.id`, `is_active`, `created_at`.

**`locations`**: `id` PK, `name` (unique, indexed), `province`, `latitude`,
`longitude`, `coordinate_confidence`, `evidence_note`, `evidence_source_url`.

**`flood_events`**: `id` PK, `event_id` (unique, indexed), `start_date`, `end_date`
(nullable), `provinces`, `districts`, `rivers`, `impact_note`, `deaths` (nullable),
`source_name`, `source_url`, `confidence_notes`.

**`weather_observations`**: see `docs/DATABASE.md` (unchanged this build).

**`model_versions`**: `id` PK, `version` (unique), `model_type`,
`training_period_start`, `training_period_end`, `metrics_json`, `artifact_path`,
`is_active` (added this build), `registered_at` (added this build).

**`predictions`**: `id` PK, `location_id` → `locations.id`, `model_version_id` →
`model_versions.id`, `predicted_at`, `prediction_probability`, `risk_level`,
`prediction_horizon`, `explanation`.

**`alerts`**: `id` PK, `title`, `risk_level`, `location_id` → `locations.id`,
`message`, `audience`, `channels`, `status` (fixed `"issued"`), `valid_until`
(nullable), `created_at`.

**`citizen_reports`** *(new this build)*: `id` PK, `reporter_user_id` (nullable) →
`users.id`, `location_id` (nullable) → `locations.id`, `description`, `severity`,
`status` (`pending`/`verified`/`rejected`), `submitted_at`,
`reviewed_by_user_id` (nullable) → `users.id`, `reviewed_at` (nullable), `review_note`.

**`data_sources`** *(new this build)*: `id` PK, `name` (unique), `category`,
`base_url`, `description`, `last_checked_at` (nullable), `last_check_status`
(`unknown`/`ok`/`failed`), `last_check_detail`.

**`audit_logs`** *(new this build)*: `id` PK, `user_id` (nullable) → `users.id`,
`action`, `entity_type`, `entity_id` (nullable), `detail`, `created_at`.

**`notifications`** *(new 2026-09-08)*: `id` PK, `user_id` (**not** nullable) →
`users.id`, `notification_type`, `entity_type`, `entity_id` (nullable, polymorphic —
same convention as `audit_logs`), `title`, `message`, `is_read` (default `false`),
`read_at` (nullable), `created_at`.

## Foreign keys / referential integrity

`users.role_id → roles.id`, `alerts.location_id → locations.id`,
`predictions.location_id → locations.id`, `predictions.model_version_id →
model_versions.id`, `citizen_reports.reporter_user_id → users.id` *(nullable)*,
`citizen_reports.location_id → locations.id` *(nullable)*,
`citizen_reports.reviewed_by_user_id → users.id` *(nullable)*,
`audit_logs.user_id → users.id` *(nullable)*, `notifications.user_id → users.id`
*(not nullable — a notification always has a real recipient)*.
All are enforced at the database level (verified in
`backend/tests/database/test_constraints.py` — inserting a row with an unknown
foreign key genuinely raises `IntegrityError`, not just an application-layer check).

## Migrations

Two migrations exist: `51f5e3fbdb3e_baseline_schema_...py` (baseline, generated by
`alembic revision --autogenerate` against an empty `public` schema — the dev database
had no rows worth preserving from the earlier skeleton, see `docs/PROJECT-MEMORY.md`)
and `927a162df6ca_add_notifications_table.py` (2026-09-08, adds `notifications`).
Workflow going forward: change a model →
`alembic revision --autogenerate -m "..."` → review the generated migration →
`alembic upgrade head`. `backend/app/main.py` no longer calls
`Base.metadata.create_all()`; a fresh environment must run `alembic upgrade head`
before starting the server (see `docs/api-inventory.md`'s "Running it locally"
section in `docs/API.md`, still accurate for install steps).

## Not yet implemented

`PredictionExplanation` (SHAP output — no trained model to explain yet), a real
alert-delivery-log table (SMS/email — no provider configured), a `settings`/user-
preferences table. See `docs/backend-architecture.md`, "Not yet built".
