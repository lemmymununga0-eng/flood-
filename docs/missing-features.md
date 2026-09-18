# Missing Features — FloodShield Zambia

Produced 2026-09-07 as part of the full codebase audit. Features confirmed absent by direct
search/code-read this session — not inferred from documentation. Grouped by area; see
`docs/AUDIT-REPORT-2026-09-07.md` for full evidence per item.

> **⚠ UPDATE 2026-09-08: the ML/AI section below is now stale and materially wrong.** A full
> `ai-engine/` codebase landed after this doc was written — data cleaning, feature engineering,
> chronological splitting, and 4 trained scikit-learn baseline models all now exist and run. See
> `docs/AUDIT-REPORT-2026-09-08.md` Section 5 for the current, accurate picture. The list below is
> kept for historical record; the corrected list follows immediately after it.

## ML/AI (the largest gap — see audit Section 8) — HISTORICAL, SEE UPDATE ABOVE

- Data cleaning/preprocessing pipeline — no code exists.
- Feature engineering — no code exists.
- XGBoost model training — `xgboost` not installed, not imported anywhere.
- LSTM/time-series model training — `tensorflow` not installed, not imported anywhere.
- Model evaluation/metrics computation — no metrics exist anywhere in the repo or database.
- SHAP explainability — `shap` not installed; zero implementation found.
- Model packaging/artifact registry — `model_versions` table is real but has 0 rows; no artifact file exists anywhere.
- Negative-class (non-flood-period) construction for the 11-event flood log — not built; the label methodology decision itself (event-log-based vs. rainfall-accumulation proxy) is still open per `docs/ML-METHODOLOGY.md`.

## ML/AI — CORRECTED as of 2026-09-08 (still missing/broken today)

- **XGBoost model training** — real code exists (`ai-engine/src/models/baselines.py`) but `xgboost` is still not installed; never actually trained.
- **LSTM/time-series model training** — a real, complete Keras architecture exists (`ai-engine/src/models/lstm.py`) but `tensorflow` is not installed and cannot be installed on the project's current Python 3.14 interpreter (TensorFlow requires 3.11 per `ai-engine/requirements.txt`). A separate Python 3.11 environment must be provisioned first.
- **SHAP explainability** — a real, complete implementation exists (`ai-engine/src/explainability/explain_models.py`) but `shap` is not installed; never actually executed; zero SHAP output files exist.
- **Real-data training** — **Update 2026-09-09: this is now done.** Three pre-2020 events were
  researched and added (14 events total), giving the training split real positive examples for
  the first time (BUG-16 resolved). Separately, NASA POWER was confirmed reachable from the real
  developer machine (it was never actually blocked by anything in this project's code — only by
  sandboxed cloud sessions used in earlier audits), so `main.py` was run for real: real NASA POWER
  weather data (Lusaka, 2000-2023) combined with real, independent flood-event labels, no
  synthetic data, no leaky proxy formula. Real (modest but genuine) results are in
  `docs/ML-METHODOLOGY.md`'s 2026-09-09 update. Remaining real gaps from this run: single-point
  (not multi-province) weather coverage, a national- rather than location-level label, and
  unhandled class imbalance (`docs/bug-register.md` BUG-17/18/19) — genuine follow-up work, not
  fabrication or leakage.
- **A valid, non-leaky label methodology** — the current proxy labels are a deterministic function of the same rolling-rainfall features used as model inputs (see BUG-13). This must be redesigned before any reported metric can be trusted.
- **Model packaging/artifact registry (DB-level)** — `model_versions` table is still real-schema-only with 0 rows; the 4 trained models exist only as `.joblib` files on disk, never registered into the running application's database.
- **Per-run artifact tracking** — `ExperimentTracker.save_artifact()` exists but is dead code; `experiments/run_00X/artifacts/` folders are always empty (see `docs/technical-debt.md` TD-13).
- **Negative-class construction from the real event log** — still not built, and now additionally blocked by the fact the real event log itself isn't loading (BUG-12).

