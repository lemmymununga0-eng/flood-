# FloodShield Zambia — ML Model & Prediction Integration Audit

> **HISTORICAL RECORD — superseded.** This document was accurate when written and has
> deliberately **not** been edited, so the project's audit trail stays honest. It does not
> describe the system as it stands now: a model is trained and served, 82 districts of
> weather data are ingested, and the corrected study's verdict is `DO_NOT_DEPLOY`.
> For the current state see **`docs/CURRENT-STATE-2026-10-01.md`**.

**Audit date:** 2026-09-09
**Scope:** inspection and analysis only, per the governing prompt's explicit rule — no files were
edited, created, or deleted as part of this audit. Every claim below is backed by a file actually
read, a command actually run (model load test, exact sample-count computation), or a live curl
probe against the running backend — not inferred from filenames or prior conversation memory.

**Disclosure required by this audit's own "no fabrication" rule, applied to itself:** computing
the exact positive/negative sample counts in Section 7 required calling the real
`DataCleaner.clean()` method, which — as a side effect of its own normal operation, not something
this audit added — re-saved `ai-engine/data/processed/cleaned_weather.csv`. That path is
git-ignored (`ai-engine/data/processed/*` in `.gitignore`) and is a disposable, fully
deterministic, regenerable intermediate file, not source code, config, or a tracked project file —
confirmed via `git status`/`git check-ignore` showing zero effect on the repository's tracked
state. No other command run during this audit wrote anything. Flagged here rather than omitted,
per this project's own transparency standard.

---

## 1-2. What Actually Exists, and What Model Actually Produced the Latest Real Result

**Four models were actually trained** on real data in the most recent run (`ai-engine/experiments/run_005`
through `run_008`, all timestamped 2026-09-08 22:5x-23:00 UTC): **Logistic Regression, Decision
Tree, Random Forest, Gradient Boosting** — read directly from each run's `config.json`
(`model_name` field) and cross-checked against `ai-engine/saved_models/*.joblib`, which contains
exactly these four files plus a `scaler.joblib`.

**XGBoost was not trained** — confirmed `xgboost` is not installed in this interpreter (`python -c
"import xgboost"` → `ModuleNotFoundError`), and the code that would train it
(`ai-engine/src/models/baselines.py`) gates it behind an `XGBOOST_AVAILABLE` flag that is `False`
here. **LSTM was not trained** — `tensorflow` is not installed either, and `main.py`'s own log
message states it requires Python 3.11 (this interpreter is 3.14). Neither absence is assumed;
both were verified by direct import attempt.

**Which model should be the production candidate, based on actual results, not assumption:**
**Logistic Regression** — by a wide margin, on every metric that matters for a rare-event problem
like this one. Read directly from `ai-engine/reports/baseline_comparison.csv`:

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| **LogisticRegression** | 0.9168 | 0.2037 | **0.4889** | 0.2876 | **0.8502** | 0.1323 | 0.0693 |
| DecisionTree | 0.9031 | 0.0816 | 0.1778 | 0.1119 | 0.5528 | 0.0428 | 0.0820 |
| RandomForest | 0.9519 | 0.0500 | 0.0222 | 0.0308 | 0.7898 | 0.0725 | 0.0580 |
| GradientBoosting | 0.9656 | 0.0000 | 0.0000 | 0.0000 | 0.5813 | 0.0390 | 0.0347 |

**Important, previously-unflagged finding:** `main.py:264` hardcodes `randomforest_model.joblib` as
"the best saved model" for SHAP explainability, unconditionally — there is no code anywhere that
actually compares the four models' metrics and selects a winner. Random Forest is, by these real
numbers, one of the two worst models (recall 0.022 — it essentially never predicts a flood).
**GradientBoosting has zero precision and zero recall** — it predicts the negative class 100% of
the time and still scores 96.6% "accuracy," which is exactly the class-imbalance trap this kind of
rare-event problem is known for, and exactly why accuracy alone is a misleading metric here (this
project's own `docs/ML-METHODOLOGY.md` already says to weight recall heavily — the actual results
now demonstrate why). **Confusion matrix, calibration curve, and PR curve plots: NOT AVAILABLE as
saved artifacts** — `SHAPExplainer`/`EDAPlotter` code exists to produce plots, but SHAP never ran
(Section 15) and no confusion-matrix image file was found in `ai-engine/reports/figures/`.

**Sample counts** (computed directly this session, not estimated — see disclosure above):
298 total NASA POWER rows... precisely: **8,766 total daily rows (2000-01-01 to 2023-12-31),
295 positive (flood) days overall (3.37%)**. Split chronologically 70/15/15:

| Split | n | Positive | Positive rate | Date range |
|---|---:|---:|---:|---|
| Train | 6,138 | 243 | 3.96% | 2000-01-01 → 2016-10-20 |
| Validation | 1,314 | 7 | 0.53% | 2016-10-21 → 2020-05-26 |
| Test | 1,314 | 45 | 3.42% | 2020-05-27 → 2023-12-31 |

This is a real, meaningful improvement over the state audited on 2026-09-08 (train had **zero**
positives before three pre-2020 events were researched and added) — training now has 243 real
positive examples — but validation still has only 7, which is thin for reliable hyperparameter
selection, and this project's own class-imbalance handling (Section 19) is not yet implemented,
which is the most likely explanation for GradientBoosting/RandomForest's collapse above.

---

## 3. The Actual Model Artifacts

