# FloodShield-Zambia — Data Collection: Final Completion Report (Stage 2, double-verified)

Date: 2026-10-07. No model was trained, no target column (`flood_next_*`) was created, no ML dataset was built
(verified by the second audit: zero `flood_next_*` columns anywhere in `data/`). Every number below comes from
files on disk via the scripts listed in §24.

## 1. Executive summary

All datasets that can be obtained without the researcher's own credentials are collected, validated, audited
twice and documented. **GloFAS v4.0 historical hydrology was DEFERRED by the researcher's decision on 2026-10-08**
because no Copernicus EWDS credentials are available; its static river-network maps are collected and its download
and extraction pipeline is built, validated against the official request constraints and tested on synthetic input,
so it can be added later without redesign. The second independent audit ran 50 checks: **48 PASS, 2 WARN, 0 FAIL**
(WARNs: GloFAS deferred; soil-wetness quantisation). The most important data-quality finding is unchanged: only 91 of 444 DesInventar flood records
(82 distinct district-days) carry a high-confidence onset date.

## 2. Project forecasting objective

Estimate the probability that a flood starts at a Zambian district within the next *H* days, using only
information available at prediction date *t*. Primary horizon H+7; also H+1, H+3, H+14, H+30.

## 3. All datasets collected

| Dataset | Version | Coverage | Size on disk | Role |
|---|---|---|---|---|
| DesInventar Zambia | export of 2026-10-05 | 2,239 records; 444 flood | ZIP + extracted | Label source |
| Location master | from DesInventar geography | 101 districts / 10 provinces | 2 CSV | Spatial key |
| NASA POWER daily weather | API v2.10.0 | 101 points × 9,789 days (988,689 rows) | 101 JSON | CORE |
| CHIRPS v3.0 daily (final, rnl) | v3.0 | 9,789/9,789 days; 0.05° Zambia grid | 28 NetCDF | CORE |
| HydroSHEDS | v1 (data v1.1), HydroRIVERS v1.0, HydroBASINS v1c | Zambia subset | 4 ZIP + 4 subsets | CORE (static) |
| GloFAS v4 river-network static maps | JRC static maps v1.1.1 | 0.05° Zambia window | 3 global + 3 subsets | CORE support |
| NASA POWER soil wetness | API v2.10.0 | 101 points × 9,789 days | 101 JSON | OPTIONAL |
| ESA WorldCover | 2021 v200 | 17 tiles (40 m overview) | 17 GeoTIFF | OPTIONAL (static) |
| JRC Global Surface Water | v1.4 (2021) | 4 tiles, 30 m | 4 GeoTIFF | OPTIONAL (static) |
| Climate indices | ONI/Niño 3.4 (ERSST.v5), DMI (HadISST1.1), BoM IOD | 1870/1950 → 2026 | 4 text files | OPTIONAL (lagged) |
| WorldPop | unconstrained 1 km, not UN-adjusted (DOI 10.5258/SOTON/WP00670) | 2000–2020 | 21 GeoTIFF | EXPOSURE |

Total `data/` size: 2.4 GB. Full table with URLs, units and missing %: `docs/FINAL_DATA_INVENTORY.md`.

## 4. Datasets not collected

| Dataset | Status | Blocking? |
|---|---|---|
| **GloFAS v4.0 historical** (discharge, runoff, soil wetness) | **DEFERRED** by researcher decision 2026-10-08 — credentials not available | No — deferred; scripts ready to add later |
| GloFAS v4.0 reforecasts | Not collected — credentials required | No (optional forecast experiment) |
| GloFAS operational forecasts | Not collected — deployment only | No |
| DFO flood archive | Not collected — server unreachable throughout | No (optional validation) |
| GRDC river gauges | Not collected — request-only; portal unreachable | No (optional / data access limited) |
| ERA5 / ERA5-Land | Not collected — CDS account | No |
| TAMSAT, IMERG rainfall | Not collected — third rainfall source adds little (IMERG needs login) | No |
| ESA CCI / SMAP soil moisture | Not collected — coarse/short; covered by GloFAS SWI + POWER | No |
| NOAA GEFSv12 reforecasts | Not collected — GloFAS reforecasts preferred | No |
| GloFAS / ISRIC soil hydraulic maps | Not collected — static, partly captured by terrain/land cover | No |
| Sentinel-1, CEMS GFM, Global Flood Database | Not collected — post-event, account-gated | No (future validation) |

