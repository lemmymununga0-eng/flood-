# Known Limitations — FloodShield Zambia

Status: updated 2026-10-01. The sections below are kept as a dated record of how the
project's understanding of its own limits developed — the 2026-09-07 list was written
before any data existed and is **no longer current**. For the limitations that apply
today, read the next section first; `docs/CURRENT-STATE-2026-10-01.md` is the single
source of truth.

## Current limitations (2026-10-01)

1. **The flood labels are incomplete, and this is the binding constraint.** Nine
   independently documented floods were negatives in the predecessor dataset.
   1990-1997, 1999, 2018, 2019 and 2024 still contain no documented district-level
   Zambian events, so those years' negatives remain unverified.
2. **The model shows no skill beyond seasonality.** Across 25 configurations, 15
   rolling-origin folds and 10 spatio-temporal folds, nothing beat a day-of-year
   climatology. Formal verdict: `DO_NOT_DEPLOY`, 2 of 5 criteria passed.
3. **There is no forecast capability.** The system predicts seven days ahead from NASA
   POWER weather that lags 2-3 days, so the deployed horizon is fictional until forecast
   meteorology is added.
4. **Precision is unusable for alerting** - roughly one false alarm per district every
   two days at the documented operating point.
5. **Spatial resolution is too coarse for urban flooding.** A ~55 km reanalysis cell
   cannot resolve a storm over a Lusaka settlement.
6. **No scheduler.** Predictions come from a manual script run.
7. **The 57-test backend suite has never been executed** - it needs a local PostgreSQL
   that this machine does not have. No pass count is claimed for it anywhere.
8. **Flood mechanisms are pooled.** Pluvial, riverine and one dam-spillway failure share
   a single target.

## Superseded: limitations as understood on 2026-09-07 (historical)

- **No data has been ingested yet.** Every downstream claim about dataset availability,
  quality, or coverage in this project is currently unverified.
- **Flood-event ground truth for Zambia is now partial, not absent.** A first
  hand-compiled log of 11 real, sourced flood events (2020–2025/26) exists at
  `ai-engine/data/external/zambia_flood_events_log.csv`, but it is media-derived (not a
  primary government dataset), has no negative (non-flood-period) examples yet, and 11
  events is a small sample for training a classifier — class imbalance and overfitting
  risk will need explicit handling (see `docs/ML-METHODOLOGY.md`, XGBoost section) and
  the eventual model's confidence intervals should be reported honestly wide. The
  project may still end up supplementing this with a documented rainfall-accumulation
  proxy for negative-class construction; if so, that proxy portion of the label is a
  materially weaker claim than "observed flooding" and must always be labelled as such
  in every document, API response, and UI surface.
- **No model has been trained.** No accuracy, precision, recall, F1, ROC-AUC, or PR-AUC
  figures exist. Any number resembling a metric anywhere in this repository before
  Phase 7 is a documentation error, not a result.
- **Prediction horizon is undetermined.** It depends on the temporal resolution of
  whichever historical source is selected (most public reanalysis/meteorological
  datasets are daily) and cannot be assumed to be hourly or sub-daily until tested.
- **Geographic scope is undecided.** Named Zambian locations in the governing prompt
  (Lusaka, Kanyama, Misisi, etc.) are candidate examples, not confirmed monitored areas.

## Structural limitations expected to persist

- **No physical sensors.** The system depends entirely on external meteorological data
  sources and their coverage/latency/accuracy for the Zambian region, which may be
  coarser than ground-based instrumentation would provide.
- **Decision-support only.** This system does not and will not claim guaranteed
  prediction, guaranteed evacuation outcomes, or official government warning status
  unless a competent authority formally adopts it.
- **Free/low-cost infrastructure constraint.** Hosting, database, and API choices are
  constrained to free or student-accessible tiers, which may limit uptime, storage, or
  request-rate compared to a funded operational deployment.

This document must be updated (not just appended to indefinitely — condense as it grows)
at the end of every phase with what was actually learned.

## Update (2026-09-08): the real-event limitation, made precise

The "11 events is a small sample" caveat above is now measured, not just anticipated. Three real
bugs blocking the historical-event log from loading at all were found and fixed this phase
(`docs/bug-register.md` BUG-12/14/15). With them fixed, the real, concrete finding is:

**All 11 recorded events occurred in 2020 or later, so this project's own chronologically-split
train set (2000-2016, using the only weather data ever trained against) contains zero of them.**
7 fall in the validation split, 45 (all from one multi-day event) in the test split — verified by
actually running the fixed ingestor against the real date range, not estimated. A model cannot be
validly trained to recognize a pattern its training data never contains an example of. This is
now the single most consequential open limitation in the project, ahead of the sample-size
concern already noted above — it is a *coverage* problem (when the events happened), not merely a
*count* problem (how many). See `docs/ML-METHODOLOGY.md`'s corresponding update for the two
possible paths forward (more/older event records, or a non-chronological validation strategy),
neither implemented yet.

## Update (2026-09-09): the coverage gap was closed, and a real model was trained — new limitations replace the old one

Three real pre-2020 events were added (now 14 total), giving the training split 243 real positive
days (was 0). NASA POWER — previously blocked only by a sandbox's egress policy — was confirmed
reachable from the real developer machine, so the first-ever real-weather, real-label, non-leaked
training run in this project actually happened (`docs/ML-METHODOLOGY.md`'s corresponding update
has the full results table). This resolves the specific limitation described above. It does not
mean the ML pipeline is now limitation-free — it has new, different, real ones:

- **Single monitoring point.** The real weather data pulled is for Lusaka only; the real flood
  events span many provinces. The model is effectively learning "does Lusaka's weather correlate
  with a flood being reported anywhere in Zambia," not location-specific risk — a genuine
  geographic-mismatch limitation, not fixed by this update.
- **Coarse, national-level label.** "A flood was reported somewhere in the country this day" is a
  much weaker signal than "flooding is occurring at this specific monitored location," which is
  what the application's per-`Location` prediction architecture implies it will eventually serve.
- **Small effective test set.** 45 of the real test-set positive days come almost entirely from a
  single event (`ZM-2023-01`). Precision/recall on this test set are therefore noisy indicators of
  one event's detectability, not a robust estimate across many independent flood instances — with
  only 14 source events total, this is a hard statistical-power ceiling, not a methodology error.
- **No class-imbalance handling yet.** With ~3.4% positive days, the tree-ensemble baselines
  (Random Forest, Gradient Boosting) collapsed toward predicting the majority class. This is an
  honest, unfixed limitation of the current run, not evidence the underlying signal doesn't exist
  (Logistic Regression's ROC-AUC of 0.85 suggests it does).
- **Still true, unaffected by this update:** XGBoost, LSTM, and SHAP remain blocked by the Python
  3.11 requirement; the proxy-label leakage issue (`docs/bug-register.md` BUG-13) is now moot for
  this specific run (real labels were used, not the proxy formula) but the leaky code path itself
  is still present and would still be a live risk in any future run that falls back to it.
