# Deployment Readiness — FloodShield Zambia

Produced 2026-09-07 as part of the full codebase audit. See `docs/AUDIT-REPORT-2026-09-07.md` for
full evidence; this document is the deployment-focused extract required as a standalone deliverable.

## Architecture as it actually exists today

FastAPI backend (single uvicorn process) + PostgreSQL 16 + a Vite-built React SPA, currently only
ever served by the Vite dev server (never a production static host). No reverse proxy, no load
balancer, no container, no orchestrator anywhere in the stack.

## What deployment requires today (manual, verified working this session)

1. A machine with PostgreSQL 16 already installed and running.
2. `.env` created from `.env.example` with real values for: `DATABASE_URL`, `ENVIRONMENT`,
   `SECRET_KEY` (must be a real random value — see P0 finding below), `API_V1_PREFIX`,
   `CORS_ORIGINS`, `NASA_POWER_BASE_URL`, `OPENWEATHER_API_KEY`, `MODEL_ARTIFACT_DIR`,
   `ACTIVE_MODEL_VERSION`.
3. `pip install -r requirements.txt` (backend deps) — **unpinned, see `docs/dependency-audit.md`.**
4. `python3 -m alembic upgrade head` (from `backend/`) — confirmed working this session via a real,
   isolated clean-database rehearsal (created `floodshield_audit_rehearsal`, migrated, seeded, served,
   then dropped — the real dev/test databases were never touched).
5. `python3 scripts/seed_db.py` — real seed data (locations, flood-event CSV, roles, data-source
   catalog); optionally a dev admin via `FLOODSHIELD_DEV_ADMIN_PASSWORD`.
6. `python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000` (no `--reload` in production; no
   process manager currently wraps this — if it crashes, nothing restarts it).
7. `npm install && npm run build` (frontend) — confirmed working this session, produces `dist/`
   (376.58 kB JS / 23.35 kB CSS, gzip 114.96 kB/8.56 kB).
8. Something to actually serve `dist/` — **not currently configured anywhere.** No static file
   server, no CDN config, no reverse-proxy config exists in the repository.

## Environment configuration audit

Per the governing constraint, no secret **values** are reproduced here — only presence/status.

| Variable | Status | Note |
|---|---|---|
| `DATABASE_URL` | PRESENT in both `.env` files (root + `backend/.env`, confirmed identical via checksum) | **MISCONFIGURED risk**: falls back to a hardcoded, weak-credentialed default if `.env` isn't found relative to process CWD (see P0 below) |
| `SECRET_KEY` | PRESENT | **Same fallback risk** — falls back to the literal string `"changeme"` if unset/not found |
| `ENVIRONMENT` | PRESENT | Not verified to gate any fail-fast behavior — the app does not currently refuse to start with default secrets even when `ENVIRONMENT=production` |
| `API_V1_PREFIX` | PRESENT | — |
| `CORS_ORIGINS` | PRESENT | Confirmed non-wildcard, confirmed actually enforced (disallowed-origin preflight returns 400) |
| `NASA_POWER_BASE_URL` | PRESENT | Endpoint unreachable in this sandbox (egress policy) — never observed succeeding |
| `OPENWEATHER_API_KEY` | PRESENT | Not exercised by any currently-live code path this audit found |
| `MODEL_ARTIFACT_DIR` | PRESENT | No artifact exists to point to yet |
| `ACTIVE_MODEL_VERSION` | PRESENT | No model version exists yet |

Both `.env` files are correctly `.gitignore`d (`*.env` at `.gitignore:4`) and were confirmed absent
from git tracking.

## Health checks

`GET /health` exists — pure liveness (`{"status": "ok"}`, no DB check). `GET /api/v1/system-status`
computes real DB connectivity + row counts at request time, but is designed as a dashboard data
endpoint, not a lightweight orchestrator readiness probe. No dedicated `/ready` endpoint exists.

## Limitations that block a real production rollout

- No containerization — cannot deploy to any container-orchestrated platform (Kubernetes, ECS, Cloud
  Run, etc.) without first writing a Dockerfile.
- No CI/CD — no automated build/test gate exists before code reaches any environment; the 42-test
  backend suite and the frontend build/typecheck are run manually today.
- No process supervision — the backend process has no restart-on-crash mechanism.
- No log aggregation beyond local stdout — fine for one process on one machine, not for anything
  scaled or distributed.
- No documented backup/recovery plan for the PostgreSQL database.
- No documented rollback plan for a failed deployment.
- The rate limiter (slowapi, in-memory) will not function correctly across multiple worker processes
  or multiple instances — a horizontally-scaled deployment would need a shared backend (e.g. Redis)
  first.
- The core product feature (flood prediction) does not exist, independent of infrastructure — see
  `docs/missing-features.md`.

## Deployment blockers

See `docs/AUDIT-REPORT-2026-09-07.md` Section 18 for the full categorized P0–P3 list. The items that
are specifically deployment-blocking (as opposed to feature-incompleteness) are:

- **P0**: insecure hardcoded secret/DB-credential fallback must fail-fast instead of silently
  succeeding.
- **P0**: zero deployment automation of any kind exists.
- **P1**: zero pinned dependency versions (reproducibility risk for any automated deploy pipeline).
- **P1**: in-memory rate limiter will not survive horizontal scaling.

## Final deployment status

**NOT READY for staging or production.** A from-empty environment can be stood up successfully by a
human manually following the documented steps (verified live this session via the isolated
clean-database rehearsal) — this proves the *application* is internally consistent and installable,
but there is no automated, reproducible, or supervised path to actually operate it as a real service.
Combined with the P0 security-config finding and the complete absence of the core prediction feature,
this system should be treated as suitable for development/QA environments only until the P0/P1 items
above are resolved and at minimum a container + one CI workflow exist.

---

## Update — 2026-09-08 re-audit

Everything above remains accurate for the web-application layer (backend/frontend) — unchanged.
Full evidence in `docs/AUDIT-REPORT-2026-09-08.md`. Two new deployment considerations from the
now-substantial `ai-engine/` codebase:

- **A separate Python 3.11 environment is required for `ai-engine/`** if XGBoost/TensorFlow(LSTM)/SHAP
  work is ever needed — `ai-engine/requirements.txt` pins TensorFlow to a version incompatible with
  the Python 3.14 interpreter this project otherwise runs on. The backend and ai-engine cannot
  currently share one Python environment for that reason. This is a new item, not present in the
  2026-09-07 deployment picture (which had no ai-engine dependencies to speak of).
- **The frontend's API base URL is hardcoded** (`frontend/src/services/api.ts:20`,
  `http://localhost:8000/api/v1`, no env-var override) — every deployment target requires a full
  frontend rebuild. Previously unflagged; add "introduce a `VITE_API_BASE_URL` env var" to the
  deployment checklist above.

**Also unresolved and now doubly true:** `README.md` remains critically stale and, as of today,
additionally fails to account for the real (if not-yet-trustworthy) ai-engine work that now exists.

**Final deployment status is unchanged: NOT READY for staging or production.** No deployment
automation was added since yesterday; the new ai-engine Python-version-split requirement makes the
eventual deployment story slightly more complex, not less.
