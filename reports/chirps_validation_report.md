# CHIRPS v3.0 Validation Report

_Generated 2026-10-07T14:59:52+00:00 by `scripts/validate_chirps.py`._

**Product:** CHIRPS v3.0 daily, `final` stream, `rnl` disaggregation, 0.05°. **Required window:** 1999-04-14 → 2026-01-30 (9789 days).

## Coverage

- Yearly files present: 28 of 28 required (1999–2026)
- Missing years: none
- Days present: 9789 of 9789; missing days: 0
- Duplicate days: 0
- Grid: 202 × 238 cells, lat -18.175…-8.125, lon 21.925…33.775
- Grid identical in every yearly file: True
- Missing/no-data pixel-days: 0; negative pixel-days: 0
- Pixel-days above 150 mm (flagged, kept): 589; maximum value: 402.0 mm/day

## Location coverage (nearest-pixel extraction at the location-master points)

- Locations expected: 101; present: 101; missing: none
- Rows: 988689; missing values: 0; duplicate location-dates: 0
- Date range of extraction: 1999-04-14 → 2026-01-30
- Locations sharing the same CHIRPS pixel: none

- Units attribute of every yearly file: ['mm/day'] (CHIRPS v3.0 official unit: mm/day)
- Each location uses the same CHIRPS pixel in every year (consistent extraction): True

## Per-year verification of the 101-location extraction

A year is *verified* only if all 101 locations have every expected day, with no duplicates, missing or negative values.

| year | expected_days | locations_present | locations_with_all_days | duplicate_location_dates | missing_values | negative_values | max_point_mm | verified |
|---|---|---|---|---|---|---|---|---|
| 1999 | 262 | 101 | 101 | 0 | 0 | 0 | 54.4 | True |
| 2000 | 366 | 101 | 101 | 0 | 0 | 0 | 55.7 | True |
| 2001 | 365 | 101 | 101 | 0 | 0 | 0 | 64.7 | True |
| 2002 | 365 | 101 | 101 | 0 | 0 | 0 | 80.7 | True |
| 2003 | 365 | 101 | 101 | 0 | 0 | 0 | 112.9 | True |
| 2004 | 366 | 101 | 101 | 0 | 0 | 0 | 101.5 | True |
| 2005 | 365 | 101 | 101 | 0 | 0 | 0 | 54.2 | True |
| 2006 | 365 | 101 | 101 | 0 | 0 | 0 | 65.3 | True |
| 2007 | 365 | 101 | 101 | 0 | 0 | 0 | 94.4 | True |
| 2008 | 366 | 101 | 101 | 0 | 0 | 0 | 68.4 | True |
| 2009 | 365 | 101 | 101 | 0 | 0 | 0 | 76.8 | True |
| 2010 | 365 | 101 | 101 | 0 | 0 | 0 | 82.3 | True |
| 2011 | 365 | 101 | 101 | 0 | 0 | 0 | 68.5 | True |
| 2012 | 366 | 101 | 101 | 0 | 0 | 0 | 69.9 | True |
| 2013 | 365 | 101 | 101 | 0 | 0 | 0 | 73.4 | True |
| 2014 | 365 | 101 | 101 | 0 | 0 | 0 | 64.4 | True |
| 2015 | 365 | 101 | 101 | 0 | 0 | 0 | 85.4 | True |
| 2016 | 366 | 101 | 101 | 0 | 0 | 0 | 70.8 | True |
| 2017 | 365 | 101 | 101 | 0 | 0 | 0 | 126.5 | True |
| 2018 | 365 | 101 | 101 | 0 | 0 | 0 | 100.0 | True |
| 2019 | 365 | 101 | 101 | 0 | 0 | 0 | 64.3 | True |
| 2020 | 366 | 101 | 101 | 0 | 0 | 0 | 72.6 | True |
| 2021 | 365 | 101 | 101 | 0 | 0 | 0 | 56.4 | True |
| 2022 | 365 | 101 | 101 | 0 | 0 | 0 | 68.9 | True |
| 2023 | 365 | 101 | 101 | 0 | 0 | 0 | 77.6 | True |
| 2024 | 366 | 101 | 101 | 0 | 0 | 0 | 71.9 | True |
| 2025 | 365 | 101 | 101 | 0 | 0 | 0 | 68.5 | True |
| 2026 | 30 | 101 | 101 | 0 | 0 | 0 | 102.7 | True |

## Per-year grid file checks

