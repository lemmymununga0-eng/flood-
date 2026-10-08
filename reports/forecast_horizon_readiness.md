# Forecast-horizon readiness (no targets built)

_Generated 2026-10-07T20:24:28+00:00 by `scripts/check_forecast_horizon_readiness.py`._

Counts are distinct district-days with a flood record, after resolving records to the 101 districts. Uncertain, unlikely and no-exact-date records must not become negatives.

|   horizon_days |   high_confidence_district_days |   high_confidence_with_full_365d_history |   plus_uncertain_district_days |   districts_with_high_confidence_event |   high_confidence_events_in_glofas_reforecast_period | reforecast_lead_covers_horizon   | month_precision_records_usable                   | date_error_tolerance       | assessment                                                                              |
|---------------:|--------------------------------:|-----------------------------------------:|-------------------------------:|---------------------------------------:|-----------------------------------------------------:|:---------------------------------|:-------------------------------------------------|:---------------------------|:----------------------------------------------------------------------------------------|
|              1 |                              82 |                                       81 |                            166 |                                     49 |                                                   71 | True                             | no                                               | none — dates must be exact | weak: too few reliable exact dates; day-level date errors dominate                      |
|              3 |                              82 |                                       81 |                            166 |                                     49 |                                                   71 | True                             | no                                               | ±1 day                     | possible but fragile (date errors)                                                      |
|              7 |                              82 |                                       81 |                            166 |                                     49 |                                                   71 | True                             | no                                               | ±2–3 days                  | PRIMARY: supported (high-confidence dates; uncertain as sensitivity)                    |
|             14 |                              82 |                                       81 |                            166 |                                     49 |                                                   71 | True                             | no                                               | ±5 days                    | supported; more positives per event, less timing precision                              |
|             30 |                              82 |                                       81 |                            166 |                                     49 |                                                   71 | True                             | only for monthly-resolution sensitivity analysis | ±1–2 weeks                 | supported as a seasonal-risk horizon; little forecast skill expected from weather alone |

High-confidence district-days by year: {2000: 1, 2001: 3, 2006: 3, 2007: 2, 2008: 6, 2009: 4, 2011: 2, 2012: 6, 2013: 8, 2014: 19, 2015: 8, 2016: 6, 2017: 5, 2022: 1, 2023: 1, 2025: 2, 2026: 5}

## Predictor availability

- Daily weather (NASA POWER, CHIRPS, soil wetness): 1999-04-14 → 2026-01-30, no gaps — supports every horizon for prediction dates up to the last event.
- Static terrain/hydrology/land cover: time-invariant.
- Climate indices: monthly, lagged (ONI ≤ month(t)−2; Niño 3.4/DMI ≤ month(t)−1).
- GloFAS reanalysis (needs EWDS credentials): daily 1979–2026 — would add hydrological state on days ≤ t for all horizons.
- GloFAS v4.0 reforecasts (needs EWDS credentials): twice-weekly issues 2003-03 → 2023-11, leads 1–46 days — the only collected-or-planned archive that supports an honest *forecast* experiment at H+1…H+30.

## Conclusion

The raw data support H+3, H+7 (primary), H+14 and H+30 targets; H+1 is not defensible with these labels because even high-confidence DesInventar dates can be off by a day. The binding constraint at every horizon is the number of reliable event dates, not predictor availability.
