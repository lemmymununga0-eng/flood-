# ML Methodology — FloodShield Zambia

Status: Phase 0/1 planning document. No model has been trained. No figures in this
document are results — they are the plan for producing results.

## Flood target / label design (the highest-risk decision in this project)

No target variable has been defined yet. Candidate approaches, per the governing
prompt's ranking from strongest to weakest evidentiary basis:

1. **Historical flood-event records** — strongest if a reliable Zambian source can be
   found (TO VALIDATE, see DATA-SOURCES.md).
2. **Official disaster/flood reports** — e.g. from a national disaster-management
   authority or international humanitarian reporting (TO VALIDATE).
3. **Remote-sensing-derived flood extent** — satellite-derived flood mapping for
   specific events/regions (TO VALIDATE).
4. **Hydrological thresholds** — river-gauge or basin-model-derived thresholds, if
   accessible for Zambian catchments (TO VALIDATE, likely hard to obtain).
5. **Rainfall-accumulation thresholds supported by literature** — a documented,
   citable proxy (e.g. multi-day precipitation accumulation exceeding a
   literature-justified threshold for the region). This is the most likely fallback if
   1–4 are unavailable.
6. **A carefully defined, documented research proxy** — as a last resort, with the
   proxy's construction and its limitations stated explicitly everywhere it's used.

Whichever is selected must be documented here with its source, and every place the
resulting label is used (training, evaluation, dashboard, API) must describe it
accurately. A proxy label is never described as "actual flood occurrence" unless real
flood observations support that claim (governing prompt, section 10).

## Candidate models

| Model | Role |
|---|---|
| Logistic Regression | Baseline, interpretable |
| Decision Tree | Baseline, interpretable |
| Random Forest | Ensemble baseline |
| Gradient Boosting | Ensemble baseline |
| XGBoost | Primary structured-data candidate — class imbalance handling, tuning, calibration, feature importance, time-series-aware CV |
| LSTM | Time-series candidate — only evaluated once preprocessing and baselines are solid, and only kept if it earns its complexity against the baselines |

No model is assumed to be the winner in advance (governing prompt rule 9/10). The
comparison table in `docs/MODEL-EVALUATION.md` (populated in Phase 7) will report actual
metrics for whichever models are actually trained — including if all of them perform
poorly.

## Data leakage controls (must be verified in code review before any model is called
successful)

- Chronological train/validation/test split — no random shuffling of time-ordered
  observations.
- Scalers/normalizers fit on the training period only, then applied to validation/test.
- No feature is allowed to be derived from a time window that includes the prediction
  target's own future.
- The test set is not touched during feature engineering or model selection — only for
  final evaluation.

## Evaluation approach (Phase 7)

Accuracy, precision, recall, F1, ROC-AUC, PR-AUC, and confusion matrix for every trained
model. Recall is weighted heavily (a missed flood is more costly than a false alarm) but
not maximized blindly — false-positive rate and precision are reported alongside it,
since excessive false alarms erode public trust in the system.

## Explainability (Phase 8)

SHAP and/or feature importance for global explanations; per-prediction local
explanations grounded only in the actual features the model used for that prediction.
Explanations describe correlation the model found, not asserted causal mechanisms — e.g.
"elevated rainfall accumulation over the preceding period contributed strongly to this
prediction" is valid; "flooding will definitely occur because soil saturation is 90%" is
not, unless that value is an actual model input and the model's behavior genuinely
supports that characterization.
