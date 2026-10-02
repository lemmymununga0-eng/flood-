# Current State — 1 October 2026

Single source of truth for what this system actually is today. Where any other document
in `docs/` disagrees with this one, this one is correct — the dated audit reports and
`PROJECT-MEMORY.md` are historical records of what was true when they were written and
have deliberately not been rewritten.

Every figure below was produced by running the thing described, not by reading code.

## The headline result

**A correctly-built pipeline showed that daily reanalysis weather cannot predict Zambian
district-level flood events beyond knowing the time of year.**

Across 25 model configurations on corrected labels, **no machine-learning model beat a
day-of-year seasonal climatology baseline that uses no weather data at all.** The formal
deployment gate returned `DO_NOT_DEPLOY` (2 of 5 pre-declared criteria passed) and
exported nothing.

This is a valid negative result, not a failure to finish. The limiting factor is
**flood-label completeness**, not model capacity — the higher-capacity models performed
worse, not better.

## Evidence for that claim

| Experiment | Design | Result |
|---|---|---|
| Fixed-split ablation | 5 model families × 5 feature sets, validation only | Best model PR-AUC 0.00300 vs baseline **0.00336** |
| Rolling-origin | 15 annual folds, all 82 districts | Best candidate averages **0.755×** the baseline; max win rate 4/15 folds |
| Spatio-temporal holdout | 10 provinces, unseen district **and** unseen future | Weather's isolated contribution over climatology-as-a-feature: **−5% to +10%**, ~50% win rate |

The decisive test gave a model the climatology score *as an input feature*, so any gain
would be incremental skill by construction. There was none that survived rolling
validation.

**A cautionary result worth reporting:** on the single fixed split, one configuration
(`DecisionTree / climatology+weather`) scored **+94.8%** over the control — by far the most
promising number the project produced. Under 15 rolling folds that same configuration won
**1 fold**, averaging 0.649×. Stopping at the fixed split would have shipped a model with
no skill.

## Data

| | |
|---|---|
| Weather | NASA POWER / MERRA-2 reanalysis, **1,099,374 rows**, **82 districts**, 1990-01-01 → 2026-09-15 |
| Flood labels | DesInventar (UNDRR), Dartmouth Flood Observatory, and a hand-compiled DMMU/WARMA/ReliefWeb/International-Charter log |
| Label reconciliation | 472 candidate events → **337 positive intervals** (was 277) |
| Third label state | 163 year-precision location-years moved from *negative* to **excluded from both classes** — the baseline asserted "no flood" where a source documents one |

Known gaps, stated plainly: 1990–1997, 1999, 2018, 2019 and 2024 still contain no
documented district-level Zambian flood events. Those years' negatives remain unverified.

## The served model

`flood_risk_lr_v1` — Logistic Regression, 6 weather features, sigmoid-calibrated,
threshold 0.50.

**It is served, and it ranks 14th of 25 in the corrected study.** Its registered metrics
record both its original numbers and the finding that qualifies them.

Two provenance facts that must not be dropped when citing it:

1. Its original test ROC-AUC of **0.777 was obtained by selecting on the test set**. On
   validation a different model ranked first. Treat 0.777 as in-sample.
2. Its fitted weights are humidity **+2.003**, max temperature **+1.445**, rainfall
   **+0.018**. Run end-to-end, a dry humid day scores HIGH while 200 mm of rain in dry
   air scores LOW.

**Intended use: research and teaching only.** This must not issue public or institutional
flood warnings.

## What is built and working

| Layer | State |
|---|---|
| Backend | FastAPI, 27 routes, boots clean; Alembic at `b4c1a7e92f30` |
| Database | PostgreSQL, 13 tables — 85 locations, 935 weather observations, 14 flood events, 85 predictions, 1 model version |
| Inference | `POST /api/v1/predictions/predict` returns a real score with target window, contract version and explicit caveats |
| Frontend | React 18 + Vite + Leaflet, 23 routes, all rendering real data, zero console errors |
| Dev wiring | vite proxies `/api` to the backend, so the app works from localhost, 127.0.0.1 and any LAN address without CORS configuration |

### Tests

| Suite | Count | Status |
|---|---|---|
| ML pipeline (`ml/tests`) | 37 | **passing** |
| Frontend (`frontend/tests`) | 11 | **passing** |
| Backend (`backend/tests`) | 57 | **written but NOT EXECUTED** |

The backend suite requires a local PostgreSQL `floodshield_zambia_test`. There is no
Postgres and no Docker on the development machine, so it has never been run here and
**no pass count is claimed for it.** Backend changes were instead verified by targeted
live requests, recorded per-fix in `docs/SYSTEM-FIX-PASS-2026-10-01.md`.

## The feature contract

`ml/contracts/feature_contract.json` binds every model input to one physical definition.
It exists because production was silently scoring a different feature vector than
training produced:

- `T2M_MAX` / `T2M_MIN` were never fetched; inference passed the daily **mean** for both.
  Measured effect on the locked test split: the alert decision flipped on **49.8% of rows**.
- `WS2M` (2 m wind) was supplied where the model expects `WS10M` (10 m wind).

Both are closed at source, and `predict_risk` now refuses a degenerate
`max == mean == min` triple rather than scoring it.

## Honest limitations

1. **The labels are incomplete.** Nine independently documented floods were negatives in
   the predecessor dataset. Several years still contain no events at all.
2. **There is no forecast capability.** The system predicts seven days ahead using NASA
   POWER weather that lags 2–3 days. The deployed horizon is fictional until forecast
   meteorology is added.
3. **Precision is unusable for alerting.** At the documented operating point, roughly one
   false alarm per district every two days.
4. **Spatial resolution is too coarse** for urban flooding — a ~55 km reanalysis cell
   cannot resolve a storm over a Lusaka settlement.
5. **No scheduler.** Predictions are generated by a manual script run, not automatically.
6. **The backend test suite has never been executed** on this machine.

## Running it

```bash
# backend — port 8001, because 8000 is occupied by an unrelated service on this machine
cd backend && python -m uvicorn app.main:app --reload --port 8001

# frontend
cd frontend && npm run dev
```

## Where to look next

| Question | Document |
|---|---|
| How were the labels built, and what was excluded? | `ml/labels/LABEL_PROVENANCE.md` |
| How do I re-run the corrected pipeline? | `ml/README.md` |
| What code defects were fixed, and how were they verified? | `docs/SYSTEM-FIX-PASS-2026-10-01.md` |
| What did the system look like earlier? | `docs/AUDIT-REPORT-2026-09-*.md`, `docs/PROJECT-MEMORY.md` (historical, not current) |
