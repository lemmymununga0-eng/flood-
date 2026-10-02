# ML Methodology — FloodShield Zambia

Status: updated 2026-10-01. Models HAVE been trained and a corrected study completed;
its measured results are in `docs/MODEL-EVALUATION.md` and the headline is that no model
beat a seasonal climatology baseline (`DO_NOT_DEPLOY`). The methodology below is what
that study followed. Historical note: this began as a planning document, and figures in
its original form
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

## Update (2026-09-08): a concrete, measured finding on option 1's viability

This document's "Status: Phase 0/1 planning" framing above is stale — a real ai-engine pipeline
now exists and has actually run once (see `docs/AUDIT-REPORT-2026-09-08.md` Section 5), and three
real bugs preventing the historical-event log (option 1 above) from loading at all have since
been found and fixed (`docs/bug-register.md` BUG-12/14/15). Fixing them surfaces a more precise,
measured version of the "eleven events... small sample" caveat already noted above:

**All 11 real recorded events postdate 2020.** Paired with the only weather dataset this project
has ever trained against (`ai-engine/data/raw/synthetic_zambia_weather.csv`, 2000–2023) and this
project's own chronological 70/15/15 train/val/test split (a deliberate, correct anti-leakage
choice — see "Data leakage controls" above), the actual measured positive-day distribution is:

```
train (2000-01-01 -> 2016-10-19): 0 positive days
val   (2016-10-19 -> 2020-05-26): 7 positive days
test  (2020-05-26 -> 2023-12-31): 45 positive days
```

**A model cannot learn what its training split never contains an example of.** This is not a
data-quality complaint about the 11 events themselves (their sourcing/confidence is unchanged and
still documented in `zambia_flood_events_log.csv`'s own README) — it's a coverage mismatch between
when the events happened and what a standard chronological split assumes. Two honest paths
forward for this project's methodology (neither implemented yet, both worth naming explicitly for
the eventual write-up):

1. **More historical event records reaching further back than 2020** — the real fix, if such
   records can be found (DMMU/WARMA archives, EM-DAT, older ReliefWeb/FloodList coverage).
2. **A validation strategy that doesn't require positives in a contiguous early block** — e.g.
   leave-one-event-out cross-validation, or stratifying the split to guarantee at least one real
   event lands in each fold — trading some chronological purity for having any real signal to
   learn from at all, and reporting that trade-off explicitly rather than hiding it.

Neither is implemented in this codebase yet. Continuing to train against proxy labels (option 6)
in the meantime is not a substitute for either — see `docs/LIMITATIONS.md`'s corresponding update
and `docs/bug-register.md` BUG-13 for why the current proxy-label implementation has its own,
separate, unresolved leakage problem.

## Update (2026-09-09): path 1 above was actually done — real training run, real results

Three pre-2020 events were researched and added to `zambia_flood_events_log.csv` (now 14 events,
2007-2026 — see that file's README for full sourcing), specifically chosen to give the training
split real positive examples. Verified by execution: this raised real positive days from 43 (all
in the test split) to 295, distributed 243 train / 7 validation / 45 test. Separately, NASA POWER —
previously blocked only by sandbox egress policy, not by anything wrong with this project's code —
was confirmed reachable from the actual developer machine (see `docs/DATA-SOURCES.md`'s 2026-09-09
update), so `main.py` was run for real, without `--use-synthetic`, for the first time in this
project's history.

**This is the first training run in this project using real weather data AND real, independent
flood-event labels — no synthetic data, no leaky proxy formula.**
`ai-engine/saved_models/model_metadata.json` records `"data_source": "nasa_power"`.

Real test-set results (`ai-engine/reports/baseline_comparison.csv`, experiment runs 005-008):

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Logistic Regression | 0.917 | 0.204 | 0.489 | 0.288 | 0.850 |
| Decision Tree | 0.903 | 0.082 | 0.178 | 0.112 | 0.553 |
| Random Forest | 0.952 | 0.050 | 0.022 | 0.031 | 0.790 |
| Gradient Boosting | 0.966 | 0.000 | 0.000 | 0.000 | 0.581 |

**How to read these, honestly:**
- These are real, modest, non-leaked numbers for a genuinely hard problem — not the suspiciously
  strong metrics the old proxy-label run produced (which measured formula reconstruction, not
  flood prediction; see `docs/bug-register.md` BUG-13). Logistic Regression's ROC-AUC of 0.85 with
  49% recall is a plausible real signal, not a fabricated one.
- **The test set's 45 positive days come almost entirely from one event** (`ZM-2023-01`, a 43-day
  block) plus 2 days from elsewhere. A model doing well on this test set is substantially being
  scored on whether it can flag one contiguous block, not on generalizing across many independent
  flood instances — a real statistical-power limit from having only 14 source events, not a flaw
  in this run's execution.
- **The label is a national/coarse one** — "a flood was reported somewhere in Zambia this day" —
  trained against **one point's** weather (Lusaka), regardless of which province the reported
  event was actually in. This is a real geographic mismatch: the model is learning "does Lusaka's
  local weather correlate with a flood being reported anywhere in the country," not "does local
  weather predict local flooding" — a materially weaker claim than the per-location prediction the
  application's own architecture (`Location`-scoped predictions) implies. Multi-location ingestion
  (`NASAPowerIngestor.download_multiple_locations()` already exists for this) paired with
  per-location event attribution is the natural next step, not yet done.
- **The tree ensembles (Random Forest, Gradient Boosting) essentially collapsed to predicting the
  majority class** (near-zero recall/F1 despite high accuracy — accuracy is a misleading metric
  here given ~3.4% positive class). This is an honest, real finding about class-imbalance
  handling, not a bug: none of these models currently use `class_weight="balanced"`, resampling
  (SMOTE/undersampling), or a tuned decision threshold — all legitimate next steps for a follow-up
  run.
- XGBoost, LSTM, and SHAP remain unexercised — still blocked by the Python 3.11 requirement
  (`docs/technical-debt.md` TD-12), unrelated to this update.

This does not mean the model is "done" or ready to back a real prediction — it means this project
now has, for the first time, a real, honestly-reported baseline result to improve on, instead of
either a fabricated number or an admitted total absence of one.