| Model file | Path | Type | Size | Modified | Framework |
|---|---|---|---:|---|---|
| `logisticregression_model.joblib` | `ai-engine/saved_models/` | joblib (pickle) | 1,247 B | 2026-09-09 00:59 | scikit-learn 1.8.0 |
| `decisiontree_model.joblib` | same | joblib | 3,801 B | 2026-09-09 00:59 | scikit-learn 1.8.0 |
| `randomforest_model.joblib` | same | joblib | 768,985 B | 2026-09-09 00:59 | scikit-learn 1.8.0 |
| `gradientboosting_model.joblib` | same | joblib | 737,961 B | 2026-09-09 01:00 | scikit-learn 1.8.0 |
| `scaler.joblib` (RobustScaler, required preprocessing object) | same | joblib | 2,503 B | 2026-09-08 00:58 | scikit-learn 1.8.0 |
| `feature_columns.json` / `model_metadata.json` | same | JSON | 1,104 B / 1,399 B | 2026-09-09 00:58-01:00 | — |

All five `.joblib` files use scikit-learn's standard `joblib.dump()` serialization (Python pickle
under the hood) — none use a model-native format (irrelevant here since no XGBoost/LSTM model
exists to have one). **Python version used to train:** 3.14.0 (this machine's only interpreter —
confirmed no venv exists anywhere in the repo). **Library version used to train:** scikit-learn
1.8.0, joblib 1.5.3, pandas 3.0.3, numpy 2.4.4 — all confirmed via direct `import`/`__version__`
this session.

---

## 4. Model Load Test — Actually Performed, Read-Only

```
MODEL LOAD TEST: PASS (all five files)

logisticregression_model.joblib -> LOAD OK -> sklearn.linear_model._logistic.LogisticRegression
decisiontree_model.joblib       -> LOAD OK -> sklearn.tree._classes.DecisionTreeClassifier
randomforest_model.joblib       -> LOAD OK -> sklearn.ensemble._forest.RandomForestClassifier
gradientboosting_model.joblib   -> LOAD OK -> sklearn.ensemble._gb.GradientBoostingClassifier
scaler.joblib                   -> LOAD OK -> sklearn.preprocessing._data.RobustScaler
```

Run via `joblib.load(...)` on each file from the same Python 3.14 / scikit-learn 1.8.0 environment
they were trained in — no version-mismatch risk exists today because it's the same interpreter.
**Critically important, verified finding for integration planning:** the **backend's own Python
environment already has `joblib` and `scikit-learn` importable** (`cd backend && python -c "import
joblib, sklearn"` → succeeds, same 1.8.0). This is because backend and ai-engine currently share
one global Python interpreter on this machine (no separate venvs exist for either). **This means
the four trained baseline models could be loaded directly inside a FastAPI backend process today,
with no new dependency installation, no Python-version migration, and no venv work** — the
Python-3.11-for-TensorFlow constraint (Section 18) blocks XGBoost/LSTM/SHAP specifically, not the
scikit-learn baselines that already exist and already work.

Required preprocessing objects for a correct load-and-predict path: the `RobustScaler`
(`scaler.joblib`) must be applied to raw features before calling `.predict_proba()` — confirmed by
reading `build_features.py`'s `scale_features()`, which fits/saves this exact scaler during
training. Feature ordering must exactly match `feature_columns.json`'s 54-entry list (Section 5) —
scikit-learn estimators do not validate column names, only column count and order, so mismatched
ordering would silently produce wrong predictions rather than an error.

---

## 5. Exact Input Features (54, verified from `feature_columns.json`, not inferred)

| # | Feature | Type | Source | Transformation |
|---|---|---|---|---|
| 1 | `prectotcorr` | float, mm/day | NASA POWER | raw |
| 2 | `t2m` | float, °C | NASA POWER | raw |
| 3 | `t2m_max` | float, °C | NASA POWER | raw |
| 4 | `t2m_min` | float, °C | NASA POWER | raw |
| 5 | `rh2m` | float, % | NASA POWER | raw |
| 6 | `ws2m` | float, m/s | NASA POWER | raw |
| 7 | `allsky_sfc_sw_dwn` | float, MJ/m²/day | NASA POWER | raw |
| 8 | `gwetroot` | float, fraction 0-1 | NASA POWER | raw |
| 9 | `gwetprof` | float, fraction 0-1 | NASA POWER | raw |
| 10-13 | `rain_rolling_{sum,mean,max}_3d`, `rh_rolling_mean_3d` | float | derived | 3-day rolling window, `min_periods=1` |
| 14-17 | same, `_7d` | float | derived | 7-day rolling |
| 18-21 | same, `_14d` | float | derived | 14-day rolling |
| 22-25 | same, `_30d` | float | derived | 30-day rolling |
| 26-30 | `prectotcorr_lag{1,2,3,7,14}d` | float | derived | `.shift(n)`, backward-looking only |
| 31-35 | `t2m_lag{1,2,3,7,14}d` | float | derived | same |
| 36-40 | `rh2m_lag{1,2,3,7,14}d` | float | derived | same |
| 41-45 | `gwetroot_lag{1,2,3,7,14}d` | float | derived | same |
| 46 | `month` | float 1-12 | calendar | `.index.month` |
| 47 | `day_of_year` | float 1-366 | calendar | `.index.day_of_year` |
| 48 | `year` | float | calendar | `.index.year` |
| 49-50 | `month_sin`/`month_cos` | float -1..1 | derived | cyclical encoding |
| 51-52 | `doy_sin`/`doy_cos` | float -1..1 | derived | cyclical encoding |
| 53 | `is_rainy_season` | float 0/1 | derived | 1 if month≥11 or ≤4 |
| 54 | `soil_saturation_index` | float | derived | `0.6·gwetroot + 0.4·gwetprof` |

