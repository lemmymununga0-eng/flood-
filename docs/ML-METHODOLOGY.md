# ML Methodology — FloodShield Zambia

Status: Phase 0/1 planning document. No model has been trained. No figures in this
document are results — they are the plan for producing results.

## Flood target / label design (the highest-risk decision in this project)

No target variable has been defined yet. Candidate approaches, per the governing
prompt's ranking from strongest to weakest evidentiary basis:

1. **Historical flood-event records** — strongest if a reliable Zambian source can be
   found. **Update 2026-09-07:** a first version of this now exists —
   `ai-engine/data/external/zambia_flood_events_log.csv`, eleven hand-compiled,
   individually-sourced flood events across Zambia from January 2020 through
   December 2025/January 2026, built from FloodList, UN-SPIDER, and Charter-activation
   reporting (see that file's `README.md` for full provenance and caveats). This is a
   genuine step beyond "no data" but is explicitly **not** validated ground truth yet:
   it is media/situation-report-derived (likely under-counts real events), has **no
   negative examples** (periods without flooding — required to train a classifier), and
   contains one unresolved date discrepancy (row `ZM-2023-01`). Eleven positive events
   over six years is also a small sample — see the statistical-power note added to
   `docs/LIMITATIONS.md`. **Next step:** decide how negative examples will be
   constructed (e.g. sampling non-event periods at the same locations) and attempt to
   cross-reference each row against a primary DMMU/WARMA source.
2. **Official disaster/flood reports** — e.g. from a national disaster-management
   authority or international humanitarian reporting. **Update 2026-09-07:** DMMU
   (Office of the Vice President) and WARMA (Water Resources Management Authority) are
   confirmed as Zambia's authoritative bodies for this (VERIFIED via UN-SPIDER and
   ReliefWeb); DMMU's own site was unreachable this session and needs a retry or direct
   contact.
3. **Remote-sensing-derived flood extent** — satellite-derived flood mapping for
   specific events/regions. **Update 2026-09-07:** a concrete, real precedent exists —
   International Charter Space and Major Disasters Activation #796 (Jan–Feb 2023)
   produced 10 Sentinel-2B-derived flood-extent products for Zambia (Luapula, Kafue, and
   Zambezi river systems; Mkushi district). Public access path to the underlying rasters
   is still TO VALIDATE.
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
