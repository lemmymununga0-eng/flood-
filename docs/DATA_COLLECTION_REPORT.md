# FloodShield-Zambia — Stage 1 Data Collection Report

_Generated 2026-10-07T20:26:01+00:00 by `scripts/generate_data_report.py` from `reports/validation_report.json`._

Stage 1 scope: **collect → store → validate → document raw data.** No target variable (`flood_next_7_days`) was created, and no model was trained or evaluated. No earlier model, prediction, label or processed dataset was reused.

## Summary

| Dataset | Source | Coverage | Records | Date Range | Missing Data | Status |
|---|---|---|---|---|---|---|
| DesInventar flood events | DesInventar Sendai (UNDRR) — Zambia | Zambia (national database) | 444 | 2000–2026 (exact-day: 2000-04-13 → 2026-01-23) | 37.8% lack an exact day | Collected |
| NASA POWER daily weather | NASA LaRC POWER Daily API | Global product; 101 Zambian district points | 988689 | 1999-04-14 → 2026-01-30 | max 0.00% per variable | Collected |
| CHIRPS v3.0 daily rainfall | UCSB Climate Hazards Center | Quasi-global product; Zambia window 0.05° | 9789 days × 202×238 px | 1999-04-14 → 2026-01-30 | 0 days; 0.00% pixels | Collected |

## Collection window

Weather sources were collected for **1999-04-14 → 2026-01-30**. This window was derived from the valid DesInventar flood dates (2000-04-13 → 2026-01-23), extended 365 days back for antecedent conditions and 7 days forward for the (t, t+7] target window. Basis: valid day- and month-precision FLOOD/FLASH FLOODS start dates (month precision counted as the whole month); year-only and invalid dates excluded.

## DesInventar

- Original export: `data/raw/desinventar/original/DI_export_zmb.zip` (1085926 bytes, sha256 `cc27bf744c657428…`, retrieved 2026-10-06T12:29:02+00:00).
- Total records (all hazard types): **2239**
- Flood records: **444** — {'FLOOD': 436, 'FLASH FLOODS': 8}
- Date precision: {'day': 276, 'year': 163, 'month': 3, 'invalid': 2} → **168** flood records have no exact day and cannot be placed in a 7-day window without further evidence.
- Exact-day date range: 2000-04-13 → 2026-01-23
- Suspicious dates: {'entered_before_event': 3, 'implausible_year:211': 1, 'implausible_year:201': 1}
- Provinces represented: 10; districts represented: 82
- Record identity: `serial` is re-used (377 flood records share a serial with another); `clave` is unique (0 duplicates) and is used as `record_id`.
- Exact duplicate records: 0 (0 groups); probable duplicates (same type, district, date and place text): 54; records sharing a district and exact day: 79 (may be distinct places — not merged).
- Records without a district: 4; records with their own coordinates: 1 (all others rely on the district point).
- Invalid numeric consequence values: none
- Location resolution of flood records: {'district': 440, 'province_only': 4}

### Province distribution (flood records)

| Province | Records |
|---|---|
| Western | 67 |
| Central | 66 |
| Eastern | 55 |
| Luapula | 53 |
| Lusaka | 52 |
| Southern | 37 |
| North-Western | 36 |
| Northern | 33 |
| Copperbelt | 28 |
| Muchinga | 17 |

### Event types and the flood definition

Included as floods: `FLOOD`, `FLASH FLOODS`. Other categories were inventoried, not assumed to be floods. `records_with_explicit_flood_words` counts records whose text mentions flood/inundation/overflow; those are listed in `reports/desinventar_flood_keyword_hits.csv` **for the researcher to confirm**; none were included.

