> **Superseded (2026-10-07):** this was the gate *before* GloFAS was added as the highest-priority source. The current, double-verified status is in `docs/DATA_COLLECTION_FINAL_COMPLETION_REPORT.md` — **COMPLETE**, with GloFAS deferred by the researcher's decision (2026-10-08).

# FloodShield-Zambia — Data Collection Completion Report (Stage 2, after QC review)

Date: 2026-10-07. Scope: collection, storage, validation and documentation of raw data. **No target
(`flood_next_7_days`), training labels, rolling features, ML dataset or model was created.** No earlier model,
prediction, label or processed dataset was reused.

Every status below was re-derived from files on disk (`docs/DATA_AUDIT_REPORT.md`, `reports/data_inventory.csv`)
and the validators (`reports/validation_report.md`, `reports/chirps_validation_report.md`,
`reports/environmental_data_validation_report.md`).

## 1. True status of every dataset

| Dataset | Role | Actual status | Files present | Coverage | Missing | Next action |
|---|---|---|---|---|---|---|
| DesInventar Zambia | Label source | **COMPLETE** | Original export ZIP (SHA-256 verified) + extracted XML/shapefiles + tables | 2,239 records; 444 flood (FLOOD 436, FLASH FLOODS 8); 440 resolved to a district | 168 without exact day; 4 province-only; date-reliability issue (§4) | Researcher chooses label rule |
| Location master | Spatial key | **COMPLETE** | `location_master.csv`, `unresolved_locations.csv` | 101/101 districts, coordinates traceable to the DesInventar export (96 verified inside polygon, 5 polygon interior points) | — | — |
| NASA POWER weather | Core | **COMPLETE** | 101 raw JSON + metadata; flattened CSV | 101 × 9,789 days = 988,689 rows, 1999-04-14 → 2026-01-30 | 0 % missing; 0 duplicates | Stage 3 capping rule for 2 flagged days |
| CHIRPS v3.0 daily | Core | **COMPLETE** | 28 yearly NetCDFs (Zambia window) + 988,689-row point extraction | 9,789/9,789 days; 28/28 years verified for all 101 locations | 0 missing values, 0 negatives, 0 duplicates | — |
| HydroSHEDS v1 (data v1.1) | Core (static) | **COMPLETE** | 4 original archives (size = server size, ZIP CRC ok, SHA-256) + 4 Zambia subsets + slope raster | DEM 15″, HydroRIVERS, HydroBASINS L4/L6; 101 districts, 0 missing values | flow-dir/acc rasters intentionally not needed | — |
| ESA WorldCover 2021 v200 | Optional (static/slow-changing) | **COMPLETE** | 17 tiles (1/4 overview ≈ 40 m) | All tiles intersecting Zambia; 101 districts; shares sum to 100 % | single 2021 snapshot | — |
| NASA POWER soil wetness | Optional experiment | **COMPLETE** | 101 raw JSON + CSV | 988,689 rows, full window, values 0.03–1.00 | — | — |
| WorldPop | Exposure (separate) | **COMPLETE** | 21 yearly rasters (DOI 10.5258/SOTON/WP00670) + `data/processed/exposure/worldpop_district_exposure.csv` | 2000–2020 × 101 districts (98.6–98.8 % of the national raster total assigned) | 2021–2026 not in product | — |
| Climate indices | Optional (seasonal, lagged) | **COMPLETE** | ONI, Niño 3.4, NOAA PSL DMI, BoM weekly IOD | ONI 1950 → 2026-08; Niño 3.4 → 2026-06; DMI 1870 → 2026-05 | unpublished recent months | — |
| DFO / satellite flood data | Validation (optional) | **MISSING** | none | — | DFO server refused connections throughout; S1/GFD/CEMS not collected | OPTIONAL VALIDATION DATA — NOT REQUIRED FOR CORE MODEL |
| GRDC / hydrological observations | Optional / data access limited | **MISSING** | README documenting the evaluation | — | request-only | OPTIONAL / DATA ACCESS LIMITED |

Download robustness: 1,054 failed request attempts were logged during an unstable connection (DNS outages); **all
1,054 were recovered on re-runs, 0 outstanding** (`reports/failed_requests.csv`). No completed dataset was
re-downloaded. DFO never completed a retry cycle, so it has no entry in that log.

## 2. What was already complete, what was verified, what was completed