## 5. Why each missing dataset was not collected

- **GloFAS (all products):** EWDS requires a personal ECMWF account, acceptance of the CEMS-FLOODS licence and a
  personal access token in `~/.cdsapirc`. None exist on this machine; creating accounts or handling credentials is
  the researcher's action. Attempted: catalogue, forms and constraints read through the public API; a request
  without credentials stops cleanly (logged in `reports/failed_requests.csv`). Alternative: no official
  credential-free route exists for the time series; unofficial mirrors were deliberately not used.
- **DFO:** `floodobservatory.colorado.edu` refused connections on every attempt on 6–7 Oct while all other hosts
  worked. No official alternative copy.
- **GRDC:** data are released only through a request form with the requester's contact details; the portal was
  also unreachable. Gauges would cover only a few main-stem rivers.
- **Others:** judged against "what additional predictive information does this provide?" — see §4 and
  `docs/DATA_SOURCES.md` §13.

## 6. GloFAS assessment

| Item | Finding (official EWDS catalogue / constraints, read 2026-10-07) |
|---|---|
| Historical product | `cems-glofas-historical`, LISFLOOD forced by ERA5; v4.0 operational (1979 → 2026), v5.0 pre-operational (1980 → 2026) |
| Variables | `average_river_discharge_in_the_last_24_hours` (time_mean), `runoff_water_equivalent` (time_mean), `soil_wetness_index` (instantaneous, root zone); ancillary upstream area and elevation |
| Grid | 0.05°, WGS84, daily; consolidated (ERA5) vs intermediate (ERA5T) streams |
| Version chosen | v4.0 — operational and identical to the reforecast version |
| Spatial context | Area Zambia + 0.25°. Discharge is routed and already integrates upstream runoff (Angola, DRC), so cropping keeps the upstream signal |
| Extraction (decided with evidence) | Discharge at the district's **main-river cell** (largest upstream area), nearest significant river as sensitivity; runoff and soil wetness as **district means**. Centroid cells sit on a ≥1,000 km² river in only 9 % of districts (median 61 km² upstream) |
| Cross-check of the river network | GloFAS main-river upstream area vs independent HydroRIVERS: log-correlation 0.981; 95 % of districts within ×2; 5 boundary cases flagged |
| Readiness | `download_glofas.py` (84 historical requests validated against official constraints; resumable; provenance), `extract_glofas.py` (tested on a synthetic grid: exact pixel values reproduced; GRIB end-of-period timestamps re-labelled to the day described), second-audit check for runoff-vs-rainfall lag alignment |
| Expected volume | estimate, assuming 16-bit GRIB packing: ~38 MB per variable-year (52,576 cells × 365 days) ≈ 3.2 GB for 3 variables × 28 years; discharge alone ≈ 1.1 GB (actual sizes are recorded per file on download) |

## 7. Forecast-data assessment

| Category | Source | What it is | Use |
|---|---|---|---|
| A. Observed / reanalysis | NASA POWER, CHIRPS, soil wetness, GloFAS historical | "What happened" up to day *t* | Features for days ≤ t only |
| B. Forecasts (operational) | GloFAS forecast (2019-11 →), 30 days, ensemble; version changes across the archive | Deployment | Not for training |
| C. Reforecasts | GloFAS v4.0 reforecast, issues 2003-03 → 2023-11 twice weekly, leads 1–46 d, 11 members | Honest historical forecast experiment | Use the latest issue ≤ *t*; never mix with reanalysis after *t* |
| D. Future operational | GloFAS forecast feed | Real-time system | Stage 4+ |

A model trained on reanalysis is an upper bound on real-time skill (it sees analysed, not forecast, rain); the
reforecast experiment is the defensible test of forecasting.

## 8. Spatial coverage

101/101 districts and all 10 provinces; every coordinate lies inside Zambia and inside a polygon carrying its own
district code; no duplicate IDs or coordinates; province of every district agrees with the raw DesInventar
geography (second audit). Two boundary-file code conflicts (Mulobezi, Chikankanta) are documented, not guessed.
Every dataset joins to all 101 districts except the national climate indices (same value everywhere).

## 9. Temporal coverage