| year | days_expected | days_present | missing_days | duplicate_days | grid_matches_first_file | missing_pixels | negative_pixels | pixel_days_gt_150mm | max_mm | zambia_window_mean_annual_total_mm |
|---|---|---|---|---|---|---|---|---|---|---|
| 1999 | 262 | 262 | 0 | 0 | True | 0 | 0 | 0 | 90.9 | 325.5 |
| 2000 | 366 | 366 | 0 | 0 | True | 0 | 0 | 0 | 123.6 | 1132.9 |
| 2001 | 365 | 365 | 0 | 0 | True | 0 | 0 | 0 | 116.5 | 1144.3 |
| 2002 | 365 | 365 | 0 | 0 | True | 0 | 0 | 0 | 107.8 | 968.7 |
| 2003 | 365 | 365 | 0 | 0 | True | 0 | 0 | 0 | 138.0 | 1004.6 |
| 2004 | 366 | 366 | 0 | 0 | True | 0 | 0 | 8 | 192.5 | 1151.3 |
| 2005 | 365 | 365 | 0 | 0 | True | 0 | 0 | 0 | 99.3 | 921.3 |
| 2006 | 365 | 365 | 0 | 0 | True | 0 | 0 | 0 | 130.2 | 1190.0 |
| 2007 | 365 | 365 | 0 | 0 | True | 0 | 0 | 0 | 143.3 | 1180.5 |
| 2008 | 366 | 366 | 0 | 0 | True | 0 | 0 | 0 | 120.2 | 1094.7 |
| 2009 | 365 | 365 | 0 | 0 | True | 0 | 0 | 97 | 402.0 | 1216.6 |
| 2010 | 365 | 365 | 0 | 0 | True | 0 | 0 | 0 | 139.5 | 1162.3 |
| 2011 | 365 | 365 | 0 | 0 | True | 0 | 0 | 16 | 193.5 | 1040.3 |
| 2012 | 366 | 366 | 0 | 0 | True | 0 | 0 | 0 | 132.5 | 1082.4 |
| 2013 | 365 | 365 | 0 | 0 | True | 0 | 0 | 0 | 138.0 | 997.6 |
| 2014 | 365 | 365 | 0 | 0 | True | 0 | 0 | 3 | 166.4 | 1079.2 |
| 2015 | 365 | 365 | 0 | 0 | True | 0 | 0 | 0 | 142.2 | 994.2 |
| 2016 | 366 | 366 | 0 | 0 | True | 0 | 0 | 10 | 188.0 | 1002.8 |
| 2017 | 365 | 365 | 0 | 0 | True | 0 | 0 | 126 | 208.7 | 1219.1 |
| 2018 | 365 | 365 | 0 | 0 | True | 0 | 0 | 93 | 267.9 | 1139.6 |
| 2019 | 365 | 365 | 0 | 0 | True | 0 | 0 | 17 | 222.5 | 1050.2 |
| 2020 | 366 | 366 | 0 | 0 | True | 0 | 0 | 3 | 173.4 | 1065.5 |
| 2021 | 365 | 365 | 0 | 0 | True | 0 | 0 | 31 | 210.7 | 959.8 |
| 2022 | 365 | 365 | 0 | 0 | True | 0 | 0 | 175 | 336.3 | 1084.8 |
| 2023 | 365 | 365 | 0 | 0 | True | 0 | 0 | 4 | 162.0 | 1044.3 |
| 2024 | 366 | 366 | 0 | 0 | True | 0 | 0 | 2 | 182.4 | 780.6 |
| 2025 | 365 | 365 | 0 | 0 | True | 0 | 0 | 4 | 164.4 | 1097.1 |
| 2026 | 30 | 30 | 0 | 0 | True | 0 | 0 | 0 | 129.2 | 223.5 |

## Annual totals (complete calendar years only)

Years used: 2000–2025 (26 years).

| location_id | district | province | annual_mean_mm | annual_min_mm | annual_max_mm |
|---|---|---|---|---|---|
| ZMB-D-0901 | Livingstone | Southern | 682.3 | 334.8 | 1112.6 |
| ZMB-D-1008 | Mwandi | Western | 696.9 | 373.4 | 1065.5 |
| ZMB-D-0505 | Chirundu | Lusaka | 708.6 | 463.9 | 912.4 |
| ZMB-D-0604 | Isoka | Muchinga | 1026.5 | 806.8 | 1337.8 |
| ZMB-D-0802 | Luwingu | Northern | 1431.1 | 1070.7 | 1857.4 |
| ZMB-D-0805 | Mporokoso | Northern | 1440.3 | 1164.8 | 1756.1 |
| ZMB-D-0707 | Ikelenge | North-Western | 1493.5 | 1290.4 | 1911.5 |

Across all districts: mean annual total 1048 mm (range of district means 682–1493 mm). Full table: `reports/chirps_annual_totals_by_location.csv`.

## Mean monthly totals (all districts)

| month | mean_monthly_total_mm |
|---|---|
| 1 | 239.0 |
| 2 | 200.4 |
| 3 | 167.0 |
| 4 | 54.1 |
| 5 | 6.5 |
| 6 | 0.5 |
| 7 | 0.1 |
| 8 | 0.2 |
| 9 | 2.5 |
| 10 | 25.4 |
| 11 | 120.0 |
| 12 | 226.0 |

The expected Zambian regime — a November–March rainy season and near-zero May–September — is the check here.

## Comparison with NASA POWER PRECTOTCORR (independent products; not forced to agree)

