# FloodShield-Zambia — Data Audit Report (Stage 2)

_Generated 2026-10-07T22:20:19+00:00 by `scripts/audit_data.py` from files on disk. Full file inventory: `reports/data_inventory.csv` (722 files)._

## True status of every dataset (QC table, computed from files on disk)

| DATASET | ROLE | ACTUAL STATUS | FILES PRESENT | COVERAGE | MISSING | NEXT ACTION |
|---|---|---|---|---|---|---|
| DesInventar | LABEL SOURCE | COMPLETE | 1 original ZIP (sha256 verified); 35 extracted files | 2239 records; 444 flood (FLOOD 436, FLASH FLOODS 8); 440 at district level | 168 without exact day; 4 province-only; exact-day onset reliability: plausible 91, uncertain 102, unlikely 83 | Researcher decides the label rule (date reliability) before Stage 3 |
| Location master | SPATIAL KEY | COMPLETE | location_master.csv, unresolved_locations.csv | 101 districts, all with traceable coordinates | none | None |
| NASA POWER weather | CORE | COMPLETE | 101 raw JSON + CSV | 101 locations × 9789 days, 1999-04-14 → 2026-01-30 | 0 missing values; 2 flagged >300 mm days (probable reanalysis artefacts, retained) | None (capping rule is a Stage 3 decision) |
| CHIRPS v3.0 | CORE | COMPLETE | 28 yearly NetCDFs + point extraction | 9789/9789 days; years verified 28/28; 101 locations | missing years none; grid extremes >300 mm flagged (outside Zambia) | None |
| HydroSHEDS v1 (data v1.1) | CORE (static) | COMPLETE | 4 archives (sha256 + ZIP CRC ok); 4 subsets | DEM 15″, HydroRIVERS, HydroBASINS L4/L6; 101 districts point + zonal | flow dir/acc rasters not needed (HydroRIVERS upstream area) | None |
| ESA WorldCover 2021 v200 | OPTIONAL (static/slow-changing) | COMPLETE | 17 tiles (1/4 overview ≈ 40 m) | all tiles intersecting Zambia; 101 districts | 2021 snapshot only (temporal limitation) | None |
| NASA POWER soil wetness | OPTIONAL EXPERIMENT | COMPLETE | 101 raw JSON + CSV | 101 locations, full window | overlap with 90-day rainfall (Spearman): GWETROOT 0.898 | None |
| WorldPop | EXPOSURE (separate layer) | COMPLETE | 21 yearly rasters; exposure table present | 2000–2020, 101 districts | 2021–2026 not in this product | None |
| Climate indices | OPTIONAL (seasonal, lagged) | COMPLETE | 4 raw files | ONI/Niño 3.4 1950–2026, DMI 1870–2026, BoM IOD 2008–2026 | months not yet published | None |
| DFO / satellite flood data | VALIDATION (optional) | MISSING | 0 DFO files | — | DFO server unreachable all collection period; S1/GFD/CEMS not collected | OPTIONAL VALIDATION DATA — NOT REQUIRED FOR CORE MODEL; re-run download_flood_observations.py if access returns |
| GRDC / hydrological observations | OPTIONAL / DATA ACCESS LIMITED | MISSING | README only | — | all series (request-only access) | Optional: submit a GRDC request; not required for Stage 3 |
| GloFAS v4 river-network static maps | CORE support | COMPLETE | 3 originals + 3 subsets | 0.05° Zambia window | — | None |
| GloFAS v4.0 historical (discharge, runoff, soil wetness) | DEFERRED by researcher decision 2026-10-08 | MISSING | 0 GRIB2 files | planned: 101 districts, 1999–2026 | all — EWDS requires the researcher's ECMWF account and token | Deferred. To add later: create ECMWF account, accept CEMS-FLOODS licence, write ~/.cdsapirc; run download_glofas.py + extract_glofas.py |
| GloFAS v4.0 reforecasts | DEFERRED (optional forecast experiment) | MISSING | 0 GRIB2 files | planned: issues 2003-03 → 2023-11, leads 1–46 d | all — same credentials | Optional, after the historical download |
| JRC Global Surface Water occurrence | OPTIONAL (static) | COMPLETE | 4 of 4 tiles | Zambia, 30 m → 101 districts | — | None |

## Temporal coverage audit

