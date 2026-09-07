# Frontend ↔ Backend Integration Matrix

Phase 0 audit deliverable for the "Complete Backend Implementation & End-to-End
Integration" master prompt (2026-09-07). This is the required inspection step before
new backend code was written: every frontend screen, what data it needs, what the
backend currently provides, and the gap. Read this alongside `docs/API.md` (current
endpoint list) and `docs/DATABASE.md` (current schema).

Legend: **OK** = real endpoint exists and is wired up. **STUB** = screen renders an
honest empty/placeholder state because no backend support exists yet. **NEW** = this
build adds it. **GAP** = identified but intentionally deferred (recorded, not silently
dropped).

| Screen (`frontend/src/pages/`) | Data needed | Current backend | Status this build |
|---|---|---|---|
| `Landing.tsx` | none (marketing copy) | n/a | OK |
| `Login.tsx` | authenticate user, get token | none — "Continue to dashboard" skips auth entirely | **NEW**: `POST /api/v1/auth/login` |
| `About.tsx` | none (static) | n/a | OK |
| `Dashboard.tsx` | locations, flood-events, alerts, predictions, system-status | all real (GET) | OK, unchanged |
| `RiskMap.tsx` | locations (markers) | `GET /locations` | OK, unchanged. No risk-color overlay — no predictions exist yet (correct, not a bug) |
| `LocationDetail.tsx` | one location, weather observations, ingest action | `GET /locations`, `GET/POST /weather/{id}` | OK, unchanged |
| `Predictions.tsx` | predictions list | `GET /predictions` (real, empty) | OK, unchanged — legitimately empty, no model trained |
| `Analytics.tsx` | aggregate stats/trends | none | STUB, stays STUB — computing analytics over an empty predictions table would mean fabricating trend lines. **GAP**, documented, not built this round. |
| `HistoricalEvents.tsx` / `HistoricalEventDetail.tsx` | flood_events | `GET /flood-events` | OK, unchanged |
| `Alerts.tsx` / `CreateAlert.tsx` | alerts list/create | `GET/POST /alerts` | OK, unchanged. **NEW**: creation now requires an authenticated ANALYST/OPERATOR/ADMIN user (RBAC) |
| `CitizenReports.tsx` | citizen reports list/submit | none | **NEW**: `GET/POST /citizen-reports`, moderation fields |
| `AIModel.tsx` | model registry entries, metrics | `model_versions` table exists, no endpoint | **NEW**: `GET /models`, `GET /models/{id}` |
| `DataSources.tsx` | data source catalog + health | none | **NEW**: `GET /data-sources` (real catalog: NASA POWER, CHIRPS, DMMU/WARMA, flood-event log — each row's `last_checked_status` reflects a real check, not an assumption) |
| `SystemStatus.tsx` | component health | `GET /system-status` | OK, unchanged |
| `Notifications.tsx` | notification feed | none | STUB, stays STUB — no notification-generating event exists yet (no new predictions, no automated alert triggers). **GAP**, documented. |
| `Settings.tsx` | user preferences | none | STUB this round — needs a real authenticated user first. **GAP**, follow-up once auth is in daily use. |
| `Profile.tsx` | current user | none | **NEW**: `GET /auth/me` |
| `NotFound.tsx` | none | n/a | OK |

## New backend capabilities this build adds (not screen-driven)

- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me` — real
  JWT auth, bcrypt password hashing, roles (ADMIN/ANALYST/OPERATOR/RESEARCHER/CITIZEN).
- RBAC enforcement on write endpoints (`POST /alerts`, `POST /citizen-reports` moderation
  actions, `POST /data-sources` checks) — read endpoints stay public, matching the
  dashboard's current public-read design; nothing that previously worked without login
  now requires it, except alert creation (previously anonymous, now requires a role,
  since an unauthenticated public dashboard should not be able to issue flood alerts to
  a citizen audience — recorded as a deliberate behavior change in
  `docs/PROJECT-MEMORY.md`).
- `audit_logs` table + write-path hooks on auth and alert-creation events (not a UI
  screen yet — audit trail is for operators/admins, not the dashboard).
- Alembic migrations replacing `Base.metadata.create_all()`.

## Explicitly out of scope this round (recorded, not silently dropped)

SHAP-based prediction explanations (no trained model exists — building an explanation
endpoint against a nonexistent model would mean fabricating explanations), full alert
delivery (SMS/email/USSD — no provider configured, same as before), Analytics and
Notifications real implementations (both depend on data that doesn't exist yet —
predictions and event triggers respectively), a dedicated Settings backend, rate
limiting beyond auth endpoints, and full RBAC on every single endpoint (applied first to
the highest-risk write paths: auth, alert issuance, citizen-report moderation).