| Dataset | Start | End | Resolution |
|---|---|---|---|
| DesInventar exact-day events | 2000-04-13 | 2026-01-23 | day (no exact-day records 2002, 2003, 2005, 2018–2021, 2024) |
| NASA POWER, CHIRPS, soil wetness | 1999-04-14 | 2026-01-30 | daily, no gaps |
| GloFAS historical (product) | 1979 | 2026-10-04 | daily (not collected) |
| GloFAS reforecast v4.0 (product) | 2003-03 | 2023-11 | twice-weekly issues |
| HydroSHEDS, GloFAS static | static | static | — |
| WorldCover / Global Surface Water | 2021 / 1984–2021 | — | snapshot / aggregate |
| WorldPop | 2000 | 2020 | yearly |
| ONI, Niño 3.4, DMI | 1950 / 1950 / 1870 | 2026-08 / 2026-06 / 2026-05 | monthly |

1. **Longest common period (core weather):** 1999-04-14 → 2026-01-30.
2. **Usable for historical training:** 2000–2017 holds 73 of the 82 high-confidence district-days (9 more in
   2022–2026); weather covers all of them with ≥ 365 days of history (81 of 82).
3. **Usable for forecast/reforecast experiments:** 2003-03 → 2023-11 (GloFAS v4.0 reforecasts), containing 71
   high-confidence district-days — once credentials allow the download.

## 10. Data-quality results

Second independent audit (`reports/second_audit_report.md`): 50 checks, 48 PASS, 2 WARN, 0 FAIL. Highlights:
DesInventar re-parsed from the original ZIP with a different parser — all 17 checked fields of all 444 flood
records identical; every NASA POWER and soil value in the CSVs equals the raw JSON; CHIRPS point series recomputed
from the NetCDFs match exactly and 5 random location-days re-read from the official CHC servers differ by
0.000000; HydroSHEDS and GloFAS subsets identical to the original windows; 239 raw files match their recorded
SHA-256; no duplicate files; every raw folder documented; empty CSVs are only empty sections of the official
DesInventar export.

## 11. Missing-data results

NASA POWER 0 % missing; CHIRPS 0 missing days, 0 missing pixels, 0 negatives; soil wetness 0 %; terrain,
land-cover and surface-water district tables complete for 101 districts; WorldPop complete 2000–2020.
DesInventar: 168 flood records without an exact day; 4 province-only. Missing-value reports:
`reports/missing_data_report.csv`.

## 12. Outlier results

- NASA POWER 338 mm (Mwinilunga 2020-02-23) and 304 mm (Siavonga 2023-12-22): CHIRPS 10.8 / 29.5 mm at the same
  points → probable reanalysis artefacts; retained and flagged.
- CHIRPS grid maxima 402 mm (2009-04-02) and 336 mm (2022-04-27): identical to the official files and pentad
  totals, located outside Zambia, affect no district series → retained and flagged.
- Soil wetness (WARN): POWER publishes 2-decimal values; GWETPROF has ~42 distinct values per district and
  plateaus up to ~200 days → limited information content (`data/quality_flags/soil_wetness_timeseries_flags.csv`).
- NASA POWER temperature: no constant runs or day-to-day jumps > 15 °C.

## 13. Cross-dataset validation

| Comparison | Result | Meaning |
|---|---|---|
| NASA POWER vs CHIRPS rainfall | monthly r 0.90, daily r 0.52, mean bias +0.20 mm/day; agree on ~4 % of heavy days | same seasonal regime; differ day to day |
| POWER vs CHIRPS lag correlation | peak at lag 0 (0.51 vs 0.44/0.46 at ±1) | no date shift between sources |
| GloFAS river network vs HydroRIVERS | log-r 0.981; 95 % within ×2 | river geometry consistent |
| GloFAS upstream area vs published basins | Zambezi at Victoria Falls 517,768 vs ~507,000 km²; Kafue 152,789 vs ~155,000 km² | grid and units correct |
| Global Surface Water vs WorldCover permanent water | Spearman 0.927 | independent sensors/years agree |
| Soil wetness vs antecedent rainfall | Spearman 0.83–0.90 (30–90 days) | largely redundant |
| Flood dates vs rainfall | 7-day rain before HIGH-confidence dates at the 73rd wet-season percentile vs 4th for UNLIKELY dates | date-reliability flags are meaningful |
| WorldCover 40 m overview vs 10 m | ≤ 0.52 percentage points at 6 sites | reading method sound |

## 14. Flood-event reliability

Per-record audit: `data/processed/desinventar_flood_event_audit.csv` (444 rows): date confidence
(HIGH 91 / UNCERTAIN 102 / UNLIKELY 83 / NO EXACT DATE 168), location confidence (district code 439, own
coordinates 1, province only 4), flood evidence in the text (explicit 201, rain/water 214, category only 29).
Uncertain, unlikely and undated records must not become negatives; absence of a record is not evidence of no flood.

