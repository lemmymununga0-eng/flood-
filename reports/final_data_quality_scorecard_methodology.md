# Final data-quality scorecard — scoring methodology

Scores in `reports/final_data_quality_scorecard.csv` are produced by `scripts/build_quality_scorecard.py`; nothing is set by hand.

```
Build reports/final_data_quality_scorecard.csv with a DEFINED, reproducible scoring method.

Scores (0-1, two decimals) — computed from files and audit results, never set by hand:
  spatial_score      share of the 101 districts the dataset can be joined to (1.0 for national/basin indices,
                     which apply to every district by definition)
  temporal_score     share of the required daily window 1999-04-14..2026-01-30 covered at the dataset's
                     native resolution; time-invariant data = 1.0; a single snapshot taken outside most of
                     the window = 0.5 (anachronism); not collected = 0
  coverage_score     spatial_score x temporal_score
  completeness_score 1 - share of missing values in the collected series/table (not collected = 0)
  quality_score      share of this dataset's checks that PASS in the second independent audit
                     (WARN counts as half); datasets without audit checks use the first-pass validator status
                     (COMPLETE = 1, otherwise 0)
Categorical:
  forecast_relevance HIGH = direct short-term flood driver or hydrological state (rainfall, discharge, runoff);
                     MEDIUM = modulates flood response (soil wetness, terrain/drainage, floodplain occurrence,
                     climate state); LOW = context or exposure; LABEL = defines the target
  leakage_risk       from reports/variable_leakage_register.csv: HIGH if the dataset holds POST-EVENT
                     variables, MEDIUM if POTENTIAL LEAKAGE (needs lag/anachronism rule), LOW otherwise
  role / final_decision  the Stage 2 classification (CORE / OPTIONAL / VALIDATION / EXPOSURE / NOT COLLECTED)
```
