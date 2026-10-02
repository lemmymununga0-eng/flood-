# Model Evaluation — Flood Prediction System ZM

Updated 2026-10-01. Every figure here was measured, not estimated. Per
`docs/RESEARCH-METHODOLOGY.md`, whatever the numbers turned out to be is what is reported
— and they are weak. That is the finding.

## Headline

**No machine-learning model beat a day-of-year seasonal climatology baseline that uses no
weather data at all.** The formal deployment gate returned `DO_NOT_DEPLOY`, 2 of 5
pre-declared criteria passed, and no model was exported.

## Why accuracy is not reported as a headline

Floods are roughly **0.1% of district-days**. A model predicting "no flood" every single
day scores **99.9% accuracy** and is worthless. At this base rate the precision-recall
curve is the informative one; ROC-AUC is dominated by the enormous true-negative mass.
**PR-AUC against a baseline** is the primary metric throughout.

## Validation comparison — 25 runs, corrected labels, 82 districts

Selection was made on validation only. The test split was locked.

| Rank | Approach | ROC-AUC | PR-AUC | Recall |
|---:|---|---:|---:|---:|
| 1 | **Seasonal climatology** (no weather) | 0.640 | **0.00336** | 0.743 |
| 2 | XGBoost + soil moisture | 0.614 | 0.00300 | 0.260 |
| 3 | XGBoost + rainfall accumulation | 0.641 | 0.00292 | 0.248 |
| 4 | Decision Tree, weather only | 0.608 | 0.00277 | 0.677 |
| 14 | **Logistic Regression** (the served model) | 0.604 | 0.00250 | 0.695 |

The best of 25 runs reaches **89%** of the baseline's PR-AUC.

Adding climate indices (ENSO/IOD) and seasonal encodings drove performance **below
chance** (ROC-AUC 0.38–0.52) — reported as the real negative result it is.

## Incremental-skill test

The sharper question is not "does the model beat climatology" but "does weather add
anything *on top of* climatology". Models were given the climatology score as an input
feature, so any gain is incremental by construction.

| Setting | Model | H beats F | Median H/F |
|---|---|---:|---:|
| Spatio-temporal | Decision Tree | 5/10 | 1.000 |
| | Logistic Regression | 6/10 | 1.046 |
| | XGBoost | 6/10 | 1.100 |
| Rolling-origin | Decision Tree | 6/15 | 0.947 |
| | Logistic Regression | 9/15 | 1.078 |
| | XGBoost | 9/15 | 1.011 |

Weather's isolated contribution: **−5% to +10%**, winning roughly half the folds. A coin
flip with a slight positive tilt, not predictive skill.

## Temporal robustness — 15 rolling-origin folds

| Candidate | Folds won | Mean PR-AUC ratio |
|---|---:|---:|
| XGBoost + climatology + weather + rain + soil | 4/15 | **0.755** |
| XGBoost + climatology + weather | 3/15 | 0.708 |
| Decision Tree + climatology + weather | 1/15 | 0.649 |
| Logistic Regression + climatology | 0/15 | 0.663 |

Every ratio is below 1.0 — on average **25–35% worse** than the calendar.

### The result that justifies this design

On the single fixed split, `DecisionTree / climatology+weather` scored **+94.8%** over the
control — the most promising number the project produced. Under 15 rolling folds it won
**one**, averaging 0.649×. A single-split result with 331 positives was noise. Stopping
there would have shipped a model with no skill.

## The served model's own provenance

`flood_risk_lr_v1` reported test ROC-AUC **0.777**. Two qualifications travel with it:

1. **It was selected on the test set.** On validation a different model (GradientBoosting)
   ranked first. Treat 0.777 as an in-sample figure.
2. **Trivial baselines beat it on that same split** — a calendar lookup scored 0.728 and a
   single 7-day rainfall column scored 0.822.

Its confusion matrix at threshold 0.50: **TP 56, FP 88,184, FN 7** — precision 0.0006,
roughly one false alarm per district every two days.

## Interpretation

The limiting factor is **flood-label completeness**, not model capacity. Evidence: the
higher-capacity models performed *worse*, and the served model's fitted weights are
humidity +2.003, max temperature +1.445, rainfall **+0.018** — it detects humidity, not
floods.

Full detail: `ml/README.md`, `ml/labels/LABEL_PROVENANCE.md`, and the reports under the
corrected pipeline's output directory (`validation_ablation.csv`,
`rolling_origin_summary.json`, `spatiotemporal_holdout_summary.json`,
`deployment_decision.json`).