## 15. Leakage assessment

`reports/variable_leakage_register.csv` classifies all 475 columns of every collected table (plus one placeholder row
for the uncollected DFO table), read from the actual headers: POST-EVENT 244, NOT A PREDICTOR 146, STATIC ENVIRONMENTAL 55, POTENTIAL LEAKAGE 13, HISTORICAL
OBSERVATION 11, EXPOSURE ONLY 4, FORECAST VARIABLE 2. Prohibited as predictors: deaths, injuries, affected people,
houses, infrastructure and economic losses, relief/response, assessment and repair text, declarations, duration/end
dates, post-event flood extent, and the location master's flood counts (they include future events). Rules:
weather/hydrology only for days ≤ t; ONI ≤ season centred on month(t) − 2; Niño 3.4/DMI ≤ month(t) − 1;
forecasts only if issued ≤ t. Second audit: no target columns and no consequence columns outside DesInventar
tables; population only in the exposure folder.

## 16. Forecast-horizon readiness

| Horizon | High-confidence district-days | + uncertain | Assessment |
|---|---:|---:|---|
| H+1 | 82 | 166 | not defensible — day-level date errors dominate |
| H+3 | 82 | 166 | possible but fragile |
| H+7 | 82 | 166 | **primary — supported** |
| H+14 | 82 | 166 | supported |
| H+30 | 82 | 166 | supported as seasonal-risk horizon |

Predictors exist for every possible prediction date; the binding constraint is the number of reliable event
dates (`reports/forecast_horizon_readiness.md`).

## 17. Core datasets

DesInventar (labels), NASA POWER weather, CHIRPS rainfall, HydroSHEDS terrain/hydrology, GloFAS river-network
static maps. GloFAS historical hydrology: **deferred** (researcher decision 2026-10-08).

## 18. Optional datasets

NASA POWER soil wetness, ESA WorldCover 2021, JRC Global Surface Water occurrence, climate indices (lagged);
GloFAS reforecasts (forecast experiment) deferred with GloFAS historical.

## 19. Validation datasets

DFO archive and GRDC gauges (not obtainable); satellite flood extent (future work). Internal validation evidence
is in place (cross-dataset checks §13).

## 20. Exposure datasets

WorldPop 2000–2020 → `data/processed/exposure/worldpop_district_exposure.csv` (location_id, population_year,
population, population_density_per_km2, source, version with DOI). Never an occurrence predictor.

## 21. Known limitations

DesInventar date reliability and uneven reporting; district-point weather in large districts; coarse POWER grid
(8 groups of districts share a cell); CHIRPS daily timing comes from ERA5 disaggregation; WorldCover and Global
Surface Water are post-period static layers; soil wetness quantised; no observed river data; GloFAS outstanding.

## 22. Remaining risks

1. Too few reliable events for short horizons (82 high-confidence district-days).
2. GloFAS access depends on the researcher's account; download volume ≈ 1–3 GB over a slow, unstable link.
3. Reanalysis-trained models overstate real-time skill unless tested on reforecasts.
4. Two rainfall sources partly duplicate the seasonal signal.

## 23. Exact files produced

- Processed: `data/processed/{location_master.csv, unresolved_locations.csv, collection_window.json,
  desinventar_flood_events.csv, desinventar_flood_event_audit.csv, desinventar_flood_date_reliability.csv,
  chirps_daily_at_locations.csv, district_terrain_hydrology.csv, district_landcover.csv,
  climate_indices_monthly.csv, climate_iod_weekly_bom.csv, derived_rasters/slope_15s_zambia.tif,
  environmental/district_surface_water.csv, hydrology/glofas_district_extraction_points.csv,
  exposure/worldpop_district_exposure.csv}`; NASA POWER CSVs in `data/raw/nasa_power/`.
- Quality flags: `data/quality_flags/{nasa_power_timeseries_flags.csv, soil_wetness_timeseries_flags.csv,
  glofas_extraction_point_flags.csv}`.