| event_type | records | role | records_with_flood_keywords | records_with_explicit_flood_words | declared_in_eventos_table |
|---|---|---|---|---|---|
| PEST | 1234 | excluded_not_flood | 1 | 0 | True |
| FLOOD | 436 | included_flood | 341 | 99 | True |
| INSECT INFESTATION | 247 | excluded_not_flood | 2 | 1 | True |
| STORM | 102 | review_possibly_flood_related | 48 | 0 | True |
| ANIMAL INCIDENT | 40 | excluded_not_flood | 8 | 3 | True |
| HAILSTORM | 39 | review_possibly_flood_related | 27 | 2 | True |
| WINDSTORM | 35 | review_possibly_flood_related | 3 | 0 | True |
| STRUCTURAL COLLAPSE | 33 | review_possibly_flood_related | 7 | 1 | True |
| FIRE | 21 | excluded_not_flood | 0 | 0 | True |
| ROAD TRAFFIC ACCIDENT | 9 | excluded_not_flood | 0 | 0 | True |
| FLASH FLOODS | 8 | included_flood | 8 | 6 | True |
| STRONG WINDS | 7 | review_possibly_flood_related | 6 | 0 | True |
| MINE DISASTER | 6 | excluded_not_flood | 0 | 0 | True |
| CHOLERA | 4 | excluded_not_flood | 0 | 0 | True |
| EPIDEMIC | 4 | excluded_not_flood | 0 | 0 | True |
| DROUGHT | 4 | excluded_not_flood | 0 | 0 | True |
| Monkey Pox | 3 | excluded_not_flood | 0 | 0 | True |
| DROWNING | 3 | review_possibly_flood_related | 1 | 0 | True |
| LIGHTENING | 2 | excluded_not_flood | 2 | 0 | True |
| KONZO | 1 | excluded_not_flood | 0 | 0 | True |
| WETLAND LOSS/DEGRADATION | 1 | excluded_not_flood | 0 | 0 | True |

## Location master

- `data/processed/location_master.csv`: **101** districts (the DesInventar level-1 geography); coordinate quality {'district_point_verified_inside_polygon': 96, 'district_polygon_representative_point': 5}.
- Districts with ≥1 flood record: 82; with ≥1 exact-day flood record: 75.
- Unresolved: `data/processed/unresolved_locations.csv` (4 rows, 4 flood records).
- Sub-district place text (`lugar`) is preserved verbatim but not geocoded: it is free text (villages, wards, schools) with no reliable gazetteer match, so no coordinates were invented for it.
- Boundary-file issue: 2 polygon(s) in the DesInventar `districts.shp` share a code with a different DesInventar district (Mulobezi → 1001, Chikankanta → 911). They were not used for verification; see `reports/boundary_file_code_conflicts.csv`.

### Unresolved locations

| original_location | province | reason_unresolved | status | n_records | record_ids |
|---|---|---|---|---|---|
|  | Central | record has no district (level 1) code in DesInventar | unresolved_at_district_level_province_known | 1 | 740 |
|  | Luapula | record has no district (level 1) code in DesInventar | unresolved_at_district_level_province_known | 1 | 1700 |
| CHIKANKATA | Southern | record has no district (level 1) code in DesInventar | unresolved_at_district_level_province_known | 1 | 1359 |
| MUNGULUBE | Muchinga | record has no district (level 1) code in DesInventar | unresolved_at_district_level_province_known | 1 | 1448 |

## NASA POWER

- Locations: 101 of 101 expected; missing: none
- Date range: ['1999-04-14', '2026-01-30']; expected days per location: 9789
- Total observations (location-days): **988689**
- Duplicate location-dates: 0
- Locations with incomplete coverage: 0
- Failed API requests: 0 attempts; outstanding: []
- Flagged values (kept, not altered): {'extreme_rain_check:PRECTOTCORR': 31, 'outside_bounds:PRECTOTCORR': 2}
- Groups of districts that fall in the same NASA POWER grid cell (identical series): 8 — [['ZMB-D-0502', 'ZMB-D-0506'], ['ZMB-D-0107', 'ZMB-D-0111'], ['ZMB-D-0203', 'ZMB-D-0204', 'ZMB-D-0207'], ['ZMB-D-0202', 'ZMB-D-0209'], ['ZMB-D-0303', 'ZMB-D-0308'], ['ZMB-D-0407', 'ZMB-D-0809'], ['ZMB-D-0501', 'ZMB-D-0507'], ['ZMB-D-0908', 'ZMB-D-0910']]

