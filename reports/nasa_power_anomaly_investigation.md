# NASA POWER rainfall anomaly investigation

_Generated 2026-10-07T14:59:50+00:00 by `scripts/validate_chirps.py`. Values are investigated, not deleted._

## ZMB-D-0706 (Mwinilunga) — 2020-02-23: 338.3 mm/day

| date | PRECTOTCORR | chirps_precip_mm |
|---|---|---|
| 2020-02-20 | 8.75 | 1.28 |
| 2020-02-21 | 13.38 | 2.80 |
| 2020-02-22 | 6.79 | 8.02 |
| 2020-02-23 | 338.30 | 10.83 |
| 2020-02-24 | 53.71 | 4.07 |
| 2020-02-25 | 6.47 | 11.05 |
| 2020-02-26 | 9.74 | 12.51 |

- Highest NASA POWER values that day (all districts): ZMB-D-0706 338.3, ZMB-D-0906 98.2, ZMB-D-1008 74.8, ZMB-D-0904 70.8, ZMB-D-0604 49.3
- CHIRPS maximum anywhere in the Zambia window that day: 55.1 mm
- DesInventar flood records in this district within ±7 days: 0

## ZMB-D-0907 (Siavonga) — 2023-12-22: 303.64 mm/day

| date | PRECTOTCORR | chirps_precip_mm |
|---|---|---|
| 2023-12-19 | 12.16 | 11.15 |
| 2023-12-20 | 1.47 | 5.71 |
| 2023-12-21 | 3.00 | 8.92 |
| 2023-12-22 | 303.64 | 29.47 |
| 2023-12-23 | 77.46 | 18.72 |
| 2023-12-24 | 7.66 | 1.60 |
| 2023-12-25 | 6.41 | 6.37 |

- Highest NASA POWER values that day (all districts): ZMB-D-0907 303.6, ZMB-D-0505 162.7, ZMB-D-0507 140.5, ZMB-D-0501 140.5, ZMB-D-0110 137.2
- CHIRPS maximum anywhere in the Zambia window that day: 46.6 mm
- DesInventar flood records in this district within ±7 days: 0

## Interpretation

NASA POWER PRECTOTCORR is a bias-corrected MERRA-2 reanalysis field on a ~0.5° grid. Single-day totals above 300 mm at a district point are physically possible in convective storms but rare in Zambia; where CHIRPS on the same day is far lower, the value is most likely a reanalysis artefact. The values are kept unchanged and flagged (`reports/nasa_power_flagged_values.csv`). Stage 3 should decide explicitly whether to cap/winsorise rainfall features, using the same rule for every location.