- Reports (`reports/`): second_audit_report.md / second_audit_checks.csv, final_data_quality_scorecard.csv (+
  _methodology.md), variable_leakage_register.csv, forecast_horizon_readiness.md/.csv,
  glofas_extraction_method_comparison.md, flood_date_reliability.md, chirps_validation_report.md (+ per-year,
  extremes, annual totals, POWER comparison CSVs), environmental_data_validation_report.md,
  nasa_power_anomaly_investigation.md, worldcover_overview_bias_test.csv, validation_report.md, data_inventory.csv,
  raw_checksums.csv, failed_requests.csv, collection.log.
- Docs (`docs/`): DATA_COLLECTION_FINAL_COMPLETION_REPORT.md (this), FINAL_DATA_INVENTORY.md,
  DATA_REQUIREMENTS_MATRIX.md, DATA_AUDIT_REPORT.md, METHODOLOGICAL_DATA_DECISIONS.md, DATA_SOURCES.md,
  DATA_DICTIONARY.md, DATA_COLLECTION_COMPLETION_REPORT.md (earlier gate), DATA_COLLECTION_REPORT.md (Stage 1).

## 24. Exact scripts produced

Collection: `collect_desinventar.py`, `build_location_master.py`, `download_nasa_power.py` (`--dataset soil`),
`download_chirps.py`, `download_hydrosheds.py`, `download_worldcover.py`, `download_worldpop.py`,
`download_climate_indices.py`, `download_flood_observations.py`, `download_glofas_static.py`,
`download_glofas.py`, `download_global_surface_water.py`. Extraction: `extract_district_environment.py`,
`build_glofas_extraction_points.py`, `extract_glofas.py`. Validation/audit: `validate_raw_data.py`,
`validate_chirps.py`, `validate_environmental_data.py`, `test_worldcover_overview.py`,
`assess_flood_date_reliability.py`, `build_leakage_register.py`, `check_forecast_horizon_readiness.py`,
`audit_data.py` (first audit), `second_audit.py` (second, independent audit), `build_quality_scorecard.py`,
`build_final_inventory.py`, `generate_data_report.py`. Shared helpers: `_common.py`. Configuration:
`config/data_sources.yaml`.

## 25. Final readiness decision

Completeness gate:

- [x] Existing datasets audited · [x] DesInventar · [x] NASA POWER · [x] CHIRPS · [x] HydroSHEDS · [x] WorldCover
- [x] Soil moisture · [x] WorldPop · [x] Climate indices
- [x] GloFAS historical investigated — suitable, but collection **deferred by the researcher's decision (2026-10-08)**
  because EWDS credentials are not available; documented as a limitation; static river maps collected; scripts ready
- [x] GloFAS forecast investigated · [x] Other high-value sources investigated
- [x] Spatial coverage · [x] Temporal coverage · [x] Missingness · [x] Extreme values · [x] Cross-dataset checks
- [x] Leakage audit · [x] Forecast-horizon requirements · [x] Reproducibility scripts · [x] Documentation
- [x] First audit · [x] Second independent audit (50 checks: 48 PASS, 2 WARN, 0 FAIL)
- [x] No uninvestigated high-value source remains
- [x] No critical unresolved data-quality issue at the data level (date reliability flagged per record; the label
  rule is a Stage 3 design decision)

**STAGE 2 — COMPLETE DATA COLLECTION AND DOUBLE VERIFICATION: COMPLETE**

- Total datasets inventoried: 15 (11 collected, 4 deferred/not collected)
- Core: DesInventar (labels), NASA POWER weather, CHIRPS rainfall, HydroSHEDS terrain/hydrology, GloFAS static maps
- Optional: NASA POWER soil wetness, ESA WorldCover 2021, JRC Global Surface Water, climate indices
- Validation: DFO and GRDC not obtainable (documented); internal cross-dataset validation complete
- Exposure: WorldPop 2000–2020 (separate folder)
- Temporal coverage: daily weather 1999-04-14 → 2026-01-30 (no gaps); labels mainly 2000–2017 (82 high-confidence district-days)
- Spatial coverage: all 101 districts, 10 provinces
- GloFAS: historical and reforecasts deferred (researcher decision 2026-10-08); static river maps collected; pipeline ready
- Forecast data: no forecast archive collected; GloFAS reforecasts are the recommended route for an honest forecast test
- Major limitations: flood-date reliability (91 of 444 records high-confidence); no hydrological state variables
  without GloFAS; two rainfall sources partly redundant; static layers post-date many events

To add GloFAS later: set up `~/.cdsapirc` (EWDS token), set `glofas.collection_status: required` in
`config/data_sources.yaml`, run `download_glofas.py --product historical`, `extract_glofas.py`, then the audit chain.
