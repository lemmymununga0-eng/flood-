# Deployment

Status as of 2026-10-08. Read **"What deployment means here"** first — it is the part that
matters.

## What deployment means here

This system can be **deployed as a research and demonstration platform**. It must **not**
be deployed as a flood *warning* service.

The software is deployable. The *model* is not decision-grade: across the evaluation in
`docs/MODEL-EVALUATION.md` no model beat a simple seasonal/rainfall baseline consistently
enough to clear the pre-declared selection gates, and the labels rest on 82 high-confidence
flood onsets. Putting a public "flood risk" screen in front of communities on that evidence
would be a harm, not a feature. Every prediction response and the About page already carry
this caveat; a deployment must not remove them.

"100% accuracy" is not a property this system has or can honestly claim. Floods are about
0.1% of district-days, so a model that always answers "no flood" scores 99.9% accuracy while
detecting nothing. Accuracy is deliberately not used as a headline metric anywhere in this
project.

## Stack

```
browser ──► web (nginx :80) ──/api/*──► backend (uvicorn :8000) ──► db (PostgreSQL 16)
              serves built SPA          FastAPI + joblib model        pgdata volume
```

nginx serves the built React bundle and proxies `/api` to the backend, so the browser only
ever talks to one origin. That is the production equivalent of the Vite dev proxy (which
does not exist in a built bundle) and is why no CORS configuration is needed.

| File | Purpose |
|---|---|
| `backend/Dockerfile` | Python 3.14 image, non-root user, healthcheck, runs `alembic upgrade head` then uvicorn |
| `backend/requirements.txt` | **Pinned** to the versions the 57 backend tests passed on |
| `frontend/Dockerfile`, `frontend/nginx.conf` | Multi-stage build, SPA fallback, `/api` proxy, security headers |
| `docker-compose.yml` | db + backend + web; the database port is not published |
| `.env.production.example` | Template; copy to `.env.production` (gitignored) |

## Deploy

```bash
cp .env.production.example .env.production
#   set POSTGRES_PASSWORD and SECRET_KEY (generate: python -c "import secrets; print(secrets.token_urlsafe(48))")
docker compose --env-file .env.production up -d --build
```

The backend runs migrations on start. It **refuses to boot** with `ENVIRONMENT=production`
and the default secret or default database URL (verified, see below), so a forgotten value
fails loudly instead of running insecurely.

Create the first admin deliberately — nothing seeds one in production:

```bash
docker compose exec -e FLOODSHIELD_DEV_ADMIN_PASSWORD='<strong password>' backend python scripts/seed_db.py
docker compose exec backend python scripts/register_model.py
```

Do **not** reuse the development admin password that appears in this project's history.

## Verified vs not verified

| Check | Status |
|---|---|
| Backend test suite | **57/57 passing** |
| ML pipeline tests | **37/37 passing** |
| Frontend tests | **11/11 passing**, production build clean |
| App refuses to boot in production with default secret / default DB URL / both | **verified** (5-case test) |
| App boots in production with real values, and in development | **verified** |
| Migrations apply to an empty PostgreSQL 17 database | **verified** (earlier this project) |
| `.env`, `.env.production`, backups excluded from git; template is not | **verified** |
| **Docker images build and the compose stack starts** | **NOT VERIFIED** — Docker is not installed on the development machine, so the Dockerfiles, nginx config and compose file have never been executed. Expect to fix small things on first build. |
| TLS / HTTPS | **NOT PROVIDED** — terminate TLS at a reverse proxy or load balancer in front of `web` |
| Backups, monitoring, log shipping | **NOT PROVIDED** |
| Scheduled predictions | **NOT PROVIDED** — predictions come from a manual script run |
| In-memory rate limiter | works for one backend process only; needs Redis to scale out |
| Load / performance testing | **NOT DONE** |

## Before pointing real users at it

1. Build and smoke-test the images (`docker compose build`, then hit `/health` and log in).
2. Put TLS in front of it.
3. Rotate every credential that has ever appeared in this repository's history or chat logs.
4. Decide, explicitly, who the audience is. For anything beyond a demo to examiners or
   researchers, this needs forecast meteorology, complete flood labels and validation by the
   relevant authority (DMMU / WARMA) first — see `docs/LIMITATIONS.md`.