- Overlapping location-days: 988689
- Daily correlation: median 0.521 (range 0.391–0.589)
- Monthly-total correlation: median 0.902 (range 0.839–0.936)
- Mean annual rainfall, all districts: CHIRPS 1036 mm vs NASA POWER 964 mm (CHIRPS − POWER median +8.7%)
- Wet-day (≥1 mm) agreement: median 88.7% of days

Selected districts:

| district | province | daily_r | monthly_r | chirps_mean_annual_mm | power_mean_annual_mm | chirps_minus_power_pct |
|---|---|---|---|---|---|---|
| Lusaka | Lusaka | 0.558 | 0.906 | 850.390 | 793.273 | 7.200 |
| Kalabo | Western | 0.489 | 0.911 | 915.589 | 861.224 | 6.313 |
| Mongu | Western | 0.542 | 0.927 | 936.679 | 874.485 | 7.112 |
| Chipata | Eastern | 0.549 | 0.879 | 1155.782 | 977.319 | 18.260 |
| Kasama | Northern | 0.539 | 0.901 | 1267.691 | 1090.798 | 16.217 |
| Livingstone | Southern | 0.554 | 0.905 | 678.424 | 638.880 | 6.190 |
| Solwezi | North-Western | 0.504 | 0.902 | 1221.565 | 1168.106 | 4.577 |

Full table: `reports/chirps_vs_nasa_power_by_location.csv`. Daily agreement is expected to be modest: CHIRPS daily values are pentad totals disaggregated with ERA5 timing, while POWER is MERRA-2; monthly agreement is the more meaningful consistency check.

### Bias (CHIRPS − NASA POWER)

- Daily: mean +0.20 mm/day; median +0.00 mm/day (median over days when either source has ≥1 mm: +0.56); mean absolute difference 2.35 mm/day
- Monthly totals: mean +5.9 mm/month; median +0.1 mm/month

### Extreme-event behaviour (all location-days in the overlap)

| source | wet_day_frequency_pct | p99_all_days_mm | p99_wet_days_mm | max_mm | mean_annual_max_day_mm | days_gt_50mm_per_location_year |
|---|---|---|---|---|---|---|
| CHIRPS | 34.11 | 25.67 | 33.28 | 126.49 | 37.59 | 0.15 |
| NASA POWER | 34.84 | 27.94 | 40.05 | 338.30 | 47.99 | 0.59 |

Heavy-rain days (≥30 mm): both sources 527, CHIRPS only 4788, POWER only 7592 (overlap/union = 0.04). The two products rarely agree on *which* day is extreme, even when monthly totals agree.

Rainfall on DesInventar exact-day flood dates (273 location-dates; descriptive only, no target built): CHIRPS: median 3-day total ending on the flood date 1.9 mm vs 13.0 mm on a typical wet-season day (median percentile 30); NASA POWER: median 3-day total ending on the flood date 2.7 mm vs 10.5 mm on a typical wet-season day (median percentile 28)

### Are the two sources redundant?

High monthly correlation shows the two products describe the same seasonal rainfall regime; it does **not** show that either is correct. At the daily scale they differ substantially (correlation, heavy-day overlap above). Using both in one model would partly duplicate the seasonal signal; Stage 3 must justify the choice (e.g. one source as the primary feature set and the other as a sensitivity analysis, or a documented combination) rather than stacking both by default.

## Grid extremes above 300 mm/day (retained and flagged)

Each event is checked against the source: `original_daily_cog_mm` is the value re-read from the official CHC daily file at the same cell (equal → not an extraction artifact); `official_pentad_mm` is the CHIRPS v3 pentad total (equal to `stored_pentad_sum_mm` → not a daily-disaggregation artifact). Whether the pentad total itself is physically real cannot be proven from CHIRPS alone.

| date | max_mm | lat | lon | max_pixel_inside_zambia | cells_gt_100mm | cells_gt_100mm_inside_zambia | stored_pentad_sum_mm | official_pentad_mm | original_daily_cog_mm | nearest_district | nearest_point_km | nearest_point_chirps_mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2009-04-02 | 402.00 | -9.48 | 33.33 | False | 156 | 1 | 516.00 | 515.97 | 401.96 | Isoka | 76.00 | 30.00 |
| 2022-04-27 | 336.30 | -9.33 | 33.63 | False | 116 | 0 | 776.60 | 776.59 | 336.35 | Isoka | 110.00 | 14.40 |

**2009-04-02 (402 mm):** identical in the official file and our copy (not an extraction artifact); the 1–5 April daily values sum to the official pentad total (not a disaggregation artifact). The cluster of >100 mm cells lies at the north-east edge of the window, largely outside Zambia (Malawi/Tanzania border), and the nearest district points (Nakonde, Isoka) received 20–30 mm that day. Classification: **plausible but unverified extreme in the source product — retained and flagged; it does not enter any district series.**

## NASA POWER anomalies

See `reports/nasa_power_anomaly_investigation.md`.

## Verdict

**COMPLETE** — every day of the required window is present with no missing or negative values.
