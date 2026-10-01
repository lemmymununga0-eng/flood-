# FloodShield Zambia — corrected ML pipeline

This package is the `CORRECTED_PIPELINE`. It does not replace or overwrite
`CURRENT_RESEARCH_BASELINE`; the baseline stays byte-for-byte intact and independently
reproducible, and `ml/baseline/baseline_manifest.json` records a hashed inventory that
proves it.

Everything here is driven by two environment variables and contains **no
developer-specific absolute path**:

```
FLOODSHIELD_DATA_ROOT   raw research inputs (default: ../flooddata)
FLOODSHIELD_ML_OUT      pipeline outputs    (default: <data_root>/corrected)
```

Check the resolution before running anything:

```bash
python ml/config.py
```

## Run order

| Step | Script | Phase | What it does |
|---|---|---|---|
| 1 | `p01_freeze_baseline.py` | 1 | Hashed inventory of the baseline: artifacts, splits, metrics, target definition. Writes only to `ml/baseline/`. |
| 2 | `p04_reconcile_labels.py` | 4, 5 | Builds the event provenance table over three documentary sources and assigns each candidate a decision. Writes `ml/labels/`. |
| 3 | `p05_complete_weather_fetch.py` | — | Completes the interrupted 11-parameter NASA POWER fetch (59 → 82 locations). Cached and idempotent. |
| 4 | `p06_build_dataset.py` | 6, 13 | Rebuilds the target and feature matrix; chronological split by global date. |
| 5 | `p10_experiments.py` | 8, 9, 10, 12, 13 | Baselines, feature ablation, model comparison. `--rolling` adds walk-forward validation. **Validation only.** |
| 6 | `p11_spatial_holdout.py` | 11 | Leave-one-province-out robustness. **Train + validation only.** |
| 7 | `p15_finalize.py` | 12, 15, 16, 21 | Selects on validation against declared gates, calibrates on validation, picks a threshold against an alert budget, exports the artifact. |
| 8 | `p20_final_evaluation.py` | 18, 20, 23, 24 | **The only script that reads `test.csv`.** Runs once, on a frozen pipeline. |

## The test set is locked

Only `p20_final_evaluation.py` opens `test.csv`. Every other script reads train and
validation. This is the direct remedy for the audit's central methodological finding:
the predecessor artifact `flood_risk_lr_v1` was selected by citing its **test** ROC-AUC
of 0.777, while on validation a different model ranked first. That contamination is
recorded in `ml/baseline/baseline_manifest.json` under
`baseline_metrics.selection_contamination_note` rather than quietly corrected.

## Three label states, not two

The baseline had positive and negative. The correction adds a third:

```
flood_next_7d = 1                     positive
flood_next_7d = 0, label_usable = 1   negative
label_usable = 0                      neither — excluded from training AND evaluation
```

A year-precision event previously made ~365 days *negative*, which contradicts the source
that documents a flood in that location-year. Those days are now excluded rather than
asserted. See `ml/labels/LABEL_PROVENANCE.md`.

## Declared before looking

Both selection criteria are in code, fixed before any result was inspected:

- **Selection** (`p15_finalize.py`): primary metric validation PR-AUC; the candidate must
  beat the best non-ML baseline's PR-AUC **and** reach recall ≥ 0.30; ties within 5%
  relative PR-AUC break toward fewer features and the simpler family. If nothing passes,
  the script exports nothing and writes `selection_verdict.json` saying so.
- **Threshold** (Phase 16): maximum validation recall subject to ≤ 6 alerts per location
  per year. If no threshold meets that budget with non-zero recall, the script reports
  that the objective is unachievable rather than substituting a convenient value.

## Tests

```bash
python -m pytest ml/tests -q
```

| File | Asserts |
|---|---|
| `test_feature_parity.py` | The provider requests every contract feature and no substitute; training and inference produce identical feature vectors on real historical observations; the daily-mean substitution and a max/min swap are both refused. |
| `test_target_and_leakage.py` | Horizon is strictly `(t, t+7]`; multi-day, overlapping and duplicate events behave consistently; rainfall windows are backward-looking (with a guard that a forward-shifted window *fails* the check); splits are date-disjoint; masked rows are in neither class; nothing was imputed. |
| `test_physical_scenarios.py` | Physical invariants (more rain never lowers the score; calibration is monotonic), plus characterisation tests that pin the known implausible behaviour so it cannot silently vanish or silently persist. |

## Feature contract

`ml/contracts/feature_contract.json` binds every model input to one physical definition.
Two production defects it closes:

- `T2M_MAX` / `T2M_MIN` were not fetched, and the inference path passed the daily **mean**
  for both. Measured effect on the locked test split: mean predicted probability
  0.491 → 0.243, alert decision flipped on **49.8%** of rows.
- `WS2M` (2 m wind) was supplied where the model expects `WS10M` (10 m wind) — different
  physical variables, differing by roughly 25–40%.

Both are now requested explicitly, stored in `weather_observations`, and enforced by
`predict_risk`, which refuses a degenerate `max == mean == min` triple outright.
