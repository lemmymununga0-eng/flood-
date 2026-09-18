# Dependency Audit — FloodShield Zambia

Produced 2026-09-07. `pip-audit -r requirements.txt` and `npm audit` were **actually run** this
session (not inferred). `pip-audit` was scoped to this project's own `requirements.txt` rather than
the full container environment — the full-environment scan is noisy and includes dozens of unrelated
system/tooling packages not part of this project's real dependency surface, so it was disregarded as
non-representative in favor of the scoped, precise result below.

## Backend (Python) — `requirements.txt`

**Zero versions are pinned anywhere in this file** (`grep -c "==" requirements.txt` → `0`). Every
package floats to whatever version is available at install time.

| Dependency | Version installed (this session) | Purpose | Status | Risk | Action |
|---|---|---|---|---|---|
| fastapi | latest available (unpinned) | Web framework | In use, working | Unpinned = reproducibility risk | Pin |
| uvicorn[standard] | latest available (unpinned) | ASGI server | In use, working | Unpinned | Pin |
| sqlalchemy | latest available (unpinned), 2.x API used | ORM | In use, working | Unpinned | Pin |
| alembic | latest available (unpinned) | Migrations | In use, working | Unpinned | Pin |
| psycopg2-binary | latest available (unpinned) | Postgres driver | In use, working | Unpinned | Pin |
| pydantic / pydantic[email] | latest available (unpinned), v2 API used | Validation/schemas | In use, working | Unpinned | Pin |
| pydantic-settings | latest available (unpinned) | Config loading | In use, working — **also the root cause of the P0 CWD-relative `.env` resolution finding** | Unpinned; behavior footgun independent of version | Pin; also fix the fail-fast behavior in `config.py` (see audit report P0-1) |
| python-jose[cryptography] | latest available (unpinned) | JWT encode/decode | In use, working | Pulls in `ecdsa` transitively (see vulnerability below) | Pin |
| bcrypt | latest available (unpinned), ≥4.1 | Password hashing (used directly, not via passlib) | In use, working | Unpinned | Pin |
| slowapi | latest available (unpinned) | Rate limiting | In use, working (in-memory limitation — see TD-02) | Unpinned | Pin |
| pytest / pytest-asyncio / httpx | latest available (unpinned) | Testing | In use, 42/42 passing | Unpinned | Pin |
| pandas, numpy, scikit-learn, matplotlib, requests, python-dotenv, pyyaml | not verified installed/used | AI-engine starter list | **Unused** — no ML code exists to use them | N/A yet | Revisit once ML work begins |
| **xgboost** | **not installed** — `ModuleNotFoundError` confirmed live | Declared for model training | **Declared, not usable** | N/A — not imported anywhere | Install when ML work actually begins |
| **tensorflow** | **not installed** — `ModuleNotFoundError` confirmed live | Declared for LSTM candidate | **Declared, not usable** | N/A — not imported anywhere | Install when ML work actually begins |
| **shap** | **not installed** — `ModuleNotFoundError` confirmed live | Declared for explainability | **Declared, not usable** | N/A — not imported anywhere | Install when ML work actually begins |

### Vulnerability scan (`pip-audit -r requirements.txt`, actually run)

```
Found 1 known vulnerability in 1 package
Name  Version ID              Fix Versions
----- ------- --------------- ------------
ecdsa 0.19.2  PYSEC-2026-1325
```

`ecdsa` is a **transitive** dependency of `python-jose` (pulled in for ES256/ECDSA-algorithm JWT
support). Confirmed by direct code read: this codebase never imports `ecdsa` directly, and
`backend/app/core/config.py:28` hardcodes `jwt_algorithm = "HS256"`, which does not use `ecdsa` at
all. **Verdict: present in the dependency tree, dormant/unexercised in this application's actual
code paths today.** Still worth tracking/patching — it would become live risk if the JWT algorithm
were ever changed to an ECDSA-based one (ES256/ES384/ES512).

## Frontend (npm) — `frontend/package.json`

Dependencies use semver caret ranges (e.g. `^18.3.1`) — safer than fully unpinned, but not
exact-pinned or lockfile-enforced in CI (no CI exists at all, per the deployment audit).