| Dataset | Earliest date | Latest date | Missing periods | Usable period |
|---|---|---|---|---|
| DesInventar flood events (exact day) | 2000-04-13 | 2026-01-23 | no exact-day records in [2002, 2003, 2005, 2018, 2019, 2020, 2021, 2024] | Labels mainly 2000–2017 (+ a few 2022–2026); see date-reliability classes |
| NASA POWER weather | 1999-04-14 | 2026-01-30 | none | full window |
| CHIRPS v3.0 | 1999-04-14 | 2026-01-30 | none | full window |
| NASA POWER soil wetness | 1999-04-14 | 2026-01-30 | none | full window (optional) |
| HydroSHEDS | static (~2000) | static | — | time-invariant |
| ESA WorldCover | 2021 | 2021 | single snapshot | quasi-static assumption |
| WorldPop | 2000 | 2020 | 2021–2026 | exposure only |
| ONI / Niño 3.4 | 1950-01 | 2026-08 / 2026-06 | unpublished recent months | full window, lagged |
| DMI (NOAA PSL) | 1870-01 | 2026-05 | unpublished recent months | full window, lagged |
| DFO archive | — | — | not collected (server unreachable) | — |
| River gauges | — | — | not collected (request-only) | — |

## Spatial coverage audit

| Dataset | Spatial relationship to the location master | Coverage of 101 districts |
|---|---|---|
| DesInventar | district (record coded to DesInventar level 1) | 82 districts have ≥1 flood record; 4 records province-only |
| Location master | district point (DesInventar regiones point verified inside polygon, or polygon interior point) | 101/101 |
| NASA POWER weather / soil | raster cell (~0.5° MERRA-2) at the district point | 101/101 (8 groups share a cell) |
| CHIRPS | raster cell (0.05°) nearest the district point; full grid kept | 101/101, one pixel each |
| HydroSHEDS DEM/slope | zonal statistic over district polygon + value at district point | 101/101 |
| HydroRIVERS | distances from point and from a ~2 km district sample grid; max upstream area in district | 101/101 |
| HydroBASINS | basin containing the point; dominant basin in district | 101/101 |
| WorldCover | zonal class shares over district polygon + class at point | 101/101 |
| WorldPop | zonal sum over district polygon (exposure layer) | 101/101 × 21 years |
| Climate indices | national/global index (same value for every district) | n/a |
| DFO / river gauges | event centroid / river station (would need a later spatial join) | not collected |

## Dataset status (detailed)

