# Environmental Data Validation Report

_Generated 2026-10-07T20:22:42+00:00 by `scripts/validate_environmental_data.py`. Values are flagged, never altered._

## HydroSHEDS (terrain and hydrology)

**Status: COMPLETE**

- Original archives: 4 of 4 expected; sha256 verified: 4
- Zambia subsets present: ['dem_15s_zambia.tif', 'hydrorivers_zambia.gpkg', 'hybas_lev04_zambia.gpkg', 'hybas_lev06_zambia.gpkg']
- DEM: CRS EPSG:4326, 2976×2544 cells, resolution 0.004167° (~464 m), bounds (21.65, -18.45, 34.05, -7.85), nodata 32767.0
- DEM elevation range in window: 98–2920 m; nodata cells: 0
- District terrain/hydrology table: 101 rows; districts missing: none; cells with missing values: 0
- District mean elevation: 506–1550 m (Zambia's lowest point is ~329 m on the Zambezi and highest ~2,300 m in the Mafinga Hills)
- District minimum / maximum elevation overall: 325 / 2301 m
- Mean slope: 0.06–3.97°; flat fraction: 0.04–1.00
- Point-to-river distance (upland ≥1,000 km²): median 13.9 km, max 41.5 km
- Max upstream area within a district: 148–858399 km²
- District area check (equal-area projection): 738,677 km² summed (Zambia ≈ 752,600 km²; the 2 excluded boundary-conflict polygons account for part of any shortfall)
- Points without a HydroBASINS level-6 basin: 0
- Elevations outside 300–2,400 m: 0 districts

## ESA WorldCover 2021

**Status: COMPLETE**

- Tiles present: 17 (S09E027, S09E030, S12E021, S12E024, S12E027, S12E030, S12E033, S15E021, S15E024, S15E027, S15E030, S15E033, S18E021, S18E024, S18E027, S18E030, S21E024)
- Invalid class codes found: none (valid: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100])
- District land-cover table: 101 rows; districts missing: none
- Percentages sum to 100 ± 0.01 in 101 of 101 districts
- No-data cells inside districts: 92 of 555234398
- Zambia-wide mean of district percentages: tree_cover 38.6%, grassland 22.1%, shrubland 21.3%, cropland 9.2%, herbaceous_wetland 5.1%, permanent_water 2.6%, built_up 1.0%, bare_sparse 0.1%

## WorldPop population (exposure layer)

**Status: COMPLETE**

- Yearly rasters: 21 of 21; sha256 verified: 21
- Exposure table `data/processed/exposure/worldpop_district_exposure.csv`: 2121 rows, years 2000–2020, districts per year 101
- National total assigned to districts: 2000: 9.59 M, 2005: 11.08 M, 2010: 12.97 M, 2015: 15.38 M, 2020: 18.56 M
- Negative or missing populations: 0
- Unit: estimated people per ~1 km cell (WorldPop unconstrained, not UN-adjusted); district values are sums of cells whose centre lies in the district.

## Soil wetness (NASA POWER GWETTOP/GWETROOT/GWETPROF — optional experiment)

**Status: COMPLETE**

- Locations: 101 of 101; rows 988689 (expected 988689)
- Date range: 1999-04-14 → 2026-01-30; duplicate location-dates: 0
- Missing %: GWETTOP 0.000%, GWETROOT 0.000%, GWETPROF 0.000%
- Range (unit: soil wetness fraction 0–1, NASA POWER/MERRA-2): GWETTOP 0.03–1.00, GWETROOT 0.14–1.00, GWETPROF 0.15–0.99
- Values outside [0, 1]: 0
- Median (over districts) Spearman correlation with trailing NASA POWER rainfall: GWETTOP: 7d 0.77, 30d 0.83, 90d 0.89; GWETROOT: 7d 0.70, 30d 0.80, 90d 0.90; GWETPROF: 7d 0.46, 30d 0.61, 90d 0.86
- Interpretation: strong correlation with 30–90-day rainfall means soil wetness largely re-expresses antecedent rainfall from the same reanalysis; it is kept as an OPTIONAL EXPERIMENT, not a core feature.

## Climate indices (ONI, Niño 3.4, DMI/IOD)

**Status: COMPLETE**

- oni: 342 of 342 months present from 1998-01 to 2026-06; range -1.76 to 2.59; latest value [2026, 8]
- nino34_anom: 342 of 342 months present from 1998-01 to 2026-06; range -1.77 to 2.72; latest value [2026, 6]
- dmi_hadisst: 341 of 342 months present from 1998-01 to 2026-06; range -0.76 to 0.96; latest value [2026, 5]
- BoM weekly IOD: 947 weeks, 2008-07-28 → 2026-10-04 (starts 2008 — too short to be the only IOD source; NOAA PSL monthly DMI covers the full window)

## Dartmouth Flood Observatory archive (optional validation)

**Status: MISSING**

- floodobservatory.colorado.edu was unreachable from this machine during collection; `scripts/download_flood_observations.py` retries and resumes.