| Variable | Missing % | Missing count | Min | Mean | Max |
|---|---:|---:|---:|---:|---:|
| PRECTOTCORR | 0.0000% | 0 | 0.0 | 2.641 | 338.3 |
| T2M | 0.0000% | 0 | 9.8 | 22.251 | 35.99 |
| T2M_MAX | 0.0000% | 0 | 15.5 | 29.041 | 45.03 |
| T2M_MIN | 0.0000% | 0 | 0.73 | 16.308 | 31.51 |
| RH2M | 0.0000% | 0 | 8.14 | 60.299 | 96.28 |
| WS10M | 0.0000% | 0 | 0.38 | 3.626 | 12.17 |

## CHIRPS v3.0

- Variant: daily `rnl` (`final`), 0.05°; files: 28 yearly NetCDFs
- Date range: ['1999-04-14', '2026-01-30']; days present 9789 of 9789; missing days: 0; duplicate days: 0
- Spatial coverage: {'lat_min': -18.175001164898276, 'lat_max': -8.125001015141606, 'lon_min': 21.925003008916974, 'lon_max': 33.775003185495734, 'n_lat': 202, 'n_lon': 238}
- Pixel-days: 470615964; missing/no-data: 0.00%; negative: 0
- Failed request attempts logged: 988; recovered on re-run: 988; outstanding dates: []
- Location-master points inside the grid: 101 (outside: 0)
- Nearest-pixel point extraction: 988689 rows, missing 0.00%, duplicates 0

## Cross-source rainfall sanity check (not a feature)

{'overlap_rows': 988689, 'monthly_total_corr_median': 0.902, 'monthly_total_corr_min': 0.839, 'daily_corr_median': 0.521, 'mean_daily_mm_power': 2.641, 'mean_daily_mm_chirps': 2.836}

NASA POWER `PRECTOTCORR` (MERRA-2 based, ~0.5° grid) and CHIRPS (0.05°) are kept as separate sources; neither replaces the other.

## Failed requests

| source | failed_attempts |
|---|---|
| chirps | 988 |
| global_surface_water | 1 |
| glofas | 1 |
| glofas_static | 1 |
| hydrosheds | 4 |
| nasa_power_soil | 46 |
| worldcover | 16 |

Recovery status: {'total_failed_attempts': 1057, 'chirps': {'failed_attempts': 988, 'recovered_on_rerun': 988, 'outstanding_dates': []}, 'global_surface_water': {'failed_attempts': 1, 'recovered_on_rerun': 1, 'outstanding': []}, 'glofas': {'failed_attempts': 1, 'recovered_on_rerun': 0, 'outstanding': ['credentials']}, 'glofas_static': {'failed_attempts': 1, 'recovered_on_rerun': 1, 'outstanding': []}, 'hydrosheds': {'failed_attempts': 4, 'recovered_on_rerun': 4, 'outstanding': []}, 'nasa_power_soil': {'failed_attempts': 46, 'recovered_on_rerun': 46, 'outstanding': []}, 'worldcover': {'failed_attempts': 16, 'recovered_on_rerun': 16, 'outstanding': []}}. A failure counts as *recovered* when the same item was successfully retrieved on a later run; *outstanding* items are still missing.

## Raw-data integrity

{'files_hashed': 130, 'files_with_recorded_hash': 102, 'mismatches': []} (`reports/raw_checksums.csv`). Raw files are written once; cleaning never overwrites them.

## Data-quality issues to carry into Stage 2

1. **168 of 444 flood records (38%) have no exact day** (year-only or month-only). They cannot be used as positives in a 7-day target and must not be treated as negatives.
2. **Reporting is uneven in time** (see `records_by_year` in the validation report): absence of a DesInventar record does not prove absence of flooding.
3. **Spatial unit is the district.** One point per district; weather for large districts is represented by a single point. NASA POWER's coarse grid means some neighbouring districts share identical series.
4. 54 probable-duplicate and 79 same-district-same-day records need a de-duplication rule before targets are built.
5. Consequence fields (deaths, houses, affected people…) are post-event information and must never be used as predictors.
6. Possibly flood-related records in other categories await the researcher's inclusion decision.

## Leakage rule for later stages

For a prediction date *t*, features may use only information available on or before *t*; `flood_next_7_days` = 1 only if a qualifying flood starts in (t, t+7]. Weather after *t* and any post-event consequence field are excluded from features.