## ML/AI — now genuinely present as of 2026-09-08 (remove from any future "missing" list)

- Data cleaning/validation pipeline (`ai-engine/src/preprocessing/`) — real, executed.
- Feature engineering (`ai-engine/src/features/build_features.py`) — real, executed (though see the leakage caveat above).
- Chronological train/val/test splitting (`ai-engine/src/datasets/split_data.py`) — real, correct methodology.
- Baseline model training (LogisticRegression, DecisionTree, RandomForest, GradientBoosting) — real, executed, 4 real `.joblib` artifacts on disk.
- Model evaluation/metrics computation (`ai-engine/src/evaluation/metrics.py`) — real, computed from real predictions (caveat: on leaky/synthetic data, per above).
- A 26-test automated unit-test suite for the ai-engine codebase — real, passing (`python -m pytest ai-engine/tests`).

## Backend/API

- `POST /auth/refresh` — refresh tokens are issued (7-day expiry) but nothing consumes them.
- Admin endpoint to change a user's role — requires a direct database script today.
- Alert delivery to any external channel (SMS/email) — `channels` is stored as metadata only; no provider is integrated.
- A shared/multi-process rate-limit backend — current limiter is in-memory, per-process only.
- File/image upload support for citizen reports — no `UploadFile`/multipart endpoint exists anywhere, despite being discussed as a design intent in `docs/LIMITATIONS.md`/`docs/SECURITY.md`.
- `/analytics/*` real aggregate endpoints — no real aggregate data source exists yet; the Analytics screen is an honest stub.
- `/notifications/*` — **narrowed 2026-09-08**: `GET /notifications` and `POST /notifications/{id}/read` now exist and are real (citizen-report moderation notifies the reporter). Still missing: notifications for issued alerts, new predictions, or data-source sync — none of those events has a real per-user recipient to target (`alerts.audience` is free text, not a set of user ids), so building those would mean inventing a targeting mechanism, not closing this gap.
- A dedicated lightweight readiness probe distinct from `/health`'s pure liveness check.

## Frontend

- Standalone How-It-Works/Methodology pages (currently folded into About).
- Prediction Detail and Citizen Report Detail single-item views (list views exist; detail views do not).
- Data Quality screen.
- React error boundary (any unhandled render exception currently produces a blank page).
- Dark/light theme toggle (current build is dark-only by design).
- Route-based code-splitting (entire app ships as one JS bundle).
- Automated frontend test suite (no test framework installed, no `test` script).

## Database

- `PredictionExplanation`/SHAP-output storage — no trained model exists to explain yet.
- A real alert-delivery-log table (tracking SMS/email delivery attempts) — no provider configured.
- A `settings`/user-preferences table.
- Documented backup/recovery plan.

## Deployment/DevOps

- Dockerfile / docker-compose configuration — none exist anywhere in the repository.
- CI/CD pipeline — no `.github/workflows/`, no equivalent on any other platform.
- Infrastructure-as-code — `infrastructure/` directory contains only a `.gitkeep`.
- Process supervision (systemd units, supervisord, or equivalent) for the backend/frontend processes.
- A documented rollback plan.
- Anything serving the built frontend (`npm run build` output) in a production-like way — currently only the Vite dev server has ever been used.

## Testing/QA

- Automated frontend tests of any kind.
- Automated test coverage for `GET /api/v1/weather/{location_id}`, `POST /api/v1/weather/{id}/ingest`, and `POST /api/v1/data-sources/{id}/check`.
- ESLint configuration (frontend) and any Python static-analysis tool (backend) — neither exists, so linting cannot currently be run at all, not merely "not run."
- A committed, CI-running Playwright (or equivalent) end-to-end suite — all E2E verification to date has been manual, ad hoc, and run from the session scratchpad, never committed to the repository.

None of the above are classified as MOCKED or FABRICATED — every one is a genuine absence (confirmed
by search/code-read), not a fake stand-in presented as real. This distinction matters per the audit's
explicit mandate to determine whether the app fabricates results: it does not; it is simply incomplete
in the areas listed above.