| Dataset | Source | Purpose | Status | Spatial coverage | Temporal coverage | Completeness | Validation status | Action required |
|---|---|---|---|---|---|---|---|---|
| DesInventar Zambia (raw export + flood subset) | UNDRR DesInventar | Flood events (future target), audit | COMPLETE | Zambia; 440/444 flood records at district level | flood years ['2000', '2026']; exact days ['2000-04-13', '2026-01-23'] | 444 flood records; 168 without exact day | raw ZIP sha256 matches; record_id unique; resolution report complete | None for collection (see methodological items below) |
| Location master (101 districts) | DesInventar geography | Spatial key for all joins | COMPLETE | 101 districts | static | 101/101 with coordinates | IDs unique; quality {'district_point_verified_inside_polygon': 96, 'district_polygon_representative_point': 5} | None |
| NASA POWER daily weather | NASA LaRC POWER API v2.10 | Core weather predictors | COMPLETE | 101 district points | 1999-04-14 → 2026-01-30 | 988689 rows; 0 missing | 0 duplicates; flagged {'extreme_rain_check:PRECTOTCORR': 31, 'outside_bounds:PRECTOTCORR': 2} | Decide capping rule for 2 flagged >300 mm days in Stage 3 (documented, not deleted) |
| CHIRPS v3.0 daily rainfall | UCSB Climate Hazards Center | Independent rainfall predictor | COMPLETE | Zambia 0.05° grid; 101 district points | 9789/9789 days | missing years [] | reports/chirps_validation_report.md | None |
| HydroSHEDS DEM/slope, HydroRIVERS, HydroBASINS | HydroSHEDS v1 | Static terrain/drainage predictors | COMPLETE | Zambia window; district zonal + point | static | see environmental report | reports/environmental_data_validation_report.md | None |
| ESA WorldCover 2021 | ESA WorldCover v200 | OPTIONAL static/slow-changing context (2021 snapshot) | COMPLETE | Zambia tiles (40 m overview) | 2021 snapshot | see environmental report | class codes + % sums checked | None |
| NASA POWER soil wetness | NASA POWER (MERRA-2) | Optional experiment | COMPLETE | 101 district points | 1999-04-14 → 2026-01-30 | see environmental report | range 0–1 checked | None |
| ERA5-Land soil moisture | Copernicus CDS | Optional experiment (higher resolution) | METHODOLOGICAL DECISION REQUIRED | not collected | 1950–present (product) | 0% | n/a | Needs the researcher's CDS account/licence acceptance — only if the optional experiment is wanted |
| River gauges (GRDC / WARMA / ZRA) | GRDC portal; national agencies | Validation/context | MISSING | not collected | unknown | 0% | n/a | OPTIONAL / DATA ACCESS LIMITED: GRDC series only via a personal request form; WARMA has no public portal. Not required for Stage 3 |
| DFO flood archive | Dartmouth Flood Observatory | Independent event validation | MISSING | event centroids | 1985– (product) | see environmental report | n/a | OPTIONAL VALIDATION DATA — NOT REQUIRED FOR CORE MODEL (server unreachable; script ready) |
| Satellite flood extent (Sentinel-1, Global Flood Database, CEMS) | Copernicus / NASA | Validation | MISSING | not collected | S1 2014–; GFD 2000–2018 | 0% | n/a | Future work (needs Earth Engine/Copernicus accounts and heavy processing) |
| Climate indices (ONI, Niño 3.4, DMI) | NOAA CPC / NOAA PSL / BoM | Optional seasonal context | COMPLETE | basin-scale index | 1870/1950 → 2026 | see environmental report | monthly continuity checked | None |
| WorldPop population | WorldPop (Univ. Southampton) | Risk/exposure layer | COMPLETE | Zambia 1 km; district sums | 2000–2020 yearly | see environmental report | national totals checked | None |
| Flood definition: 7 non-flood-category records describing floods | DesInventar | Label scope | METHODOLOGICAL DECISION REQUIRED | — | — | kept separately | reports/desinventar_flood_keyword_hits.csv | Researcher decides include/exclude before Stage 3 labels |
| Flood-date reliability (exact-day records) | DesInventar | Label timing | METHODOLOGICAL DECISION REQUIRED | — | — | onset_plausible / uncertain / unlikely flags | reports/flood_date_reliability.md | Researcher chooses which exact-day records may be positives (many dates are assessment/report dates) |
| Year-/month-only flood dates (168 records) | DesInventar | Label scope | METHODOLOGICAL DECISION REQUIRED | — | — | preserved | date_precision column | Stage 3 must exclude them from both classes (cannot be placed in a 7-day window) |

## What is on disk (by folder)

| top | files | mb |
|---|---|---|
| ai-engine/data/external | 3 | 0.0 |
| ai-engine/data/features | 1 | 0.0 |
| ai-engine/data/interim | 1 | 0.0 |
| ai-engine/data/processed | 3 | 4.4 |
| ai-engine/data/raw | 3 | 1.1 |
| config | 1 | 0.0 |
| data/final | 1 | 0.0 |
| data/processed | 15 | 126.9 |
| data/quality_flags | 3 | 0.0 |
| data/raw/chirps | 29 | 918.1 |
| data/raw/climate_indices | 8 | 0.1 |
| data/raw/desinventar | 36 | 28.3 |
| data/raw/era5_land | 1 | 0.0 |
| data/raw/glofas | 9 | 156.2 |
| data/raw/hydrology | 1 | 0.0 |
| data/raw/hydrosheds | 12 | 339.3 |
| data/raw/landcover | 17 | 167.1 |
| data/raw/nasa_power | 407 | 602.9 |
| data/raw/other | 8 | 145.4 |
| data/raw/satellite_flood | 1 | 0.0 |
| data/raw/worldpop | 43 | 88.7 |
| docs | 51 | 0.6 |
| docs/backend | 1 | 0.0 |
| ml/baseline | 1 | 0.0 |
| ml/labels | 4 | 0.2 |
| reports | 34 | 1.1 |
| scripts | 28 | 0.3 |

Per-location NASA POWER JSON responses (101 + 101 files), DesInventar XML tables and provenance sidecars are counted above but not listed individually below.

## Key data files