| | Datasets |
|---|---|
| Already complete before Stage 2 — **verified, not re-downloaded** | DesInventar (raw ZIP SHA-256 re-checked), location master, NASA POWER weather, CHIRPS 1999–2016 (2017 in progress) |
| Completed in Stage 2 | CHIRPS 2017–2026 (resumed from the first missing day; per-year verification of all 28 years) |
| New datasets collected | HydroSHEDS v1 (DEM, HydroRIVERS, HydroBASINS), ESA WorldCover 2021, NASA POWER soil wetness, WorldPop 2000–2020, ONI/Niño 3.4/DMI/IOD |
| Derived (not ML datasets) | `district_terrain_hydrology.csv`, `district_landcover.csv`, `exposure/worldpop_district_exposure.csv`, `climate_indices_monthly.csv`, `desinventar_flood_date_reliability.csv` |
| Rejected / optional / not collected | ERA5-Land (needs the researcher's CDS account; POWER soil wetness used instead for the optional experiment), river gauges (request-only), DFO (unreachable), Sentinel-1 / Global Flood Database (future work), Copernicus EMS (no Zambia flood activations), HydroSHEDS flow-direction/accumulation rasters (not needed) |

## 3. Temporal and spatial coverage

| Dataset | Earliest | Latest | Missing periods | Usable period |
|---|---|---|---|---|
| DesInventar flood (exact day) | 2000-04-13 | 2026-01-23 | no exact-day records in 2002, 2003, 2005, 2018–2021, 2024 | mainly 2000–2017 |
| NASA POWER / CHIRPS / soil wetness | 1999-04-14 | 2026-01-30 | none | full window |
| HydroSHEDS | static | static | — | time-invariant |
| WorldCover | 2021 | 2021 | snapshot | quasi-static |
| WorldPop | 2000 | 2020 | 2021–2026 | exposure only |
| ONI / Niño 3.4 / DMI | 1950 / 1950 / 1870 | 2026-08 / 2026-06 / 2026-05 | unpublished months | full window, lagged |

The common window of the core weather sources is **1999-04-14 → 2026-01-30**; usable labels concentrate in
2000–2017. The modelling period is a Stage 3 decision. Spatial relationships (district / district point / raster
cell / zonal statistic / national index) are tabulated in `docs/DATA_AUDIT_REPORT.md` → *Spatial coverage audit*;
every collected dataset joins to all 101 districts except the national climate indices (same value everywhere).

## 4. Key findings from QC

1. **Label timing (most important).** Of 276 exact-day flood records, only **91 are plausibly onset dates**; 102 are
   uncertain and 83 are unlikely (dry-season assessment, repair or batch entries, e.g. 20 records dated 2013-06-06).
   The flags use no rainfall, yet rainfall separates them sharply: the 7-day rain before *plausible* dates sits at the
   73rd wet-season percentile vs the 4th for *unlikely* dates (`reports/flood_date_reliability.md`).
2. **CHIRPS vs NASA POWER:** monthly r 0.90, daily r 0.52, mean bias +0.20 mm/day, mean absolute daily difference
   2.35 mm; they agree on only ~4 % of heavy (≥30 mm) days. Not forced to agree; partly redundant at the seasonal
   scale — Stage 3 must justify using one or both.
3. **NASA POWER 338 / 304 mm days** are probable reanalysis artefacts (CHIRPS 10.8 / 29.5 mm at the same points) —
   retained, flagged.
4. **CHIRPS grid extremes (402 mm 2009-04-02; 336 mm 2022-04-27)** match the official files and pentad totals, lie
   outside Zambia, and touch no district series — retained, flagged.
5. **Soil wetness** correlates 0.83–0.90 (Spearman) with trailing 30–90-day rainfall → optional experiment only.
6. **WorldCover** overview method checked at six sites (≤ 0.52 percentage points) — a method check, not a
   nationwide accuracy assessment; classified optional because it is a 2021 snapshot.

## 5. Leakage controls

Prohibited as predictors (kept only for audit/validation): deaths, injured, missing, affected, victims, evacuated,
relocated, houses damaged/destroyed, crop/livestock/road/bridge/school/hospital damage, economic losses, sector
flags, relief/emergency response, assessment reports, disaster declarations, event duration/end date, comments,
post-event flood extent, DFO deaths/displaced/severity. Climate indices must be lagged (ONI ≤ month(t) − 2;
Niño 3.4/DMI ≤ month(t) − 1). Weather windows must end at *t*. Details: `docs/DATA_REQUIREMENTS_MATRIX.md` §4.

## 6. Final data-collection gate

- [x] DesInventar verified (SHA-256, 444 flood records, record IDs unique, resolution preserved)
- [x] 101-location master verified
- [x] NASA POWER weather verified (0 missing, 0 duplicates)
- [x] CHIRPS complete and validated (9,789/9,789 days; 28/28 years × 101 locations)
- [x] HydroSHEDS verified (v1, data version 1.1; sizes, CRC and SHA-256)
- [x] WorldCover verified **and** classified optional
- [x] Soil moisture evaluated (optional experiment)
- [x] Climate indices collected
- [x] WorldPop collected as a separate exposure layer
- [x] GRDC limitation documented (`data/raw/hydrology/README.md`)
- [x] Satellite/DFO validation status documented (`data/raw/satellite_flood/README.md`)
- [x] Temporal coverage documented
- [x] Spatial coverage documented
- [x] Provenance documented (`docs/DATA_SOURCES.md`, per-file provenance JSON, checksums)
- [x] Leakage risks documented
- [x] Core / optional / validation / exposure classification documented (`docs/METHODOLOGICAL_DATA_DECISIONS.md`)

## 7. Decisions required before dataset construction (Stage 3, researcher)

1. Label rule given date reliability (§4.1) — the first step of Stage 3, and it determines whether a 7-day target
   has enough events (91 plausible; 193 if uncertain dates are admitted).
2. Whether the 7 flood-describing records in other categories count as floods.
3. Rainfall-source policy (POWER, CHIRPS, or one as sensitivity analysis).
4. One rule for extreme rainfall values.
5. Which optional experiments to run.

None of these is a missing-data problem; all are design choices that need the researcher's judgement.

## 8. Status

**CORE DATA COLLECTION STATUS:** COMPLETE
**OPTIONAL DATA STATUS:** COMPLETE (soil wetness, climate indices, land cover; ERA5-Land not required)
**VALIDATION DATA STATUS:** NOT REQUIRED — none obtained (DFO unreachable; gauges request-only; satellite = future work)
**EXPOSURE DATA STATUS:** COMPLETE

**OVERALL: DATA COLLECTION COMPLETE — READY FOR DATASET CONSTRUCTION**
(Stage 3 must begin with the researcher's label-rule decision in §7.1.)