| Dependency | Declared range | Purpose | Status |
|---|---|---|---|
| react, react-dom | ^18.3.1 | UI framework | In use, working |
| react-router-dom | ^7.18.3 | Routing | In use, working |
| leaflet | ^1.9.4 | Map rendering | In use, working (tile loading BLOCKED by sandbox egress, not a library defect) |
| @types/leaflet, @types/react, @types/react-dom | ^ various | Type definitions | In use |
| @vitejs/plugin-react | ^4.3.1 | Vite React plugin | In use |
| typescript | ^5.5.3 | Type checking | In use — `tsc -b --noEmit` clean, confirmed live |
| vite | ^5.4.0 | Build tool/dev server | In use — `npm run build` succeeds, confirmed live |

### Vulnerability scan (`npm audit`, actually run)

- `npm audit --omit=dev` (production dependency tree only): **0 vulnerabilities.**
- `npm audit` (including dev dependencies): **2 vulnerabilities**, both dev-server-only:
  - `esbuild ≤0.24.2` — moderate (CVSS 5.3) — dev server can be made to forward requests/responses to an arbitrary website (GHSA-67mh-4wv8-2f99).
  - `vite ≤6.4.2` — high (CVSS 7.5) — `server.fs.deny` bypass on Windows alternate paths, path-traversal-adjacent (GHSA-fx2h-pf6j-xcff), plus two additional moderate advisories bundled under the same `vite` finding.
  - **Neither affects the production build output** (`dist/`), which was independently confirmed to build cleanly this session. They matter only if the Vite dev server itself is ever exposed to untrusted network access.

## Summary action list

| Priority | Action |
|---|---|
| P1 | Pin every `requirements.txt` version to the currently-working, tested set (prevents a repeat of the earlier `passlib`/`bcrypt` incident). |
| P1 | Track the `ecdsa` PYSEC-2026-1325 advisory; patch via `python-jose` update when a fixed transitive version is available, even though it's currently dormant. |
| P2 | Upgrade `vite`/`esbuild` dev-tooling once a non-breaking path is available, or accept the dev-only risk explicitly if the dev server is never exposed beyond localhost. |
| P3 | Revisit `pandas`/`numpy`/`scikit-learn`/`matplotlib`/`requests`/`python-dotenv`/`pyyaml` and the not-yet-installed `xgboost`/`tensorflow`/`shap` together, once ML/AI work actually begins — no action needed on them today since nothing imports them. |

---

## Update — 2026-09-08 re-audit

**`ai-engine/requirements.txt` is new** (didn't exist 2026-09-07) — ML/AI work has begun, so the
P3 item above is now partially superseded. Full evidence in `docs/AUDIT-REPORT-2026-09-08.md`.

| Dependency | Declared (ai-engine/requirements.txt) | Installed this session? | Status | Risk | Action |
|---|---|---|---|---|---|
| scikit-learn | pinned | Yes (1.8.0) | In use — actually trained 4 real baseline models | Low | None |
| pandas, numpy, joblib | pinned | Yes | In use, working | Low | None |
| xgboost | pinned, `>=2.0.0` | **No** — `ModuleNotFoundError` confirmed live | Declared, still not usable | N/A — code gates on an `XGBOOST_AVAILABLE` flag | Install once the environment supports it |
| tensorflow | pinned `==2.15.0` | **No** — `ModuleNotFoundError` confirmed live | Declared, **cannot install on the current Python 3.14 interpreter** — requires Python 3.11 per the package's own comment in this requirements file | High — blocks the entire LSTM path, not just "not yet installed" | Provision a separate Python 3.11 environment for `ai-engine/` |
| shap | pinned `>=0.44.0` | **No** — `ModuleNotFoundError` confirmed live | Declared, not usable | N/A — never executed | Install alongside tensorflow once environment is fixed |

**Unlike the root `requirements.txt`, `ai-engine/requirements.txt` IS version-pinned** — good
hygiene, and worth applying back to the root file (see TD-01/P1 above, unchanged).

**Could not be re-verified this session:** `pip-audit` itself is not installed in this sandbox
(`pip show pip-audit` → not found), so the prior `ecdsa 0.19.2` / `PYSEC-2026-1325` finding could
not be re-run. Not assumed fixed or newly broken — just unverified-this-session. `npm audit` was
re-run live and produced identical results to 2026-09-07 (0 vulnerabilities production-only, 2
dev-server-only vulnerabilities including dev deps) — no drift.
