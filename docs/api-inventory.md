# API Inventory — FloodShield Zambia

Every endpoint that exists in the running backend as of this build, grouped by
router. Auth column: **public** (no token required), **auth** (any valid, active
user), or a role list (enforced by `require_roles(...)`). Live reference: FastAPI's
auto-generated OpenAPI docs at `/docs` on the running backend. Error responses across
every endpoint share one shape: `{"error": <machine code>, "message": <human text>}`
(422s add a `"fields"` array).

| Method | Path | Auth | Behavior |
|---|---|---|---|
| GET | `/health` | public | Liveness check. |
| POST | `/api/v1/auth/register` | public (rate-limited: 5/min/IP) | Creates a real user, always role CITIZEN. Returns access+refresh tokens. |
| POST | `/api/v1/auth/login` | public (rate-limited: 10/min/IP) | Verifies bcrypt hash, returns access+refresh tokens. |
| GET | `/api/v1/auth/me` | auth | Returns the authenticated user's real profile. |
| GET | `/api/v1/locations` | public | Real seeded locations. Query: `province`, `limit`, `offset`. |
| GET | `/api/v1/flood-events` | public | The 11 real, sourced historical events. Query: `province`, `sort` (`start_date`\|`deaths`), `limit`, `offset`. |
| GET | `/api/v1/weather/{location_id}` | public | Stored weather observations (empty until a real ingestion succeeds). |
| POST | `/api/v1/weather/{location_id}/ingest` | public | Real NASA POWER HTTP request; honest success/failure — see `docs/DATA-SOURCES.md`. |
| GET | `/api/v1/predictions` | public | Real predictions only — legitimately `[]` (no trained model). |
| GET | `/api/v1/alerts` | public | Real persisted alerts. Query: `risk_level`, `location_id`, `limit`, `offset`. |
| POST | `/api/v1/alerts` | **ADMIN, ANALYST, OPERATOR** | Creates a real alert; audit-logged (`alert_issued`). |
| GET | `/api/v1/citizen-reports` | public | Real citizen reports. Query: `status`, `limit`, `offset`. |
| POST | `/api/v1/citizen-reports` | auth | Submits a real report tied to the authenticated user. |
| POST | `/api/v1/citizen-reports/{id}/moderate` | **ADMIN, ANALYST, OPERATOR** | Sets `status` (verified/rejected) + `review_note`; audit-logged. |
| GET | `/api/v1/models` | public | Model registry (`model_versions` table) — legitimately `[]`, no model trained. |
| GET | `/api/v1/models/{id}` | public | One model version; 404 if it doesn't exist. |
| GET | `/api/v1/data-sources` | public | The real data-source catalog (NASA POWER, DMMU, WARMA, the flood-event log), with the status of the last real connectivity check. |
| POST | `/api/v1/data-sources/{id}/check` | **ADMIN, ANALYST, OPERATOR** | Runs a real HTTP check against that source right now and updates its stored status. |
| GET | `/api/v1/system-status` | public | Computed at request time — DB ping, real row counts. Never hardcoded. |

## Auth error codes

| HTTP | `error` | When |
|---|---|---|
| 401 | `not_authenticated` | No bearer token supplied. |
| 401 | `invalid_token` | Token malformed, expired, or wrong type (e.g. a refresh token used where an access token is required). |
| 401 | `invalid_user` | Token's subject doesn't resolve to an active user. |
| 401 | `invalid_credentials` | Login with a wrong password or unknown email. |
| 403 | `account_disabled` | Login attempt for a deactivated account. |
| 403 | `forbidden` | Authenticated but the user's role isn't in the endpoint's allow-list. |
| 409 | `email_taken` | Registration with an email that already exists. |
| 429 | `rate_limited` | Too many requests to a rate-limited endpoint. |

## Not yet implemented as an endpoint

`POST /api/v1/auth/refresh` (tokens are issued, nothing exchanges them yet), any
admin endpoint to change a user's role, `/analytics/*` (no real aggregate data to
serve yet), `/notifications/*` (no event source generates them yet), SHAP explanation
endpoints (no trained model), alert-delivery status for external channels (no
provider configured). See `docs/backend-architecture.md`, "Not yet built".
