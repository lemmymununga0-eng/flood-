# Technical Debt Register — FloodShield Zambia

Produced 2026-09-07 as part of the full codebase audit. Distinct from `docs/bug-register.md`:
this file tracks structural/maintainability debt rather than functional defects.

| ID | Description | Location | Severity | Impact | Effort | Risk | Recommended Fix | Priority |
|---|---|---|---|---|---|---|---|---|
| TD-01 | Zero pinned dependency versions in `requirements.txt` | `requirements.txt` | High | Already caused a real incident this project (`passlib`/`bcrypt≥4.1` break) | Low (pin current known-good versions) | High — silent breakage on any fresh install | Pin exact versions; add a `pip-audit`/Dependabot-style check going forward | P1 |
| TD-02 | In-memory, per-process rate limiter (slowapi) | `backend/app/core/rate_limit.py` | Medium | Correct today (single process); silently ineffective under any multi-worker/horizontally-scaled deployment | Medium (needs a shared backend, e.g. Redis) | Medium — only manifests once scaled | Move to a shared-state rate-limit backend before scaling beyond one process | P1 |
| TD-03 | No route-based code-splitting on the frontend | `frontend/src/main.tsx` / router setup | Low | 376.58 kB single JS chunk; will grow as more screens are added | Low (`React.lazy` + `Suspense` per route) | Low today, compounding | Introduce lazy-loaded routes | P3 |
| TD-04 | ESLint entirely unconfigured | `frontend/` (absence) | Medium | No automated style/correctness linting is possible | Low (standard React+TS ESLint config) | Medium — real bugs a linter would catch go unnoticed | Add ESLint config + `lint` script, wire into CI once CI exists | P2 |
| TD-05 | No Python static analysis/linting configured | `backend/` (absence) | Medium | Same class of gap as TD-04 for the backend | Low (`ruff` is fast to add) | Medium | Add `ruff` (or `flake8`) + a `make lint`/CI step | P2 |
| TD-06 | Dead scaffold directories (`database/schema/`, `database/migrations/`, `infrastructure/`) contain only `.gitkeep` | repo root | Low | Misleading to a new contributor — implies structure that isn't actually used (real migrations live in `backend/alembic/`) | Trivial | Low | Remove or clearly mark as unused/reserved in a README note | P3 |
| TD-07 | No frontend automated test suite committed to the repository | `frontend/` (absence) | High | Every "verified" frontend claim across this project's history is a manual, point-in-time Playwright run — nothing prevents silent regressions | Medium-High (would need real test infrastructure + maintained specs) | High — regression risk grows with every future change | Commit a maintained Playwright (or equivalent) suite under `frontend/tests/e2e/`, wire into CI once CI exists | P2 |
| TD-08 | No indexes beyond primary/unique keys anywhere in the schema | `backend/alembic/versions/` | Low today | Untested at scale — dev dataset (3 locations, 11 events) gives no signal either way | Low once query patterns are known | Low today, unknown at scale | Review real query patterns before/during first real-traffic deployment and add indexes as needed | P3 |
| TD-09 | Two different error-response shapes depending on whether an error originates in routing or in a business-logic handler | `backend/app/main.py` | Medium | Frontend/API consumers must special-case both shapes | Low | Medium | Register a `StarletteHTTPException` handler to normalize routing-layer errors too | P2 |
| TD-10 | `frontend/package.json` version string still reads `0.1.0-skeleton` | `frontend/package.json` | Trivial | Cosmetic — understates how much has actually been built | Trivial | None | Bump when convenient; not urgent | P3 |
| TD-11 | Historical master prompts not preserved verbatim in `prompts/` (only the first of four exists there; the rest are summarized in `docs/PROJECT-MEMORY.md`) | `prompts/` | Low | Project provenance/history is summarized, not archived verbatim | Low | Low | Save the remaining prompt texts to `prompts/` if full historical fidelity matters | P3 |

No debt item above blocks development-testing use of the application today; several (TD-01, TD-02,
TD-07) materially block a safe production deployment and are cross-referenced in
`docs/AUDIT-REPORT-2026-09-07.md`'s P0/P1 blocker list.

---

## Update — 2026-09-08 re-audit