| path | bytes | modified | rows | date_min | date_max | extent |
|---|---|---|---|---|---|---|
| data/processed/chirps_daily_at_locations.csv | 106968072 | 2026-10-07 16:55 | 988689 | 1999-04-14 | 2026-01-30 |  |
| data/processed/climate_indices_monthly.csv | 228929 | 2026-10-07 11:26 | 1884 |  |  |  |
| data/processed/climate_iod_weekly_bom.csv | 26833 | 2026-10-07 11:26 | 947 | 2008-07-28 | 2026-09-28 |  |
| data/processed/collection_window.json | 411 | 2026-10-06 14:29 |  |  |  |  |
| data/processed/derived_rasters/slope_15s_zambia.tif | 18138506 | 2026-10-07 13:02 |  |  |  | 2976x2544 px, res 0.00417, bounds (21.65, -18.45, 34.05, -7.85) |
| data/processed/desinventar_flood_date_reliability.csv | 70010 | 2026-10-07 21:37 | 444 | 2000-04-13 | 2026-01-23 |  |
| data/processed/desinventar_flood_event_audit.csv | 175593 | 2026-10-07 21:37 | 478 |  |  |  |
| data/processed/desinventar_flood_events.csv | 330317 | 2026-10-06 14:29 | 444 | 2000-04-13 | 2026-01-23 |  |
| data/processed/district_landcover.csv | 23031 | 2026-10-07 16:43 | 101 |  |  |  |
| data/processed/district_terrain_hydrology.csv | 51269 | 2026-10-07 13:03 | 101 |  |  |  |
| data/processed/environmental/district_surface_water.csv | 18007 | 2026-10-07 22:23 | 101 |  |  |  |
| data/processed/exposure/worldpop_district_exposure.csv | 827384 | 2026-10-07 16:55 | 2121 |  |  |  |
| data/processed/hydrology/glofas_district_extraction_points.csv | 26239 | 2026-10-07 22:11 | 101 |  |  |  |
| data/processed/location_master.csv | 26212 | 2026-10-06 14:43 | 101 |  |  |  |
| data/processed/unresolved_locations.csv | 1374 | 2026-10-06 14:43 | 4 |  |  |  |
| data/quality_flags/glofas_extraction_point_flags.csv | 1103 | 2026-10-07 22:11 | 5 |  |  |  |
| data/quality_flags/nasa_power_timeseries_flags.csv | 42 | 2026-10-08 00:11 | 0 |  |  |  |
| data/quality_flags/soil_wetness_timeseries_flags.csv | 17455 | 2026-10-08 00:12 | 303 |  |  |  |
| data/raw/chirps/chirps_manifest.csv | 2026654 | 2026-10-07 16:53 | 10091 | 1999-04-14 | 2026-01-30 |  |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.1999.nc | 20108864 | 2026-10-06 14:40 | 262 | 1999-04-14 | 1999-12-31 | time=262 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2000.nc | 36395576 | 2026-10-06 14:43 | 366 | 2000-01-01 | 2000-12-31 | time=366 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2001.nc | 35390825 | 2026-10-06 14:45 | 365 | 2001-01-01 | 2001-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2002.nc | 34118200 | 2026-10-06 14:48 | 365 | 2002-01-01 | 2002-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2003.nc | 33746019 | 2026-10-06 14:53 | 365 | 2003-01-01 | 2003-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2004.nc | 35774213 | 2026-10-06 14:56 | 366 | 2004-01-01 | 2004-12-31 | time=366 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2005.nc | 31853419 | 2026-10-06 15:00 | 365 | 2005-01-01 | 2005-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2006.nc | 36154950 | 2026-10-06 15:02 | 365 | 2006-01-01 | 2006-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2007.nc | 35539530 | 2026-10-06 15:05 | 365 | 2007-01-01 | 2007-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2008.nc | 33571998 | 2026-10-06 15:10 | 366 | 2008-01-01 | 2008-12-31 | time=366 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2009.nc | 34479832 | 2026-10-06 15:15 | 365 | 2009-01-01 | 2009-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2010.nc | 35110081 | 2026-10-06 15:18 | 365 | 2010-01-01 | 2010-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2011.nc | 34477896 | 2026-10-06 19:43 | 365 | 2011-01-01 | 2011-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2012.nc | 33924073 | 2026-10-07 09:17 | 366 | 2012-01-01 | 2012-12-31 | time=366 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2013.nc | 32082103 | 2026-10-07 09:30 | 365 | 2013-01-01 | 2013-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2014.nc | 33279406 | 2026-10-07 09:49 | 365 | 2014-01-01 | 2014-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2015.nc | 35097348 | 2026-10-07 10:11 | 365 | 2015-01-01 | 2015-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2016.nc | 33210335 | 2026-10-07 10:30 | 366 | 2016-01-01 | 2016-12-31 | time=366 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2017.nc | 35865417 | 2026-10-07 10:54 | 365 | 2017-01-01 | 2017-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2018.nc | 34807766 | 2026-10-07 12:40 | 365 | 2018-01-01 | 2018-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2019.nc | 33799989 | 2026-10-07 12:59 | 365 | 2019-01-01 | 2019-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2020.nc | 34230985 | 2026-10-07 16:33 | 366 | 2020-01-01 | 2020-12-31 | time=366 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2021.nc | 33510518 | 2026-10-07 16:36 | 365 | 2021-01-01 | 2021-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2022.nc | 35026562 | 2026-10-07 16:42 | 365 | 2022-01-01 | 2022-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2023.nc | 32998088 | 2026-10-07 16:47 | 365 | 2023-01-01 | 2023-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2024.nc | 31790238 | 2026-10-07 16:50 | 366 | 2024-01-01 | 2024-12-31 | time=366 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2025.nc | 35299373 | 2026-10-07 16:53 | 365 | 2025-01-01 | 2025-12-31 | time=365 x lat=202 x lon=238 |
| data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.2026.nc | 4417804 | 2026-10-07 16:53 | 30 | 2026-01-01 | 2026-01-30 | time=30 x lat=202 x lon=238 |
| data/raw/climate_indices/dmi.had.long.data | 19861 | 2026-10-07 11:26 |  |  |  |  |
| data/raw/climate_indices/ersst5.nino.mth.91-20.ascii | 67087 | 2026-10-07 11:26 |  |  |  |  |
| data/raw/climate_indices/iod_1.txt | 22069 | 2026-10-07 11:26 |  |  |  |  |
| data/raw/climate_indices/oni.ascii.txt | 23025 | 2026-10-07 11:26 |  |  |  |  |
| data/raw/desinventar/extracted/desinventar_all_records_joined.csv | 1470727 | 2026-10-06 14:29 | 2319 |  |  |  |
| data/raw/desinventar/extracted/DI_export_zmb.xml | 22894481 | 2026-10-06 14:29 |  |  |  |  |
| data/raw/desinventar/extracted/districts.shp | 802504 | 2026-10-06 14:29 | 103 |  |  | (21.98, -18.08, 33.71, -8.27) |
| data/raw/desinventar/extracted/Provinces.shp | 323860 | 2026-10-06 14:29 | 10 |  |  | (21.98, -18.08, 33.71, -8.27) |
| data/raw/desinventar/original/DI_export_zmb.zip | 1085926 | 2026-10-06 14:29 |  |  |  |  |
| data/raw/glofas/static/original/chan_Global_03min.nc | 26025166 | 2026-10-07 22:10 |  |  |  | unreadable: KeyError("No variable named 'time'. Variables on the dataset include ['crs', 'Band1', 'lon', 'lat']") |
| data/raw/glofas/static/original/ldd_repaired.nc | 26026096 | 2026-10-07 21:51 |  |  |  | unreadable: KeyError("No variable named 'time'. Variables on the dataset include ['crs', 'Band1', 'lon', 'lat']") |
| data/raw/glofas/static/original/upArea_repaired.nc | 103785588 | 2026-10-07 21:42 |  |  |  | unreadable: KeyError("No variable named 'time'. Variables on the dataset include ['crs', 'Band1', 'lon', 'lat']") |
| data/raw/glofas/static/zambia_subset/chan_Global_03min_zambia.nc | 75719 | 2026-10-07 22:10 |  |  |  | unreadable: KeyError("No variable named 'time'. Variables on the dataset include ['crs', 'Band1', 'lon', 'lat']") |
| data/raw/glofas/static/zambia_subset/ldd_repaired_zambia.nc | 76363 | 2026-10-07 21:51 |  |  |  | unreadable: KeyError("No variable named 'time'. Variables on the dataset include ['crs', 'Band1', 'lon', 'lat']") |
| data/raw/glofas/static/zambia_subset/upArea_repaired_zambia.nc | 234129 | 2026-10-07 21:42 |  |  |  | unreadable: KeyError("No variable named 'time'. Variables on the dataset include ['crs', 'Band1', 'lon', 'lat']") |
| data/raw/hydrosheds/original/hybas_af_lev04_v1c.zip | 5945213 | 2026-10-07 12:58 |  |  |  |  |
| data/raw/hydrosheds/original/hybas_af_lev06_v1c.zip | 17945918 | 2026-10-07 12:59 |  |  |  |  |
| data/raw/hydrosheds/original/hyd_af_dem_15s.zip | 170986111 | 2026-10-07 12:45 |  |  |  |  |
| data/raw/hydrosheds/original/HydroRIVERS_v10_af_shp.zip | 107873468 | 2026-10-07 12:57 |  |  |  |  |
| data/raw/hydrosheds/zambia_subset/dem_15s_zambia.tif | 9515092 | 2026-10-07 13:00 |  |  |  | 2976x2544 px, res 0.00417, bounds (21.65, -18.45, 34.05, -7.85) |
| data/raw/hydrosheds/zambia_subset/hybas_lev04_zambia.gpkg | 1216512 | 2026-10-07 13:01 | 17 |  |  | (15.39, -25.21, 39.39, 4.27) |
| data/raw/hydrosheds/zambia_subset/hybas_lev06_zambia.gpkg | 2641920 | 2026-10-07 13:01 | 229 |  |  | (18.67, -21.31, 36.31, -5.7) |
| data/raw/hydrosheds/zambia_subset/hydrorivers_zambia.gpkg | 23183360 | 2026-10-07 13:00 | 73859 |  |  | (21.44, -18.58, 34.33, -7.71) |
| data/raw/landcover/worldcover_2021_v200_ov4/S09E027.tif | 8093497 | 2026-10-07 16:41 |  |  |  | 9000x9000 px, res 0.00033, bounds (27.0, -9.0, 30.0, -6.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S09E030.tif | 9091193 | 2026-10-07 16:41 |  |  |  | 9000x9000 px, res 0.00033, bounds (30.0, -9.0, 33.0, -6.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S12E021.tif | 8819351 | 2026-10-07 16:36 |  |  |  | 9000x9000 px, res 0.00033, bounds (21.0, -12.0, 24.0, -9.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S12E024.tif | 8572257 | 2026-10-07 16:37 |  |  |  | 9000x9000 px, res 0.00033, bounds (24.0, -12.0, 27.0, -9.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S12E027.tif | 10428603 | 2026-10-07 16:37 |  |  |  | 9000x9000 px, res 0.00033, bounds (27.0, -12.0, 30.0, -9.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S12E030.tif | 11785337 | 2026-10-07 16:38 |  |  |  | 9000x9000 px, res 0.00033, bounds (30.0, -12.0, 33.0, -9.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S12E033.tif | 11414969 | 2026-10-07 16:40 |  |  |  | 9000x9000 px, res 0.00033, bounds (33.0, -12.0, 36.0, -9.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S15E021.tif | 6389489 | 2026-10-07 16:33 |  |  |  | 9000x9000 px, res 0.00033, bounds (21.0, -15.0, 24.0, -12.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S15E024.tif | 6845419 | 2026-10-07 16:33 |  |  |  | 9000x9000 px, res 0.00033, bounds (24.0, -15.0, 27.0, -12.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S15E027.tif | 10958449 | 2026-10-07 16:34 |  |  |  | 9000x9000 px, res 0.00033, bounds (27.0, -15.0, 30.0, -12.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S15E030.tif | 12237055 | 2026-10-07 16:35 |  |  |  | 9000x9000 px, res 0.00033, bounds (30.0, -15.0, 33.0, -12.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S15E033.tif | 10624673 | 2026-10-07 16:36 |  |  |  | 9000x9000 px, res 0.00033, bounds (33.0, -15.0, 36.0, -12.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S18E021.tif | 10448017 | 2026-10-07 16:30 |  |  |  | 9000x9000 px, res 0.00033, bounds (21.0, -18.0, 24.0, -15.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S18E024.tif | 11171565 | 2026-10-07 16:31 |  |  |  | 9000x9000 px, res 0.00033, bounds (24.0, -18.0, 27.0, -15.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S18E027.tif | 12296435 | 2026-10-07 16:32 |  |  |  | 9000x9000 px, res 0.00033, bounds (27.0, -18.0, 30.0, -15.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S18E030.tif | 13006075 | 2026-10-07 16:33 |  |  |  | 9000x9000 px, res 0.00033, bounds (30.0, -18.0, 33.0, -15.0) |
| data/raw/landcover/worldcover_2021_v200_ov4/S21E024.tif | 4941959 | 2026-10-07 13:02 |  |  |  | 9000x9000 px, res 0.00033, bounds (24.0, -21.0, 27.0, -18.0) |
| data/raw/nasa_power/download_manifest.csv | 14588 | 2026-10-07 16:48 | 202 |  |  |  |
| data/raw/nasa_power/nasa_power_daily.csv | 234785767 | 2026-10-07 12:30 | 988689 | 1999-04-14 | 2026-01-30 |  |
| data/raw/nasa_power/nasa_power_daily_soil_moisture.csv | 222583387 | 2026-10-07 16:48 | 988689 | 1999-04-14 | 2026-01-30 |  |
| data/raw/other/global_surface_water/occurrence_20E_0Nv1_4_2021.tif | 26483330 | 2026-10-07 21:48 |  |  |  | 40000x40000 px, res 0.00025, bounds (20.0, -10.0, 30.0, 0.0) |
| data/raw/other/global_surface_water/occurrence_20E_10Sv1_4_2021.tif | 32552400 | 2026-10-07 22:08 |  |  |  | 40000x40000 px, res 0.00025, bounds (20.0, -20.0, 30.0, -10.0) |
| data/raw/other/global_surface_water/occurrence_30E_0Nv1_4_2021.tif | 51640724 | 2026-10-07 22:22 |  |  |  | 40000x40000 px, res 0.00025, bounds (30.0, -10.0, 40.0, 0.0) |
| data/raw/other/global_surface_water/occurrence_30E_10Sv1_4_2021.tif | 34734376 | 2026-10-07 22:09 |  |  |  | 40000x40000 px, res 0.00025, bounds (30.0, -20.0, 40.0, -10.0) |
| data/raw/worldpop/worldpop_api_wpic1km_ZMB.json | 45846 | 2026-10-07 16:49 |  |  |  |  |
| data/raw/worldpop/zmb_ppp_2000_1km_Aggregated.tif | 4209384 | 2026-10-07 12:39 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2001_1km_Aggregated.tif | 4213190 | 2026-10-07 12:42 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2002_1km_Aggregated.tif | 4211174 | 2026-10-07 16:49 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2003_1km_Aggregated.tif | 4210768 | 2026-10-07 16:49 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2004_1km_Aggregated.tif | 4213644 | 2026-10-07 16:50 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2005_1km_Aggregated.tif | 4216748 | 2026-10-07 16:50 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2006_1km_Aggregated.tif | 4212930 | 2026-10-07 16:50 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2007_1km_Aggregated.tif | 4217316 | 2026-10-07 16:50 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2008_1km_Aggregated.tif | 4215988 | 2026-10-07 16:50 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2009_1km_Aggregated.tif | 4216688 | 2026-10-07 16:51 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2010_1km_Aggregated.tif | 4217955 | 2026-10-07 16:51 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2011_1km_Aggregated.tif | 4220046 | 2026-10-07 16:52 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2012_1km_Aggregated.tif | 4231886 | 2026-10-07 16:52 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2013_1km_Aggregated.tif | 4231330 | 2026-10-07 16:52 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2014_1km_Aggregated.tif | 4228660 | 2026-10-07 16:52 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2015_1km_Aggregated.tif | 4236041 | 2026-10-07 16:53 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2016_1km_Aggregated.tif | 4231296 | 2026-10-07 16:53 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2017_1km_Aggregated.tif | 4235890 | 2026-10-07 16:53 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2018_1km_Aggregated.tif | 4231818 | 2026-10-07 16:53 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2019_1km_Aggregated.tif | 4236202 | 2026-10-07 16:54 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |
| data/raw/worldpop/zmb_ppp_2020_1km_Aggregated.tif | 4239238 | 2026-10-07 16:54 |  |  |  | 1405x1179 px, res 0.00833, bounds (22.0, -18.08, 33.71, -8.25) |

## Scripts

| path | bytes | modified |
|---|---|---|
| scripts/_common.py | 8331 | 2026-10-07 11:25 |
| scripts/assess_flood_date_reliability.py | 10778 | 2026-10-07 21:37 |
| scripts/audit_data.py | 28125 | 2026-10-08 00:10 |
| scripts/build_final_inventory.py | 12349 | 2026-10-08 00:10 |
| scripts/build_glofas_extraction_points.py | 8269 | 2026-10-07 22:11 |
| scripts/build_leakage_register.py | 9120 | 2026-10-07 22:23 |
| scripts/build_location_master.py | 12771 | 2026-10-06 14:42 |
| scripts/build_quality_scorecard.py | 8274 | 2026-10-08 00:10 |
| scripts/check_forecast_horizon_readiness.py | 6090 | 2026-10-07 21:39 |
| scripts/collect_desinventar.py | 12754 | 2026-10-06 14:29 |
| scripts/download_chirps.py | 13860 | 2026-10-07 12:33 |
| scripts/download_climate_indices.py | 4775 | 2026-10-07 11:26 |
| scripts/download_flood_observations.py | 2085 | 2026-10-07 12:31 |
| scripts/download_global_surface_water.py | 4883 | 2026-10-07 21:36 |
| scripts/download_glofas.py | 9380 | 2026-10-08 00:00 |
| scripts/download_glofas_static.py | 3159 | 2026-10-07 21:08 |
| scripts/download_hydrosheds.py | 5712 | 2026-10-07 17:06 |
| scripts/download_nasa_power.py | 11214 | 2026-10-07 12:30 |
| scripts/download_worldcover.py | 4346 | 2026-10-07 12:30 |
| scripts/download_worldpop.py | 2006 | 2026-10-07 12:44 |
| scripts/extract_district_environment.py | 15541 | 2026-10-07 13:01 |
| scripts/extract_glofas.py | 7286 | 2026-10-07 21:46 |
| scripts/generate_data_report.py | 37748 | 2026-10-07 22:22 |
| scripts/second_audit.py | 27895 | 2026-10-08 00:10 |
| scripts/test_worldcover_overview.py | 4203 | 2026-10-07 13:00 |
| scripts/validate_chirps.py | 30234 | 2026-10-07 16:32 |
| scripts/validate_environmental_data.py | 14550 | 2026-10-07 16:49 |
| scripts/validate_raw_data.py | 26174 | 2026-10-07 17:06 |

## Legacy artefacts from the earlier pipeline (NOT used)

Stage 1 restarted from raw sources; nothing below feeds the new pipeline. They are listed so they are not mistaken for current data. **Note:** the legacy folder contains a *synthetic* weather file (`ai-engine/data/raw/synthetic_zambia_weather.csv`) — it must never be used as observed data.

| path | bytes | modified | rows |
|---|---|---|---|
| ml/labels/authoritative_events.csv | 62747 | 2026-09-26 18:38 | 711 |
| ml/labels/candidate_events.csv | 163844 | 2026-09-26 18:38 | 473 |
| ml/labels/LABEL_PROVENANCE.md | 6548 | 2026-09-26 19:03 |  |
| ml/labels/label_reconciliation.json | 801 | 2026-09-26 18:38 |  |
| ml/baseline/baseline_manifest.json | 15832 | 2026-09-26 18:26 |  |
| ai-engine/data/external/.gitkeep | 0 | 2026-09-07 20:12 |  |
| ai-engine/data/external/README.md | 5040 | 2026-09-09 00:30 |  |
| ai-engine/data/external/zambia_flood_events_log.csv | 6814 | 2026-09-09 00:15 | 14 |
| ai-engine/data/features/.gitkeep | 0 | 2026-09-07 20:12 |  |
| ai-engine/data/interim/.gitkeep | 0 | 2026-09-07 20:12 |  |
| ai-engine/data/processed/.gitkeep | 0 | 2026-09-07 20:12 |  |
| ai-engine/data/processed/cleaned_weather.csv | 532514 | 2026-09-09 10:21 | 8766 |
| ai-engine/data/processed/features.csv | 3866464 | 2026-09-09 00:58 | 8752 |
| ai-engine/data/raw/.gitkeep | 0 | 2026-09-07 20:12 |  |
| ai-engine/data/raw/nasa_power_zambia.csv | 532514 | 2026-09-09 00:58 | 8766 |
| ai-engine/data/raw/synthetic_zambia_weather.csv | 520492 | 2026-07-02 20:53 | 8766 |
