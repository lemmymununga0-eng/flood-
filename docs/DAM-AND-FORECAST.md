# Seven-day outlook and Dam / Reservoir Monitoring

Both features are additive. The production model (`backend/ml_artifacts/flood_risk_lr_v1`), `app/ml/predictor.py`,
`POST /predictions/predict`, the feature contract and the risk bands are unchanged.

## 1. Seven-day outlook

**Original problem.** There was no seven-day display to repair. The model scores one observation and returns one
probability for the window (t, t+7]; no weather-forecast provider exists (`docs/LIMITATIONS.md` item 3). The
requested per-day flood predictions are therefore not scientifically supported by the current model.

**What was built.** `GET /api/v1/forecast/outlook?location_id=` (read-only) and the "Seven-day outlook" section on
the Predictions page.

- Seven consecutive, unique dates generated at runtime in `Africa/Lusaka`.
- Convention: **Day 1 = tomorrow**, matching the model's own window start (t+1).
- Each card shows day number, weekday and date. If the latest *stored* prediction's window covers that date, the card
  shows its risk level labelled "window-level estimate (not specific to this day)". Otherwise "No model risk".
- `daily_flood_prediction` and `weather_forecast` are always `null` (`weather_forecast_status: unavailable_no_provider`).
- Status: `no_prediction | window_outside_outlook | partial | complete`; `stale` when the prediction's weather is more
  than 3 days old or its window has passed. Generation timestamp is displayed in Lusaka time.

**Refreshing the prediction.** The outlook only shows what is stored, so it goes stale (the stored prediction was
computed from old weather). `POST /api/v1/forecast/outlook/refresh?location_id=` (ADMIN/ANALYST/OPERATOR; the
"Refresh from latest weather" button) fetches real NASA POWER weather, stores new observations, scores the newest
complete day with the unchanged model, marks the previous prediction stale and returns the new outlook. NASA POWER lags
about 3 days, so the new window (t, t+7] covers roughly Day 1 to Day 4: the outlook then shows status `partial`, which is
the honest extent of the model's coverage. If the provider fails or returns no complete day, nothing is stored (HTTP 502).

To obtain real per-day weather, integrate a forecast provider as a separate, labelled data source. Running the model on
forecast weather would be a distribution shift from its reanalysis training data and needs separate evaluation.

## 2. Dam and reservoir monitoring

Routes (`/api/v1`): `GET /dams`, `GET /dams/{slug}`, `GET /dams/{slug}/assessment`,
`POST /dams/{slug}/import?data_kind=historical|manual_import|synthetic_test` (ADMIN/ANALYST, body = CSV, `Content-Type: text/csv`).
Pages: `/dams`, `/dams/:slug` (nav: "Dam Monitoring").

**Migration** `e1a4b7c93d68` (down_revision `d8e3f6a92b57`): creates `dams`, `dam_observations`, `dam_release_notices`
and seeds Kariba (Zambezi) and Itezhi-Tezhi (Kafue) with **identity fields only**. Coordinates, capacity, district,
province and provider are NULL and flagged `verification_required`. No existing table is altered; downgrade drops only
the three new tables.

**Observations.** Every measurement is nullable (NULL = not measured, never zero). `observed_at` is stored apart from
`retrieved_at`; `data_kind` (live / historical / manual_import / synthetic_test), provider, source reference and quality
flag are mandatory. Duplicates `(dam, observed_at, provider)` are skipped; nothing is overwritten.

**CSV format.** Header must include `observed_at` (ISO 8601 **with offset**). Optional columns: `source_published_at`,
`provider`*, `source_reference`*, `quality_flag` (good|suspect|estimated|unverified), and any of
`reservoir_level_m, storage_m3, storage_pct, inflow_m3s, outflow_m3s, spillway_m3s, turbine_m3s, downstream_level_m,
downstream_discharge_m3s, rainfall_observed_mm, rainfall_forecast_mm` (* required). Blank cell = missing. Range checks
reject only physically impossible values; they are not operating thresholds. Import is all-or-nothing: any invalid row
rejects the file. `live` imports are refused: no live feed exists. Synthetic data never changes a dam's `data_status`
and is excluded from assessments.

**Data-source status (verified in `data/raw/hydrology/README.md`, not re-verified online in this work).** No public
live API was found for WARMA, ZRA or ZESCO. ZRA publishes PDF press statements; WARMA data is by institutional request.
**No live official integration is operational.** Provide validated CSVs obtained through those bodies to populate dams.

**Assessment** (`dam_assessment.py`, experimental, never creates alerts). Statuses: Insufficient data / Monitoring /
Elevated concern based on documented conditions / Official release notice available. No "% full" rule exists. A rise in
reservoir level, inflow or downstream level is a signal only if its 7-day change exceeds the 90th percentile of that
dam's own history (≥ 30 comparisons required); a reported spillway discharge is a fourth signal. Two or more signals ⇒
"elevated concern". Stale or absent data returns exactly: *"Insufficient hydrological data to assess dam-related flood
risk."* No downstream arrival times or affected areas are computed. The map shows markers only for verified
coordinates (currently none, so no markers).

The p90 / 30-sample / 48 h freshness / 3-day staleness values are documented engineering choices, not validated
hydrological standards.

## 3. Tests

```
cd backend
python -m pytest --noconftest tests/pure -q      # no database needed (SQLite for the API layer only)
cd ../frontend && npm test && npx tsc --noEmit && npm run build
```

Results at the time of writing (against a throwaway PostgreSQL 16.4 started from the EnterpriseDB binaries):

- Full backend suite (`python -m pytest -q`, includes `tests/pure`): **183 passed**.
- `tests/pure` alone with `--noconftest`: 36 passed. Frontend: 13 passed; `tsc` clean; build succeeds.
- Migrations: `alembic upgrade head` from an empty database succeeded; seeded dams have NULL coordinates and capacity;
  `downgrade d8e3f6a92b57` removed only the three dam tables; re-upgrade succeeded.
- A pre-change run of the original suite was not possible (no database existed then), so the pre-change baseline for
  the DB-backed tests is not recorded. The model-level baseline (artifact hashes and fixed-input outputs) was.

`tests/pure/prediction_baseline.json` holds the artifact SHA-256 hashes and outputs for three fixed inputs, recorded
before any change; `test_prediction_protection.py` fails if either differs. The migration has not been applied to any
development or production database.

## 4. Remaining work

- Verified coordinates, capacities, districts, provinces and data providers for each dam.
- A real data feed or formal data-sharing agreement; a weather-forecast provider if per-day weather is wanted.
- Kafue Gorge dams (add via a new `dams` row once data is available).
- Any per-day or dam-aware prediction requires a new, separately evaluated model version with its own artifacts.