TD-01 through TD-11 above re-checked, all still accurate and unchanged. New debt found in the
now-substantial `ai-engine/` codebase, full evidence in `docs/AUDIT-REPORT-2026-09-08.md`:

| ID | Description | Location | Severity | Impact | Effort | Risk | Recommended Fix | Priority |
|---|---|---|---|---|---|---|---|---|
| TD-12 | `ai-engine` ML dependencies (`tensorflow`, and transitively the LSTM path) require Python 3.11; the project's actual interpreter is 3.14 | `ai-engine/requirements.txt` | High | LSTM and (if it follows suit) SHAP work cannot proceed in the current environment at all | Medium (provision a separate 3.11 venv, or find a TF-free path) | High — silently blocks 2 of 5 planned model types | Stand up a dedicated Python 3.11 environment for `ai-engine/` before resuming LSTM/SHAP work | P1 |
| TD-13 | `ExperimentTracker.save_artifact()` exists but is never called — every `experiments/run_00X/artifacts/` folder is always empty | `ai-engine/src/utils/experiment_tracker.py:102-113`; callers in `ai-engine/src/training/` | Medium | "Artifacts" folders are misleading — they contain nothing; no plots/model copies are actually tracked per-run | Low | Low today, misleading later | Call `save_artifact()` from `train_baselines.py`/`train_lstm.py` for the model file + key plots per run | P2 |
| TD-14 | Audit companion docs (this set) went stale on their ML/AI sections within 24 hours of being written, because a large amount of `ai-engine/` code landed the same day | `docs/*.md` (the 9 companion docs from 2026-09-07) | Medium | Process risk: a fast-moving project can outpace its own audit snapshot quickly | Low (delta-patch, as done here) | Medium — a stale doc read in isolation misleads exactly like a stale README | Regenerate or delta-patch audit docs whenever a major subsystem changes, not only on a fixed schedule | P2 |
| TD-15 | Unused scaffolding in `ai-engine/`: `models/` (distinct from `saved_models/`), `data/interim/`, `data/features/` are all empty and never referenced by any code path | `ai-engine/models/`, `ai-engine/data/interim/`, `ai-engine/data/features/` | Low | Same class of noise as TD-06 (dead scaffold dirs) | Trivial | Low | Remove or clearly mark as reserved-for-future-use | P3 |

No debt item above blocks development-testing use of the ai-engine pipeline today (it runs
end-to-end and its own 26 tests pass); TD-12 blocks two specific model types and all
explainability work, and is the most consequential new item.

---

## Update — Phase 3: ai-engine data-pipeline bug fixes (2026-09-08)

Two silent-failure traps in `ai-engine/src/ingestion/flood_events_ingestor.py` were fixed and are
now covered by regression tests (`ai-engine/tests/test_flood_events_ingestor.py`) — full detail
in `docs/bug-register.md` BUG-14/BUG-15. Both are resolved, not just documented:

| ID | Description | Location | Severity | Impact | Effort | Risk | Status |
|---|---|---|---|---|---|---|---|
| TD-16 | Broad `except Exception` in `FloodEventsIngestor.load()` silently converts any CSV parse failure into a quiet fallback to proxy labels, with only a log line and no failure signal visible to a normal pipeline run | `flood_events_ingestor.py:120-122` | Medium | A future malformed data file would silently degrade to proxy labels again with no loud failure | Low (already improved by fixing the one bad row; the broad catch itself remains) | Medium — this exact failure mode already happened once | Resolved for the current data (BUG-14); the broad except-clause pattern itself is still there and would benefit from re-raising or loudly counting parse failures in a future pass | Open (lower severity now that the current file parses cleanly) |
| TD-17 | `events_to_daily_labels()` had no null-check on `event_end`, silently zeroing out any event missing an end date | `flood_events_ingestor.py:154-159` | High (was silently dropping 9/11 real events) | Understated real flood-event coverage with no error | Low (one-line null-check + fallback, already added) | Was high, now mitigated | **Resolved** |

No new debt item blocks the ai-engine pipeline's current tests (30/30 passing after these fixes).
The train-split-has-zero-real-positives finding (`docs/bug-register.md` BUG-16) is tracked there
as a data/methodology blocker, not technical debt — no code change can resolve it.
