# Raw Data Validation Report

Generated 2026-10-07T20:25:25+00:00 by `scripts/validate_raw_data.py`. Values are flagged, never removed or changed.

## DesInventar (FLOOD + FLASH FLOODS)

- **total_records_all_types**: 2239
- **flood_records**: 444
- **flood_records_by_type**: {'FLOOD': 436, 'FLASH FLOODS': 8}
- **date_precision**: {'day': 276, 'year': 163, 'month': 3, 'invalid': 2}
- **date_range_day_precision**: ['2000-04-13', '2026-01-23']
- **date_range_all_valid_years**: ['2000', '2026']
- **suspicious_dates**: {'entered_before_event': 3, 'implausible_year:211': 1, 'implausible_year:201': 1}
- **exact_duplicate_records**: 0
- **probable_duplicate_records**: 54
- **same_district_same_day_records**: 79
- **missing_district**: 4
- **records_missing_coordinates**: 443
- **provinces_represented**: 10
- **districts_represented**: 82
- **invalid_numeric_fields**: {}
- **location_resolution**: {'district': 440, 'province_only': 4}

## NASA POWER

- **locations_expected**: 101
- **locations_present**: 101
- **locations_missing**: []
- **date_range**: ['1999-04-14', '2026-01-30']
- **expected_days_per_location**: 9789
- **total_observations**: 988689
- **missing_value_pct**: {'PRECTOTCORR': 0.0, 'T2M': 0.0, 'T2M_MAX': 0.0, 'T2M_MIN': 0.0, 'RH2M': 0.0, 'WS10M': 0.0}
- **duplicate_location_dates**: 0
- **flagged_values**: {'extreme_rain_check:PRECTOTCORR': 31, 'outside_bounds:PRECTOTCORR': 2}
- **api_failures**: 0
- **locations_incomplete_coverage**: 0
- **groups of locations sharing an identical series**: 8

## CHIRPS v3.0

- **files**: 28
- **date_range**: ['1999-04-14', '2026-01-30']
- **days_expected**: 9789
- **days_present**: 9789
- **missing_dates_count**: 0
- **duplicate_dates**: 0
- **grid**: {'lat_min': -18.175001164898276, 'lat_max': -8.125001015141606, 'lon_min': 21.925003008916974, 'lon_max': 33.775003185495734, 'n_lat': 202, 'n_lon': 238}
- **missing_pixel_pct**: 0.0
- **negative_pixel_days**: 0
- **download_status**: {'ok': 9378, 'failed': 713}
- **locations_outside_grid**: 0
- **point_extraction_missing_pct**: 0.0

## Failed requests

{'total_failed_attempts': 1057, 'chirps': {'failed_attempts': 988, 'recovered_on_rerun': 988, 'outstanding_dates': []}, 'global_surface_water': {'failed_attempts': 1, 'recovered_on_rerun': 1, 'outstanding': []}, 'glofas': {'failed_attempts': 1, 'recovered_on_rerun': 0, 'outstanding': ['credentials']}, 'glofas_static': {'failed_attempts': 1, 'recovered_on_rerun': 1, 'outstanding': []}, 'hydrosheds': {'failed_attempts': 4, 'recovered_on_rerun': 4, 'outstanding': []}, 'nasa_power_soil': {'failed_attempts': 46, 'recovered_on_rerun': 46, 'outstanding': []}, 'worldcover': {'failed_attempts': 16, 'recovered_on_rerun': 16, 'outstanding': []}}

## Cross-source rainfall sanity check

{'overlap_rows': 988689, 'monthly_total_corr_median': 0.902, 'monthly_total_corr_min': 0.839, 'daily_corr_median': 0.521, 'mean_daily_mm_power': 2.641, 'mean_daily_mm_chirps': 2.836}

## Raw file integrity

{'files_hashed': 130, 'files_with_recorded_hash': 102, 'mismatches': []}