All 54 (in this exact order) are required — scikit-learn matches by position/count. Missing-value
handling: `DataCleaner` fills gaps before feature engineering (verified 0 missing values in this
run's log); rows with `NaN` from the lag/rolling windows' warm-up period are dropped
(`build_features.py:138`). Scaling: `RobustScaler`, fit on the training split only (verified —
`scale_features(fit=True)` is called once on the full pre-split `df_features`, then the *fitted*
scaler is reused; this is fit-before-split, a technically-imperfect-but-common practice worth
flagging — see Section 6).

---

## 6. Data Leakage Check

```
Leakage status: WARNING (one real, minor issue found; the labels themselves are clean)
```

**Label independence — PASS.** The real label (`events_to_daily_labels()`, from the actual,
independently-researched flood-event log) does not derive from any of the 54 model input features
— confirmed by reading both functions side by side. This is a genuine improvement over the
2026-09-08 finding, where the *proxy* label was a direct function of `rain_rolling_sum_3d`/`_7d`/
`soil_saturation_index` (three of the 54 features) — that leakage is real, but it does **not**
apply to this run, because `main.py:171-174` confirmed real labels were used this time
(`has_real_labels = True`), which skips `_add_proxy_labels()` entirely (`build_features.py:133`).
If this project ever falls back to proxy labels again (e.g. if the events CSV goes missing), the
same BUG-13 leakage would return — it is dormant, not fixed, and this audit does not claim
otherwise.

**Temporal split — PASS.** Strictly chronological, no shuffling, confirmed by reading
`DataSplitter.split()`: `X[:n_train]`, `X[n_train:n_train+n_val]`, `X[n_train+n_val:]` — a
positional slice on a pre-sorted DatetimeIndex, not `train_test_split` or any random-order
operation.

**Rolling/lag features — PASS, no future leakage.** `.rolling(w, min_periods=1)` and `.shift(lag)`
are both strictly backward-looking pandas operations; verified no `.shift(-n)` (a negative shift,
which would pull future values backward) anywhere in `build_features.py`.

**The one real WARNING: the scaler is fit before the split, not after.** `main.py:191` calls
`fe.scale_features(df_features, fit=True)` on the *entire* feature-engineered dataset, and only
*then* does `DataSplitter.split()` divide it into train/val/test. This means the `RobustScaler`'s
median/IQR were computed using validation- and test-period data, not training data alone —
technically a (mild) form of information leakage from validation/test into the preprocessing step,
though not into the labels or the model's decision boundary directly. This is a real, fixable
methodology note worth including in any write-up, not a fabricated concern — for a dataset this
size the practical effect on results is likely small, but "likely small" is not the same as
"verified small," and it should be named rather than assumed away.

**No national-label-onto-local-weather mismatch found in the code path itself** — the real labels
are date-indexed only (no location dimension), and the weather data is single-point (Lusaka) —
this is a *scope* limitation (Section 7), not a code-level leakage bug: the label correctly answers
"did a flood happen in Zambia on this date," and the model correctly learns from Lusaka weather on
that date, but the two are not asserting a false connection at the code level. It does mean the
resulting model's real-world claim is bounded to "national-flood-day likelihood," not
"Lusaka-specific flood risk" — an important scientific-framing note.

---

## 7. Dataset Audit

```
Dataset name       : NASA POWER Daily Point (Lusaka), + Zambia flood-event log
Location            : ai-engine/data/raw/nasa_power_zambia.csv (weather),
                      ai-engine/data/external/zambia_flood_events_log.csv (labels)
Rows (weather)      : 8,766 (2000-01-01 to 2023-12-31, daily, zero gaps)
Columns (raw)       : 9 (date + 8 meteorological variables)
Geographic coverage : single point — Lusaka (-15.4167, 28.2833) only
Data source         : NASA POWER API (power.larc.nasa.gov) — REAL, live-fetched this week
Flood-event source  : 14 individually-sourced events (FloodList, UN-SPIDER, Charter activations,
                      DMMU/WARMA references) — REAL, hand-researched, cited per-row
Positive samples    : 295 of 8,766 rows (3.37%)
Negative samples    : 8,471 of 8,766 (96.63%)
Missing values      : 0 (confirmed by DataCleaner's own log this session)
Duplicate records   : not separately audited this session — no prior finding flags this as an issue
Spatial coverage     : ONE point for weather; events span multiple provinces (Southern, Central,
                      Eastern, Lusaka, Luapula, Muchinga) — a real spatial mismatch (Section 6)
Temporal resolution  : daily
```

**REAL / SYNTHETIC / MIXED classification: this run is REAL.** Both the weather data
(`model_metadata.json: "data_source": "nasa_power"`) and the labels are real and independently
sourced — verified directly, not assumed from a filename. A separate, still-present
`ai-engine/data/raw/synthetic_zambia_weather.csv` exists from the prior (2026-09-07/08) run and
must not be confused with this one — the two are cleanly separated by filename and by
`model_metadata.json`'s explicit `data_source` field, which is exactly the discipline this
project's own rules ask for.

---

## 8. Flood Label Audit

```
Target variable        : flood_label (binary)
Label definition        : 1 if the date falls within a documented flood event's
                          start_date–end_date window (or is the start_date itself,
                          for the 9 events with no recorded end date); 0 otherwise
Positive class          : a real, individually-sourced flood event was reported on/around this date
Negative class          : no such event was reported (NOT verified as "definitely no flooding
                          occurred" — absence of a report is not proof of absence)
Label source            : ai-engine/data/external/zambia_flood_events_log.csv (14 rows),
                          each with its own source_name/source_url/confidence_notes column
Label date range        : 2007-01-01 to 2026-01-03 (event dates); applied against weather data
                          covering 2000-2023
Positive examples        : 295 (out of 8,766 weather rows)
Negative examples        : 8,471
```

**This label represents a real, sourced, event-based occurrence — not a synthetic threshold or
proxy formula** — for this run specifically. It does **not** claim to represent every flood that
happened (media/report-derived event logs under-count real events; this is disclosed in the CSV's
own `README.md` and in `docs/LIMITATIONS.md`), and the "negative" class is really "no reported
event," not "confirmed dry." This distinction matters and should be stated in any dissertation
text exactly this way — this is a genuine, real-event label, with a genuine, known, disclosed
under-counting risk, not a risk proxy pretending to be an observation.

---

## 9. Train/Validation/Test Split Audit

```
Training split          : 6,138 rows, 2000-01-01 → 2016-10-20 (70%)
Validation split         : 1,314 rows, 2016-10-21 → 2020-05-26 (15%)
Test split               : 1,314 rows, 2020-05-27 → 2023-12-31 (15%)
Random split?            : NO
Temporal split?          : YES — strict chronological, confirmed by code read
Walk-forward validation? : NO — single fixed split, not rolling-origin
Potential temporal leakage? : One instance found — the RobustScaler is fit on the full dataset
                              before splitting (Section 6's WARNING), not on the training
                              portion alone. The label/feature construction itself has no
                              temporal leakage.
```

---

## 10. Model Registration Audit (Database)

1. **`model_versions` table exists** — confirmed in `backend/app/models/prediction.py:9-26` and
   the Alembic migration.
2. **Columns:** `id`, `version` (unique), `model_type`, `training_period_start`,
   `training_period_end`, `metrics_json`, `artifact_path`, `is_active`, `registered_at`. No
   `dataset_version` or `feature_schema` column exists — if per-feature-list versioning matters
   for reproducibility claims, that's presently only recoverable via `feature_columns.json`
   sitting alongside the artifact, not via the DB row itself.
3. **Records currently registered: ZERO.** Confirmed live this session: `curl
   http://127.0.0.1:8000/api/v1/models` → `[]`.
4. **`GET /api/v1/models` exists** (`backend/app/api/model_registry.py:12-16`) and is a correct,
   simple `SELECT * FROM model_versions ORDER BY registered_at DESC` — the emptiness is a data
   problem, not a broken query.
5. **The trained model is NOT connected to the database in any way.** No code anywhere in
   `backend/` or `ai-engine/` constructs a `ModelVersion` row — confirmed by grep for
   `ModelVersion(` across the whole repository, matching only the class definition itself.
6. **The database does not know which artifact to load** — there is no row, so there is nothing
   for `artifact_path` to point to yet.
7. **`is_active` boolean exists as a column** and is exactly the right mechanism for an
   active/production flag — it's simply never been set because no row exists.
8. **Model versioning is schema-ready but not implemented** — the `version` column (unique
   string) is the intended versioning mechanism; nothing populates it yet.

---

## 11. Prediction Pipeline Audit

| Stage | Status | Existing File/Endpoint | Explanation |
|---|---|---|---|
| Input validation | MISSING | — | No request schema exists for "give me a prediction for location X" — no such endpoint exists at all |
| Feature preparation | PARTIAL | `ai-engine/src/features/build_features.py` | Real, working code — but it's training-pipeline code, not wired to accept a single live weather reading for on-demand inference |
| Preprocessing | PARTIAL | same file, `scale_features(fit=False)` path | The inference-mode branch exists in code and is correct, but has never been called by anything outside the training script |
| Model loading | MISSING (in backend) / EXISTS (in ai-engine) | `ai-engine/saved_models/*.joblib` | Files exist and load-tested clean (Section 4); no backend code loads them |
| Inference | MISSING | — | No `.predict()`/`.predict_proba()` call exists anywhere in `backend/` (confirmed by grep) |
| Probability | MISSING | — | Follows from the above |
| Risk classification | MISSING | — | `Prediction.risk_level` column exists in the DB schema; nothing computes a value for it |
| SHAP explanation | BLOCKED | `ai-engine/src/explainability/explain_models.py` | Real, complete implementation; `shap` not installed; never executed (confirmed via the run's own log: "SHAP not installed. Skipping explainability plots.") |
| DB persistence | MISSING | `backend/app/models/prediction.py` (`Prediction` table) | Table and schema exist; no `INSERT` path exists — there isn't even a `POST /predictions` endpoint, only `GET` |
| API response | EXISTS (for the empty case) | `backend/app/api/predictions.py` | Correctly, honestly returns `[]` — this is the one stage that is fully done, precisely because there's nothing to hide yet |
| Frontend display | EXISTS (for the empty case) | `frontend/src/pages/Predictions.tsx`, `AIModel.tsx` | Both correctly render an honest empty state sourced from the real (empty) API response — verified by this week's UI redesign work, not a new finding |

**Where the system currently stops, precisely:** immediately after "trained model artifact exists
on disk." Every stage from "model loading inside the running application" onward does not exist.

---

## 12. FastAPI Backend Architecture Audit

Clean architecture already exists and should be extended, not replaced — verified directly:
- `backend/app/repositories/` (new this week) — `WeatherObservationRepository`,
  `DataSourceRepository`. **No `PredictionRepository`/`ModelVersionRepository` exists yet** — the
  natural place to add one, following the exact pattern already established for the other two.
- `backend/app/integrations/` (new this week) — `NasaPowerWeatherProvider`/`HttpHealthChecker`,
  both real external-I/O wrappers behind a small interface + FastAPI `Depends()` injection seam
  (so tests can swap in a fake). **No `ModelInferenceProvider`-shaped equivalent exists** — this is
  the natural pattern to reuse for "load model, run inference," not a new architecture to invent.
- `backend/app/services/` — currently `weather_ingestion.py`, `data_source_health.py`, both thin
  orchestration functions. **No `prediction_service.py` exists.**
- `backend/app/schemas/` — `PredictionOut`/`ModelVersionOut` already exist and match the DB
  columns exactly; no new output schema is needed for a first version, only a `PredictionCreate`-
  shaped input if a request-driven (rather than batch/scheduled) endpoint is wanted.

**Recommendation embedded in this finding (not an instruction to act on yet, per Rule 8):** any
integration should add `backend/app/integrations/model_inference.py` (mirrors
`weather_provider.py`'s pattern exactly: an interface + a real `JoblibModelProvider` implementation
+ a `get_model_provider()` FastAPI dependency) and `backend/app/repositories/prediction_repository.py`
+ `model_version_repository.py`, then a `backend/app/services/prediction_service.py` that composes
them — the same layering this week's architecture pass already established for weather/health
checks, applied to a third real external concern (a trained model) instead of inventing a fourth
pattern.

---

## 13. Existing Prediction-Adjacent Endpoints

| Method | Path | Auth | Request | Response | DB | ML | Status |
|---|---|---|---|---|---|---|---|
| GET | `/api/v1/models` | public | — | `list[ModelVersionOut]` | reads `model_versions` | none | Live-tested this session: `200 []` |
| GET | `/api/v1/models/{id}` | public | — | `ModelVersionOut` | reads `model_versions` | none | 404 for any id (table empty) |
| GET | `/api/v1/predictions` | public | — | `list[PredictionOut]` | reads `predictions` | none | Live-tested this session: `200 []` |

**No `POST /api/v1/predictions`, no `/forecast`, no `/risk` endpoint exists anywhere** — confirmed
by grep across `backend/app/api/`. `/api/v1/alerts` exists and is unrelated (human-issued warnings,
not model output). This means there is currently no API surface at all for triggering or receiving
a live inference, even hypothetically — the gap is not "the endpoint returns nothing," it's "the
endpoint to ask for something doesn't exist yet."

---

## 14. Frontend Audit

- `frontend/src/pages/Predictions.tsx` — real, consumes `GET /api/v1/predictions` via `fetchPredictions()`
  (`frontend/src/services/predictions.ts`), renders an honest empty state today, and (per this
  week's redesign) a real `RiskBadge`-driven table/KPI-strip the moment the API ever returns rows —
  **no mock/hardcoded data anywhere in this file**, confirmed by direct read.
- `frontend/src/pages/AIModel.tsx` — same pattern against `GET /api/v1/models`, same honest-empty
  behavior, same "will render real registry data with zero code changes the day a row exists."
- **No Prediction Detail screen exists** (`/predictions/:id` is not a route in `App.tsx`) — this
  is a known, previously-documented gap (`docs/missing-features.md`), not new. Building it before
  any real `Prediction` row can exist would be premature.
- `RiskMap.tsx`/`LocationDetail.tsx` both already have the "no prediction available" honest-empty
  language wired in per-location; connecting them to a real value later is a data-availability
  change, not a UI rebuild.
- **Confirmed: the frontend currently consumes real backend data everywhere it touches predictions,
  never mock/static data.** This holds across the entire prediction-adjacent surface, verified by
  this week's redesign work (which touched every one of these files) plus this session's direct
  re-read of `Predictions.tsx`.

---

## 15. SHAP / Explainability Audit

```
SHAP installed?              NO (confirmed: python -c "import shap" -> ModuleNotFoundError)
SHAP code exists?            YES — ai-engine/src/explainability/explain_models.py is a complete,
                              real implementation (global importance, summary/waterfall/dependence/
                              force plots) — not a stub
Model compatible?            YES, in principle — SHAP's TreeExplainer supports every tree-based
                              model already trained here (DecisionTree/RandomForest/GradientBoosting);
                              LogisticRegression (the actual best model) would need SHAP's
                              LinearExplainer or KernelExplainer instead of TreeExplainer — the
                              existing code only wires up `model_type="tree"` (main.py:282), so as
                              written it targets RandomForest specifically, not the best model
Explanation generated?       NO — caught by ImportError, never ran
Explanation stored?          NO
Explanation returned by API? NO — `PredictionOut.explanation` is a free-text column with no
                              current writer
Explanation displayed?       NO — no UI surface has ever received one to render
```

**Required for a first working prediction: NO.** **Recommended later enhancement: YES.** This
audit explicitly separates the two per the governing prompt's instruction — a first real
prediction (probability + risk class) does not need SHAP to be honest or useful; it needs to say
"why" only once explainability actually exists, and until then the `explanation` field should
either stay empty or contain a plain, non-SHAP statement like "derived from recent rainfall and
soil-moisture trends" rather than a fabricated feature-attribution table.

---

## 16. Minimum Path to a Real Working Prediction (derived from actual repo state, not assumed)

```
STEP 1 — Decide which model is the production candidate: the evidence in Section 2 says
         Logistic Regression, not the RandomForest main.py currently hardcodes for SHAP.
         This is a decision, not an engineering task, and should be made deliberately.
STEP 2 — Write model_metadata.json's contents (already exists) into a real ModelVersion row:
         version, model_type="LogisticRegression", training_period_start/end (2000-01-01 /
         2016-10-20, the TRAIN period, not the full dataset — a real methodology choice to
         get right), metrics_json (the real Section 2 numbers), artifact_path (the real
         .joblib path), is_active=True.
STEP 3 — Add backend/app/repositories/model_version_repository.py + prediction_repository.py,
         mirroring the existing weather_observation_repository.py pattern exactly.
STEP 4 — Add backend/app/integrations/model_inference.py: an interface + a real
         JoblibModelProvider that loads the .joblib + scaler.joblib + feature_columns.json
         once (not per-request) and exposes predict(features: dict) -> (probability, risk_level).
STEP 5 — Add backend/app/services/prediction_service.py composing the above: given a location's
         latest real weather observations (already flowing in via the existing
         weather_ingestion.py path), build the exact 54-feature vector in the exact saved
         order, scale it, call the model, classify risk.
STEP 6 — Feature availability check BEFORE inference: this is the real, non-optional gate —
         the model needs rolling/lag windows up to 30 days of prior daily weather per
         location. Locations with insufficient real weather_observations rows cannot get a
         real prediction yet; this must fail honestly (no prediction, not a fabricated one),
         not silently default missing inputs to zero.
STEP 7 — Add a prediction endpoint (POST /api/v1/predictions/{location_id}/run or similar,
         RBAC-gated the same way alert/data-source actions already are) that calls the
         service and persists a real Prediction row.
STEP 8 — Frontend: no new page needed for a first version — Predictions.tsx and AIModel.tsx
         already render real data the moment the API returns it; only a trigger UI (e.g. a
         button, mirroring LocationDetail.tsx's existing "Fetch weather data" pattern) is new.
STEP 9 — End-to-end test: real weather in -> real feature vector -> real model.predict_proba()
         -> real DB row -> real API response -> real rendered UI, verified live, the same way
         this week's notifications feature was verified (a real round trip, not a unit test
         claiming success).
STEP 10 — SHAP explanation: deferred, per Section 15 — add only after Step 9 works, and only
          using LinearExplainer/KernelExplainer (not the currently-wired TreeExplainer) if
          Logistic Regression stays the production candidate.
```

**Explicitly not necessary steps** (per Rule 5 / Rule 6, and confirmed unnecessary by this audit's
own findings, not assumed): no new Python environment/venv is needed for this path (Section 4's
finding — the backend already has scikit-learn/joblib available); no XGBoost/LSTM training is a
prerequisite (Logistic Regression is the actual best current model); no new database is needed
(the schema is already correctly shaped); no message queue, background-job framework, or separate
inference microservice is needed at this data volume (a handful of locations, daily-cadence
weather) — in-process inference inside the existing FastAPI app is sufficient and is what the
existing `weather_ingestion.py`/`data_source_health.py` pattern already models for "call something
external/slow from within a request."

---

## 17. What Must NOT Be Done

- Do not assume XGBoost or LSTM are ready — neither is installed, and Logistic Regression is the
  actual best-performing model that exists today (Section 2).
- Do not let `main.py`'s hardcoded RandomForest-for-SHAP convention silently become "the
  production model" by default — it is not the best one.
- Do not fabricate a `Prediction` row, a metric, or a SHAP value to make the Predictions/AI Model
  screens "look done" — every one of those screens currently earns its honesty and should keep it.
- Do not build a Prediction Detail or Citizen-Report Detail screen before real data exists to show
  on them (both already correctly deferred).
- Do not treat "no reported flood" (the negative class) as "confirmed no flood" in any UI copy or
  documentation — the label audit (Section 8) is explicit about this distinction.
- Do not introduce a new Python environment, a separate inference microservice, Docker, a message
  queue, Kubernetes, or Supabase to solve this — none of that is needed at this data volume, and
  Section 16 already found a path that reuses the exact architecture this week's work built.
- Do not skip the "does this location have enough real weather history" feature-availability check
  — silently zero-filling missing lag/rolling inputs would produce a plausible-looking but
  meaningless prediction, which is exactly the kind of fabrication this project's rules forbid.
- Do not replace the fit-before-split scaler issue (Section 6) with a bigger retraining effort as a
  precondition for integration — it's real, it's worth fixing eventually, but it does not block a
  first honest prediction, and conflating "not perfect" with "not usable" would stall real progress
  over a second-order methodology refinement.
- Do not delete or modify `ai-engine/main.py`'s RandomForest/SHAP wiring as part of this
  integration work without a separate, deliberate decision — that's an ai-engine research-pipeline
  concern, distinct from the backend-integration work this audit scoped.

---

## 18. Python Environment Assessment

```
Current Python (both backend and ai-engine, confirmed same interpreter): 3.14.0
Required for scikit-learn baselines (what actually exists and works): 3.14 — already satisfied,
    confirmed by the live load test in Section 4.
Required for XGBoost: not Python-version-blocked per se, just not installed — could likely be
    installed on 3.14 (not verified this session, since installing anything is out of scope for
    a read-only audit).
Required for TensorFlow (LSTM) and SHAP (if pinned to a TF-era constraint): Python 3.11, per
    ai-engine/requirements.txt's own comment and this project's own prior audits.
Why: TensorFlow's published wheels do not yet support Python 3.14 at the pinned version this
    project's requirements file specifies.
Migration/venv recommendation: NOT required for the minimum path in Section 16 (Logistic
    Regression only). Only required if/when XGBoost+SHAP or LSTM work resumes — at that point, a
    dedicated `py -3.11 -m venv` for ai-engine specifically (not backend) is the right-sized fix,
    exactly as this project's own documentation already recommends.
```

---

## 19. Scientific Integrity Ratings

| Dimension | Rating | Why |
|---|---|---|
| Data authenticity | GOOD | Real NASA POWER data, live-fetched and verified this week; no synthetic data in this run |
| Label validity | ACCEPTABLE | Real, sourced, event-based — but media-derived, likely under-counts, and "negative" means "unreported," not "confirmed absent" (disclosed, not hidden) |
| Feature validity | GOOD | All 54 features are real meteorological/derived quantities with clear physical rationale; none are fabricated or placeholder |
| Temporal validation | GOOD | Strict chronological split, no shuffling, no future-looking window operations |
| Spatial validity | NEEDS WORK | Single-point (Lusaka) weather paired with multi-province event labels — a real scope mismatch, disclosed in this audit and not previously named this precisely |
| Leakage prevention | ACCEPTABLE | Labels are clean of feature-derived leakage this run; one real but minor issue (scaler fit before split, Section 6) |
| Model reproducibility | GOOD | Fixed seed (42), versioned config/metrics per run, feature list saved alongside artifacts — genuinely reproducible from what's checked in |
| Model evaluation | ACCEPTABLE | Real metrics computed correctly (accuracy/precision/recall/F1/ROC-AUC/PR-AUC/Brier) — but no confusion matrix or calibration plot artifact was found, and class-imbalance handling is absent, which is the likely cause of two of the four models collapsing to near-zero recall |
| Prediction calibration | NEEDS WORK | Brier scores exist and are reported (a genuine calibration signal), but no calibration curve/plot exists, and no calibration method (e.g. Platt scaling, isotonic) has been applied |
| Explainability | CRITICAL | Real code exists but has never executed once — zero explanations have ever been produced, stored, or shown, for any model, ever, in this project's history |

---

# A. EXECUTIVE SUMMARY

**How much of the ML system is actually complete?** As an engineering estimate (not a scientific
measurement): **the training/research pipeline is ~65% complete** (real data, real labels, real
baseline models, real honest metrics — missing only XGBoost/LSTM/SHAP and class-imbalance
handling), but **the integration into the running product is ~5% complete** (a database schema
that's ready, and nothing else — no loading code, no inference service, no endpoint, no persisted
prediction, ever, anywhere in the running application). Averaging those two numbers would be
misleading, since they measure different things; both are reported separately rather than blended
into one falsely-precise overall percentage.

# B. WHAT WE ALREADY HAVE

- Four real, trained, load-tested scikit-learn models, on real NASA POWER weather + real
  researched flood-event labels, with real (if modest) evaluation metrics and no proxy-label
  leakage in this specific run.
- A correctly-shaped, migrated, currently-empty database schema (`model_versions`, `predictions`)
  ready to receive real rows with no schema changes needed for a first version.
- A clean backend layering pattern (`repositories/`, `integrations/`) already established this
  week for two other external concerns, directly reusable for model inference without inventing a
  new pattern.
- Frontend screens (`Predictions.tsx`, `AIModel.tsx`) that already correctly render real data the
  moment the API provides it — verified to contain no mock data.
- A complete, real SHAP implementation that has simply never been run.
- A working, environment-verified model-load path: the backend's own Python process can already
  `import joblib, sklearn` and load every trained artifact today.

# C. WHAT IS MISSING

**BLOCKING** (nothing works end-to-end without these): a model-loading service inside the backend;
a prediction/inference service; a feature-preparation path that turns real stored weather
observations into the exact 54-feature vector; at least one endpoint to trigger/serve a real
prediction; a write path from that service into the `Prediction`/`ModelVersion` tables.

**IMPORTANT** (correctness/credibility, not blocking a first demo): a deliberate "which model is
production" decision (currently defaults, wrongly, to whatever's hardcoded); a feature-availability
gate so locations without enough weather history don't get a fabricated prediction; fixing the
scaler fit-before-split issue; class-imbalance handling before trusting RandomForest/GradientBoosting
results.

**NICE TO HAVE**: SHAP explanations (real code exists, just needs the environment and the right
explainer type for whichever model is chosen); confusion-matrix/calibration plots as saved
artifacts; XGBoost/LSTM once environment work is done.

# D. EXACT MODEL DETAILS

```
Model             : Logistic Regression (recommended production candidate — see Section 2)
Artifact          : ai-engine/saved_models/logisticregression_model.joblib (1,247 bytes)
Framework         : scikit-learn 1.8.0
Python version    : 3.14.0
Features          : 54 (exact list in Section 5 / feature_columns.json)
Dataset           : NASA POWER daily point, Lusaka, 2000-01-01 to 2023-12-31 (8,766 rows)
Training period   : 2000-01-01 to 2016-10-20 (6,138 rows, 243 positive)
Validation period : 2016-10-21 to 2020-05-26 (1,314 rows, 7 positive)
Test period       : 2020-05-27 to 2023-12-31 (1,314 rows, 45 positive)
ROC-AUC (test)    : 0.8502
Recall (test)     : 0.4889
Precision (test)  : 0.2037
F1 (test)         : 0.2876
PR-AUC (test)     : 0.1323
Brier (test)      : 0.0693
Confusion matrix  : NOT FOUND as a saved artifact
Calibration curve : NOT FOUND as a saved artifact
```

# E. Current Architecture

```
REAL NASA POWER DATA (ai-engine/data/raw/nasa_power_zambia.csv)
 ↓
PREPROCESSING (DataCleaner — real, executed)
 ↓
FEATURE ENGINEERING (FeatureEngineer — real, executed, 54 features)
 ↓
MODEL (4 real scikit-learn baselines, trained, saved, load-test PASS)
 ↓
??? ← NOTHING EXISTS PAST THIS POINT INSIDE THE RUNNING APPLICATION
 ↓
FASTAPI (real, running — but has no model-loading or inference code)
 ↓
POSTGRESQL (real, running — model_versions/predictions tables exist, both empty)
 ↓
REACT (real, running — Predictions.tsx/AIModel.tsx correctly render the current empty truth)
```

# F. ML Integration Gap

```
REAL DATA (NASA POWER + real flood-event log)
   ↓
TRAINING (4 baseline models, real metrics, load-tested)
   ↓
TRAINED MODEL ARTIFACT (ai-engine/saved_models/*.joblib)
   ↓
[SYSTEM CURRENTLY STOPS HERE]
   ↓
MODEL REGISTRY (schema exists, 0 rows — nothing writes to it)
   ↓
INFERENCE SERVICE (does not exist in backend/)
   ↓
PREDICTION API (GET exists and is honest; no POST/trigger endpoint exists)
   ↓
DATABASE (Prediction table exists, 0 rows, no writer)
   ↓
FRONTEND (correctly renders the current — empty — truth; will render real data with no
          changes needed the moment upstream stages exist)
```

# G. Implementation Plan

| # | Objective | Files likely affected | Dependencies | Risk | Acceptance criteria |
|---|---|---|---|---|---|
| 1 | Decide + document the production model choice | `docs/ML-METHODOLOGY.md`, `docs/MODEL-EVALUATION.md` | Section 2's real metrics | Low — a decision, not code | A written, evidence-cited choice exists, naming Logistic Regression or explaining why not |
| 2 | Register the chosen model as a real `ModelVersion` row | a one-off script or admin action, not new architecture | Task 1 | Low | `GET /api/v1/models` returns exactly one real row with real metrics |
| 3 | Build `ModelVersionRepository`/`PredictionRepository` | `backend/app/repositories/` | Existing repository pattern | Low | Mirrors `weather_observation_repository.py` exactly |
| 4 | Build `model_inference.py` integration (interface + `JoblibModelProvider`) | `backend/app/integrations/` | Task 2 (needs `artifact_path`), scikit-learn already available | Medium — first real inference code in this backend | A unit test loads the real artifact and gets a real probability for a known feature vector |
| 5 | Build a feature-preparation function turning stored `WeatherObservation` rows into the exact 54-column vector | `backend/app/services/prediction_service.py` (new) | `feature_columns.json`'s exact order | Medium-High — the single most error-prone step (silent misordering) | A test asserts the built vector's column order matches `feature_columns.json` byte-for-byte |
| 6 | Add the feature-availability gate (refuse to predict without enough real history) | same service | Task 5 | Low | A location with insufficient weather history gets an honest "not enough data" response, never a fabricated one |
| 7 | Add a prediction-trigger endpoint | `backend/app/api/predictions.py` | Tasks 3-6 | Medium | A real `POST`, RBAC-gated like alerts, persists a real `Prediction` row end-to-end |
| 8 | Add a trigger UI element | `frontend/src/pages/LocationDetail.tsx` (mirrors its own existing "Fetch weather data" button) | Task 7 | Low | Clicking it produces a real, rendered prediction, no mock |
| 9 | End-to-end live test | new backend test file, mirroring `test_notifications.py`'s round-trip style | Tasks 1-8 | — | A real weather-in → real prediction-out round trip passes, verified live, not just unit-tested |
| 10 | SHAP, deferred | `ai-engine`/`backend` (later) | Task 1 (explainer type depends on model choice), environment work (Section 18) | — | Not part of this plan's Definition of Done |

# H. Definition of Done

**Technical:** a real `ModelVersion` row exists with `is_active=True` and an accurate
`artifact_path`; `GET /api/v1/models` returns it; a real endpoint accepts a request, loads the
real model, builds the real 54-feature vector from real stored weather data (with a feature-
availability gate, not zero-filled fabrication), computes a real probability, persists a real
`Prediction` row; `GET /api/v1/predictions` and the frontend render that real row with no
code changes needed beyond what already exists; a live end-to-end test (not just a unit test)
demonstrates this working against the real running stack.

**Scientific:** the `explanation` field either stays empty or contains language honestly
describing what the model used, never a fabricated SHAP-shaped explanation before SHAP actually
runs; the model card / any dissertation text names the real metrics from Section 2, the real
train/val/test date ranges, and explicitly states the label-source and spatial-coverage caveats
from Sections 6-8 — not a rounded-up or cherry-picked characterization.

# I. Final Recommendation

1. **Should we integrate the existing trained model now?** Yes — Logistic Regression specifically.
   It is real, load-tested, and has the best (if modest) metrics of anything actually trained.
2. **Should we retrain first?** No, not before a first integration — but yes, eventually: fixing
   the scaler fit-before-split issue (Section 6) and adding class-imbalance handling
   (`class_weight="balanced"` or similar) are both small, well-understood fixes worth a follow-up
   retrain once integration plumbing exists, so there's something meaningful to re-integrate.
3. **Should we use XGBoost now? DO NOT DO THIS** — it isn't installed, isn't trained, and isn't
   the best-performing option that exists; installing and training it is real, separate,
   uncommitted work, not a integration-blocking prerequisite.
4. **Should we add LSTM now? DO NOT DO THIS** — same reasoning, plus a real Python-version
   migration cost (Section 18) for a model type this project's own baselines don't yet justify.
5. **Should we improve the dataset before integration? DO NOT BLOCK ON THIS** — the spatial
   (single-point) and label (under-counting) limitations are real and worth continued research
   effort, but they don't prevent an honest first integration that's explicit about those bounds.
6. **Should we modify the existing frontend?** No rebuild needed — `Predictions.tsx`/`AIModel.tsx`
   already do the right thing; only a small trigger control (Task 8) is new, additive UI.
7. **Fastest scientifically defensible route to a working demonstration:** Sections 16 and G's
   ten-task plan, using Logistic Regression, with the feature-availability gate as the one
   non-negotiable safety check — everything else in that plan reuses architecture that already
   exists and already works.
8. **What should be done AFTER the first real prediction is successfully displayed?** Fix the
   scaler-fit-before-split methodology issue and retrain; add class-imbalance handling and
   retrain; then, and only then, revisit XGBoost/SHAP once a Python 3.11 environment decision is
   made deliberately (this is exactly the fork already surfaced and deferred earlier this week);
   write up the real metrics, real limitations, and real integration architecture for the
   dissertation using this audit's Sections 2, 6, 7, 8, and 19 as the primary evidentiary source.

---

## STOP — Audit complete. No files were modified, created, or deleted by this audit, with the one
disclosed exception in the preamble (a git-ignored, deterministic, regenerable intermediate CSV
re-saved as an unavoidable side effect of calling real, unmodified pipeline code to compute exact
sample counts rather than estimate them).
