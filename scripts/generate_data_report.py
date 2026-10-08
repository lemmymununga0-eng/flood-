"""Generate docs/DATA_COLLECTION_REPORT.md and docs/DATA_DICTIONARY.md from the validation results.

Every number in the report is read from reports/validation_report.json and the collection
manifests, never typed by hand. Run scripts/validate_raw_data.py first.

Usage
  python scripts/generate_data_report.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, p, utc_now  # noqa: E402


def fmt_pct(x) -> str:
    return "—" if x is None else f"{x:.2f}%"


def table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |")
    return "\n".join(out)


def collection_report(cfg, v: dict) -> str:
    d, n, c, w = v["desinventar"], v["nasa_power"], v["chirps"], v["window"]
    rep = ROOT / cfg["paths"]["reports"]
    proc = ROOT / cfg["paths"]["processed"]
    win = json.loads((proc / "collection_window.json").read_text(encoding="utf-8"))
    inv = pd.read_csv(rep / "desinventar_event_type_inventory.csv")
    unres = pd.read_csv(proc / "unresolved_locations.csv")
    master = pd.read_csv(proc / "location_master.csv")
    fails = pd.read_csv(rep / "failed_requests.csv") if (rep / "failed_requests.csv").exists() else pd.DataFrame(
        columns=["source", "target", "error"])
    conflicts = pd.read_csv(rep / "boundary_file_code_conflicts.csv") if (rep / "boundary_file_code_conflicts.csv").exists() else pd.DataFrame()
    prov_json = ROOT / cfg["paths"]["raw_desinventar_original"] / "DI_export_zmb.provenance.json"
    prov = json.loads(prov_json.read_text(encoding="utf-8")) if prov_json.exists() else {}

    power_missing = max(n.get("missing_value_pct", {0: 0}).values()) if n.get("missing_value_pct") else None
    n_fail = lambda s: int((fails["source"] == s).sum())  # noqa: E731
    overview = pd.DataFrame([
        {"Dataset": "DesInventar flood events", "Source": "DesInventar Sendai (UNDRR) — Zambia",
         "Coverage": "Zambia (national database)", "Records": d["flood_records"],
         "Date Range": f"{d['date_range_all_valid_years'][0]}–{d['date_range_all_valid_years'][1]} (exact-day: "
                       f"{d['date_range_day_precision'][0]} → {d['date_range_day_precision'][1]})",
         "Missing Data": f"{100 * d['records_without_exact_day'] / d['flood_records']:.1f}% lack an exact day",
         "Status": "Collected"},
        {"Dataset": "NASA POWER daily weather", "Source": "NASA LaRC POWER Daily API",
         "Coverage": f"Global product; {n.get('locations_present')} Zambian district points",
         "Records": n.get("total_observations"), "Date Range": " → ".join(n.get("date_range", ["", ""])),
         "Missing Data": f"max {fmt_pct(power_missing)} per variable",
         "Status": "Collected" if not n.get("locations_missing") else "Partial"},
        {"Dataset": "CHIRPS v3.0 daily rainfall", "Source": "UCSB Climate Hazards Center",
         "Coverage": "Quasi-global product; Zambia window 0.05°",
         "Records": f"{c.get('days_present')} days × {c['grid']['n_lat']}×{c['grid']['n_lon']} px" if c.get("grid") else "—",
         "Date Range": " → ".join(c.get("date_range", ["", ""])),
         "Missing Data": f"{c.get('missing_dates_count')} days; {fmt_pct(c.get('missing_pixel_pct'))} pixels",
         "Status": "Collected" if c.get("missing_dates_count") == 0 else "Partial"},
    ])

    L = ["# FloodShield-Zambia — Stage 1 Data Collection Report", "",
         f"_Generated {utc_now()} by `scripts/generate_data_report.py` from `reports/validation_report.json`._", "",
         "Stage 1 scope: **collect → store → validate → document raw data.** No target variable "
         "(`flood_next_7_days`) was created, and no model was trained or evaluated. No earlier model, "
         "prediction, label or processed dataset was reused.", "",
         "## Summary", "", table(overview), "",
         "## Collection window", "",
         f"Weather sources were collected for **{w['start']} → {w['end']}**. This window was derived from the "
         f"valid DesInventar flood dates ({win['earliest_flood_date']} → {win['latest_flood_date']}), extended "
         f"{win['lookback_days']} days back for antecedent conditions and {win['horizon_days']} days forward for "
         f"the (t, t+7] target window. Basis: {win['basis']}.", "",
         "## DesInventar", "",
         f"- Original export: `data/raw/desinventar/original/DI_export_zmb.zip` "
         f"({prov.get('bytes', '?')} bytes, sha256 `{prov.get('sha256', '?')[:16]}…`, retrieved {prov.get('retrieved_utc', '?')}).",
         f"- Total records (all hazard types): **{d['total_records_all_types']}**",
         f"- Flood records: **{d['flood_records']}** — {d['flood_records_by_type']}",
         f"- Date precision: {d['date_precision']} → **{d['records_without_exact_day']}** flood records "
         "have no exact day and cannot be placed in a 7-day window without further evidence.",
         f"- Exact-day date range: {d['date_range_day_precision'][0]} → {d['date_range_day_precision'][1]}",
         f"- Suspicious dates: {d['suspicious_dates']}",
         f"- Provinces represented: {d['provinces_represented']}; districts represented: {d['districts_represented']}",
         f"- Record identity: `serial` is re-used ({d.get('duplicate_serial_numbers')} flood records share a serial with another); "
         f"`clave` is unique ({d.get('duplicate_record_ids')} duplicates) and is used as `record_id`.",
         f"- Exact duplicate records: {d['exact_duplicate_records']} ({d['exact_duplicate_groups']} groups); "
         f"probable duplicates (same type, district, date and place text): {d['probable_duplicate_records']}; "
         f"records sharing a district and exact day: {d['same_district_same_day_records']} (may be distinct places — not merged).",
         f"- Records without a district: {d['missing_district']}; records with their own coordinates: "
         f"{d['records_with_coordinates']} (all others rely on the district point).",
         f"- Invalid numeric consequence values: {d['invalid_numeric_fields'] or 'none'}",
         f"- Location resolution of flood records: {d['location_resolution']}", "",
         "### Province distribution (flood records)", "",
         table(pd.DataFrame(list(d["province_distribution"].items()), columns=["Province", "Records"])), "",
         "### Event types and the flood definition", "",
         "Included as floods: `FLOOD`, `FLASH FLOODS`. Other categories were inventoried, not assumed to be floods. "
         "`records_with_explicit_flood_words` counts records whose text mentions flood/inundation/overflow; those are listed in "
         "`reports/desinventar_flood_keyword_hits.csv` **for the researcher to confirm**; none were included.", "",
         table(inv[inv["records"] > 0]), "",
         "## Location master", "",
         f"- `data/processed/location_master.csv`: **{len(master)}** districts (the DesInventar level-1 geography); "
         f"coordinate quality {master['coordinate_quality'].value_counts().to_dict()}.",
         f"- Districts with ≥1 flood record: {(master['n_flood_records'] > 0).sum()}; with ≥1 exact-day flood record: "
         f"{(master['n_flood_records_day_precision'] > 0).sum()}.",
         f"- Unresolved: `data/processed/unresolved_locations.csv` ({len(unres)} rows, "
         f"{int(unres['n_records'].sum()) if len(unres) else 0} flood records).",
         "- Sub-district place text (`lugar`) is preserved verbatim but not geocoded: it is free text "
         "(villages, wards, schools) with no reliable gazetteer match, so no coordinates were invented for it.",
         ]
    if len(conflicts):
        L.append(f"- Boundary-file issue: {len(conflicts)} polygon(s) in the DesInventar `districts.shp` share a code with a "
                 "different DesInventar district (" + ", ".join(f"{r.NAME} → {r.DATAB_DIST}" for r in conflicts.itertuples())
                 + "). They were not used for verification; see `reports/boundary_file_code_conflicts.csv`.")
    L += ["", "### Unresolved locations", "", table(unres[["original_location", "province", "reason_unresolved", "status",
                                                          "n_records", "record_ids"]]) if len(unres) else "None.", "",
          "## NASA POWER", "",
          f"- Locations: {n.get('locations_present')} of {n.get('locations_expected')} expected; missing: {n.get('locations_missing') or 'none'}",
          f"- Date range: {n.get('date_range')}; expected days per location: {n.get('expected_days_per_location')}",
          f"- Total observations (location-days): **{n.get('total_observations')}**",
          f"- Duplicate location-dates: {n.get('duplicate_location_dates')}",
          f"- Locations with incomplete coverage: {len(n.get('locations_incomplete_coverage', {}))}",
          f"- Failed API requests: {n_fail('nasa_power')} attempts; outstanding: "
          f"{(v.get('failures', {}).get('nasa_power') or {}).get('outstanding', [])}",
          f"- Flagged values (kept, not altered): {n.get('flagged_values') or 'none'}",
          f"- Groups of districts that fall in the same NASA POWER grid cell (identical series): "
          f"{len(n.get('locations_sharing_identical_series', []))} — "
          f"{n.get('locations_sharing_identical_series')}", "",
          "| Variable | Missing % | Missing count | Min | Mean | Max |", "|---|---:|---:|---:|---:|---:|"]
    for var, pct in n.get("missing_value_pct", {}).items():
        s = n["summary_stats"][var]
        L.append(f"| {var} | {pct:.4f}% | {n['missing_value_count'][var]} | {s['min']} | {s['mean']} | {s['max']} |")
    L += ["", "## CHIRPS v3.0", "",
          f"- Variant: daily `{cfg['chirps']['variant']}` (`{cfg['chirps']['stream']}`), 0.05°; files: {c.get('files')} yearly NetCDFs",
          f"- Date range: {c.get('date_range')}; days present {c.get('days_present')} of {c.get('days_expected')}; "
          f"missing days: {c.get('missing_dates_count')}; duplicate days: {c.get('duplicate_dates')}",
          f"- Spatial coverage: {c.get('grid')}",
          f"- Pixel-days: {c.get('pixel_days')}; missing/no-data: {fmt_pct(c.get('missing_pixel_pct'))}; negative: {c.get('negative_pixel_days')}",
          f"- Failed request attempts logged: {n_fail('chirps')}; recovered on re-run: "
          f"{(v.get('failures', {}).get('chirps') or {}).get('recovered_on_rerun', 0)}; outstanding dates: "
          f"{(v.get('failures', {}).get('chirps') or {}).get('outstanding_dates', [])}",
          f"- Location-master points inside the grid: {c.get('locations_inside_grid')} (outside: {c.get('locations_outside_grid')})",
          f"- Nearest-pixel point extraction: {c.get('point_extraction_rows')} rows, missing {fmt_pct(c.get('point_extraction_missing_pct'))}, "
          f"duplicates {c.get('point_extraction_duplicates')}", "",
          "## Cross-source rainfall sanity check (not a feature)", "",
          f"{v.get('cross_source') or 'not available'}", "",
          "NASA POWER `PRECTOTCORR` (MERRA-2 based, ~0.5° grid) and CHIRPS (0.05°) are kept as separate sources; "
          "neither replaces the other.", "",
          "## Failed requests", "",
          (table(fails.groupby(["source"]).size().rename("failed_attempts").reset_index()) if len(fails) else "None."), "",
          f"Recovery status: {v.get('failures')}. A failure counts as *recovered* when the same item was "
          "successfully retrieved on a later run; *outstanding* items are still missing.", "",
          "## Raw-data integrity", "",
          f"{v.get('checksums')} (`reports/raw_checksums.csv`). Raw files are written once; cleaning never overwrites them.", "",
          "## Data-quality issues to carry into Stage 2", "",
          f"1. **{d['records_without_exact_day']} of {d['flood_records']} flood records ({100 * d['records_without_exact_day'] / d['flood_records']:.0f}%) have no exact day** "
          "(year-only or month-only). They cannot be used as positives in a 7-day target and must not be treated as negatives.",
          "2. **Reporting is uneven in time** (see `records_by_year` in the validation report): absence of a DesInventar "
          "record does not prove absence of flooding.",
          "3. **Spatial unit is the district.** One point per district; weather for large districts is represented by "
          "a single point. NASA POWER's coarse grid means some neighbouring districts share identical series.",
          f"4. {d['probable_duplicate_records']} probable-duplicate and {d['same_district_same_day_records']} same-district-same-day "
          "records need a de-duplication rule before targets are built.",
          "5. Consequence fields (deaths, houses, affected people…) are post-event information and must never be used as predictors.",
          "6. Possibly flood-related records in other categories await the researcher's inclusion decision.",
          "", "## Leakage rule for later stages", "",
          "For a prediction date *t*, features may use only information available on or before *t*; "
          "`flood_next_7_days` = 1 only if a qualifying flood starts in (t, t+7]. Weather after *t* and any "
          "post-event consequence field are excluded from features.", ""]
    return "\n".join(L)


STATIC_DICTIONARY = """# FloodShield-Zambia — Data Dictionary (Stage 1 raw and processed data)

_Generated by `scripts/generate_data_report.py`. Units come from the official source metadata:
NASA POWER units from the API response `parameters` block and the POWER parameter manager
(`/api/system/manager/parameters`); CHIRPS units from the CHIRPS v3.0 NetCDF `units` attribute (`mm/day`);
DesInventar extension-field labels from the export's own `diccionario` table. Where a source does not state a
unit, the table says so rather than guessing._

## NASA POWER — `data/raw/nasa_power/nasa_power_daily.csv`

Raw responses: `data/raw/nasa_power/daily_weather/<location_id>/*.json` (verbatim API output; fill value −999).

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| location_id | Location master ID (district) | location master | — | string | No |
| latitude | Requested point latitude (location master) | location master | decimal degrees (WGS84) | float | No |
| longitude | Requested point longitude | location master | decimal degrees (WGS84) | float | No |
| date | Day of observation, local solar time (LST) | NASA POWER | YYYY-MM-DD | date | No |
| PRECTOTCORR | Precipitation Corrected — "the average MERRA-2 bias corrected total precipitation at the surface of the earth" | NASA POWER | mm/day | float | Yes (fill −999 → empty) |
| T2M | Temperature at 2 Meters — average air (dry bulb) temperature at 2 m | NASA POWER | °C | float | Yes |
| T2M_MAX | Temperature at 2 Meters Maximum — maximum hourly air temperature at 2 m in the day | NASA POWER | °C | float | Yes |
| T2M_MIN | Temperature at 2 Meters Minimum — minimum hourly air temperature at 2 m in the day | NASA POWER | °C | float | Yes |
| RH2M | Relative Humidity at 2 Meters — ratio of vapour pressure to saturation vapour pressure over water | NASA POWER | % | float | Yes |
| WS10M | Wind Speed at 10 Meters — average wind speed at 10 m | NASA POWER | m/s | float | Yes |
| power_point_longitude / power_point_latitude | Point echoed by the API response geometry | NASA POWER | decimal degrees | float | No |
| source | API name and version | NASA POWER | — | string | No |
| community | POWER user community requested (AG) | request | — | string | No |
| time_standard | Time standard of daily aggregation (LST) | request | — | string | No |
| retrieval_timestamp_utc | When the raw response was retrieved | pipeline | ISO-8601 UTC | string | No |
| raw_file | Path of the verbatim JSON the row came from | pipeline | — | string | No |

## CHIRPS v3.0 — `data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.<YYYY>.nc`

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| precip (time, lat, lon) | CHIRPS v3.0 daily precipitation (pentads disaggregated to days with ERA5 — `rnl`), values copied unchanged | CHC UCSB | mm/day | float32 | Yes (none expected over land) |
| time | Day | CHC file name | date | datetime64 | No |
| lat / lon | Pixel-centre coordinates, 0.05° grid | CHC COG geotransform | decimal degrees (WGS84) | float64 | No |
| source_url (time) | COG the day was read from | pipeline | — | string | No |
| retrieved_utc (time) | Retrieval timestamp | pipeline | ISO-8601 UTC | string | No |

`data/raw/chirps/chirps_manifest.csv`: date, url, status (`ok`/`failed`/`not_available`), retrieved_utc,
n_pixels, n_nodata, n_negative, min, max, mean (mm/day), error.

## CHIRPS point extraction — `data/processed/chirps_daily_at_locations.csv`

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| location_id | Location master ID | location master | — | string | No |
| date | Day | CHIRPS | YYYY-MM-DD | date | No |
| chirps_precip_mm | Value of the CHIRPS pixel nearest the location point (no interpolation, no aggregation) | CHIRPS v3.0 | mm/day | float | Yes |
| pixel_lat / pixel_lon | Centre of the pixel used | CHIRPS grid | decimal degrees | float | No |
| source_file | Yearly NetCDF the value came from | pipeline | — | string | No |

## Location master — `data/processed/location_master.csv`

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| location_id | `ZMB-D-` + DesInventar district code | derived | — | string | No |
| location_name | Normalised district name (HTML entities decoded, case normalised) | derived from DesInventar | — | string | No |
| location_name_original | District name exactly as in the DesInventar export | DesInventar `regiones` | — | string | No |
| district / province | Normalised district / province names | DesInventar `regiones` | — | string | No |
| district_code / province_code | DesInventar geography codes (level 1 / level 0) | DesInventar | — | string | No |
| latitude / longitude | District point | see coordinate_source | decimal degrees (WGS84) | float | Only if unresolved |
| coordinate_source | Where the coordinate came from | pipeline | — | string | No |
| coordinate_quality | `district_point_verified_inside_polygon`, `district_polygon_representative_point`, or `unresolved` | pipeline | — | string | No |
| spatial_unit | Always "district (DesInventar level 1)" | pipeline | — | string | No |
| district_area_km2 | Polygon area (EPSG:6933 equal-area) | DesInventar `districts.shp` | km² | float | Yes |
| approx_km_to_polygon_centroid | Distance from the point to the polygon centroid (approximate, 111 km/°) | derived | km | float | Yes |
| in_boundary_file | District has a polygon in `districts.shp` | derived | — | bool | No |
| n_flood_records / n_flood_records_day_precision | Flood records coded to the district (all / exact-day only) | DesInventar | count | int | No |
| in_weather_collection | Weather was collected for this location | config | — | bool | No |
| created_utc | Build time | pipeline | ISO-8601 UTC | string | No |

## Unresolved locations — `data/processed/unresolved_locations.csv`

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| original_location | `lugar` text exactly as recorded | DesInventar | — | string | Yes |
| district / province | As recorded (district empty when missing) | DesInventar | — | string | Yes |
| reason_unresolved | Why a district point could not be assigned | pipeline | — | string | No |
| attempted_sources | Sources tried | pipeline | — | string | No |
| status | `unresolved` or `unresolved_at_district_level_province_known` | pipeline | — | string | No |
| resolution_level | `province_only`, `unresolved` or `geography` | pipeline | — | string | No |
| n_records / record_ids | Affected DesInventar records (record_id = DesInventar `clave`) | DesInventar | count / ids | int / string | No |

## DesInventar flood events — `data/processed/desinventar_flood_events.csv`

All columns of the DesInventar record (`fichas`) joined with its extension fields (`extension`) are kept verbatim
as strings. Columns added by the pipeline:

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| event_start_date | Most precise start date the record supports: `YYYY-MM-DD`, `YYYY-MM` or `YYYY` | parsed from fechano/fechames/fechadia | date text | string | Yes (invalid dates) |
| date_precision | `day`, `month`, `year` or `invalid` | pipeline | — | string | No |
| date_quality_flag | e.g. `implausible_year:211`, `date_after_retrieval` | pipeline | — | string | Yes (empty = no issue) |
| event_end_date_from_duration | start + duracion − 1, only when DesInventar states duracion > 0 and the day is known | derived | YYYY-MM-DD | string | Yes |
| province_original / district_original / location_original | Copies of name0 / name1 / lugar, verbatim | DesInventar | — | string | Yes |
| retrieved_utc / source | Provenance of the record table | pipeline | — | string | No |

### DesInventar core fields (record table `fichas`)

Consequence fields are **post-event information: audit only, never predictors.** The export does not state
units for the core fields; the descriptions follow DesInventar's standard field meanings.

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| serial | Datacard serial number as entered — **not unique in this database** | DesInventar | — | string | No |
| clave | Database record key — unique; used as `record_id` throughout the pipeline | DesInventar | — | string | No |
| uu_id | Record UUID | DesInventar | — | string | No |
| level0 / name0 | Province code / name | DesInventar | — | string | No |
| level1 / name1 | District code / name | DesInventar | — | string | Yes |
| level2 / name2 | Sub-district level (unused in Zambia) | DesInventar | — | string | Yes |
| evento | Hazard/event type (e.g. FLOOD, FLASH FLOODS) | DesInventar | — | string | No |
| glide | GLIDE number (empty in this database) | DesInventar | — | string | Yes |
| lugar | Free-text place (village, ward, school…) | DesInventar | — | string | Yes |
| fechano / fechames / fechadia | Event year / month / day (0 = unknown) | DesInventar | — | string | month/day may be 0 |
| duracion | Event duration | DesInventar | days | string | Yes (0 = not stated) |
| causa / descausa | Cause / cause description | DesInventar | — | string | Yes |
| muertos | Deaths | DesInventar | people | string | Yes |
| heridos | Injured | DesInventar | people | string | Yes |
| desaparece | Missing | DesInventar | people | string | Yes |
| afectados | Affected people | DesInventar | people | string | Yes |
| damnificados | Victims (people suffering severe damage) | DesInventar | people | string | Yes |
| evacuados / reubicados | Evacuated / relocated | DesInventar | people | string | Yes |
| vivdest | Houses destroyed | DesInventar | houses | string | Yes |
| vivafec | Houses damaged | DesInventar | houses | string | Yes |
| nhectareas | Crops and woods affected | DesInventar | hectares | string | Yes |
| cabezas | Livestock lost | DesInventar | head | string | Yes |
| kmvias | Roads affected (length; unit not stated in the export) | DesInventar | not stated | string | Yes |
| nhospitales / nescuelas | Health centres / schools affected | DesInventar | count | string | Yes |
| valorloc / valorus | Losses in local currency / US dollars | DesInventar | local currency (kwacha; old ZMK vs rebased ZMW not stated) / USD | string | Yes |
| socorro, salud, educacion, agropecuario, industrias, acueducto, alcantarillado, energia, comunicaciones, transporte | Sector-affected indicators | DesInventar | indicator (non-zero = sector affected) | string | Yes |
| hay_* | "Quantity not given but effect present" indicators for the matching count field | DesInventar | indicator (−1 = yes) | string | Yes |
| otros | Other losses (free text) | DesInventar | — | string | Yes |
| fuentes | Information source | DesInventar | — | string | Yes |
| di_comments | Record comments | DesInventar | — | string | Yes |
| latitude / longitude | Record coordinates (0 = not recorded) | DesInventar | decimal degrees | string | Yes |
| fechafec / fechapor | Data-entry date / entered by | DesInventar | — | string | Yes |
| approved / defaultab | Workflow status fields | DesInventar | — | string | Yes |
| magnitud2 | Magnitude text | DesInventar | — | string | Yes |

### DesInventar extension fields (from the export's `diccionario` table)

"#" in a label is DesInventar's own count notation.

"""


STAGE2_DICTIONARY = """

## Stage 2 — static district attributes (`data/processed/`)

`*_point_*` = value at the location-master coordinate; `*_district_*` = zonal statistic over the district polygon
(cells whose centre is inside). Distances/areas in ESRI:102022 (Africa Albers Equal Area).

### `district_terrain_hydrology.csv` (HydroSHEDS v1)

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| location_id | Location master ID | location master | — | string | No |
| dem_cells | DEM cells inside the district | derived | count | int | No |
| elev_point_m | Elevation of the DEM cell at the point | HydroSHEDS DEM 15″ | m | float | Only if point cell is nodata |
| slope_point_deg | Slope at the point | derived from DEM | degrees | float | Same |
| elev_district_mean_m / _median_m / _min_m / _max_m / _std_m / _p10_m / _p90_m | Elevation statistics over the district | HydroSHEDS DEM 15″ | m | float | No |
| slope_district_mean_deg / _median_deg | Slope statistics (central differences, geodesic cell size) | derived from DEM | degrees | float | No |
| flat_fraction_slope_lt_0.5deg | Share of district cells with slope < 0.5° | derived | fraction 0–1 | float | No |
| dist_point_to_river_upland_ge_{100,1000,10000}km2_km | Distance from the point to the nearest HydroRIVERS reach whose upstream area is ≥ threshold | HydroRIVERS v1.0 | km | float | No |
| upland_km2_of_nearest_river_ge_{…}km2 | Upstream area of that nearest reach | HydroRIVERS `UPLAND_SKM` | km² | float | No |
| district_area_km2 | Polygon area | DesInventar districts.shp | km² | float | No |
| max_upland_km2_in_district | Largest upstream area of any reach intersecting the district (flow-accumulation proxy) | HydroRIVERS `UPLAND_SKM` | km² | float | No |
| max_dis_av_cms_in_district | Largest modelled long-term mean discharge of any reach in the district | HydroRIVERS `DIS_AV_CMS` | m³/s | float | No |
| river_density_upland_ge_100km2_km_per_km2 | Length of reaches (upstream ≥100 km²) inside the district per district area | HydroRIVERS | km/km² | float | No |
| frac_district_within_5km_of_river_upland_ge_1000km2 | Share of district area within 5 km of a reach with upstream area ≥1,000 km² | HydroRIVERS | fraction 0–1 | float | No |
| hybas_lev04_id_point / hybas_lev06_id_point | HydroBASINS basin containing the point | HydroBASINS v1c | ID | int | No |
| hybas_main_basin_id_point | `MAIN_BAS` (main river basin) of the point | HydroBASINS v1c | ID | int | No |
| hybas_lev04_up_area_km2_point / hybas_lev06_up_area_km2_point | Total upstream area of the basin containing the point | HydroBASINS `UP_AREA` | km² | float | No |
| hybas_lev04_id_district_dominant / _share | Level-4 basin covering most of the district, and its share | HydroBASINS | ID / fraction | int / float | No |

### `district_landcover.csv` (ESA WorldCover 2021 v200, 1/4 overview ≈ 40 m)

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| pct_tree_cover, pct_shrubland, pct_grassland, pct_cropland, pct_built_up, pct_bare_sparse, pct_snow_ice, pct_permanent_water, pct_herbaceous_wetland, pct_mangroves, pct_moss_lichen | Share of district area per class (cells weighted by cos latitude) | ESA WorldCover | % | float | No |
| class_at_point | Class of the cell at the location point | ESA WorldCover | category | string | No |
| cells_sampled / nodata_cells | Valid / no-data overview cells inside the district | derived | count | int | No |
| overview_factor | Decimation factor of the overview used (4 = ~40 m) | config | — | int | No |

### `exposure/worldpop_district_exposure.csv` (WorldPop, EXPOSURE layer — not an occurrence predictor)

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| location_id, population_year | District and population year (2000–2020) | — | — / year | string / int | No |
| population | Sum of cells whose centre lies in the district | WorldPop unconstrained 1 km (not UN-adjusted) | people | float | No |
| population_density_per_km2 / district_area_km2 | population ÷ area / polygon area | derived | people per km² / km² | float | No |
| pop_in_point_cell | Value of the 1 km cell at the location point | WorldPop | people per cell | float | No |
| source, version | Provider; product title, resolution, adjustment and DOI from the WorldPop API record | WorldPop API | — | string | No |
| source_file, role | Raster used; fixed text "EXPOSURE ONLY - not a flood-occurrence predictor" | pipeline | — | string | No |

### `data/raw/nasa_power/nasa_power_daily_soil_moisture.csv` (optional experiment)

Same layout as `nasa_power_daily.csv`, with:

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| GWETTOP | Surface Soil Wetness — water in the upper 5 cm of soil | NASA POWER (MERRA-2) | fraction 0 (dry) – 1 (saturated) | float | Yes (fill −999 → empty) |
| GWETROOT | Root Zone Soil Wetness — water available in the root zone (~upper 1 m) | NASA POWER | fraction 0–1 | float | Yes |
| GWETPROF | Profile Soil Moisture — surface down to bedrock | NASA POWER | fraction 0–1 | float | Yes |

### `climate_indices_monthly.csv` and `climate_iod_weekly_bom.csv`

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| year, month | Calendar month the value refers to | — | — | int | No |
| oni | Oceanic Niño Index — 3-month running-mean Niño 3.4 SST anomaly, season centred on `month` | NOAA CPC (ERSST.v5) | °C | float | Yes (not yet published) |
| oni_total_c / oni_season | Season mean SST / season label (e.g. DJF) | NOAA CPC | °C / — | float / string | Yes |
| nino34_sst_c / nino34_anom | Monthly Niño 3.4 SST and anomaly vs 1991–2020 | NOAA CPC | °C | float | Yes |
| dmi_hadisst | Dipole Mode Index (western minus eastern tropical Indian Ocean SST anomaly) | NOAA PSL (HadISST1.1) | °C | float | Yes |
| week_start, week_end, iod_bom | Weekly IOD index | Australian Bureau of Meteorology | dates / °C | date / float | No |

**Lag rule (leakage):** for a prediction date *t*, ONI may be used up to the season centred on month(t) − 2, and
Niño 3.4 / DMI up to month(t) − 1 (see `docs/DATA_REQUIREMENTS_MATRIX.md` §4).

### `dfo_zambia_events.csv` (validation only)

All columns of the DFO archive spreadsheet kept verbatim for rows mentioning Zambia (e.g. `ID`, `GlideNumber`,
`Country`, `OtherCountry`, `long`, `lat`, `Area` (km²), `Began`, `Ended`, `Validation`, `Dead`, `Displaced`,
`MainCause`, `Severity`), plus `source_file`. Post-event information: never a predictor.
"""


FINAL_DICTIONARY = """

## Final Stage 2 tables

### `hydrology/glofas_district_extraction_points.csv` (GloFAS v4 static maps)

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| A_centroid_lat/lon, A_upstream_km2, A_on_significant_river | GloFAS cell at the district point, its upstream area, and whether that is >= 1,000 km2 | GloFAS upArea | deg, km2, bool | float/bool | No |
| B_zonal_cells | Number of GloFAS cells whose centre lies in the district (used for runoff / soil-wetness means) | derived | count | int | No |
| C_main_river_lat/lon, C_upstream_km2 | Cell in the district with the largest upstream area (main river) - discharge extraction point | GloFAS upArea | deg, km2 | float | No |
| D_nearest_river_lat/lon, D_upstream_km2, D_distance_km, D_inside_district | Nearest cell with upstream area >= 1,000 km2 to the district point (sensitivity variant) | GloFAS upArea | deg, km2, km, bool | float/bool | No |
| hydrorivers_max_upland_km2, C_vs_hydrorivers_ratio | Independent HydroRIVERS comparison | HydroRIVERS | km2, ratio | float | No |

### `hydrology/glofas_historical_district_daily.csv` (created by extract_glofas.py once GloFAS is downloaded)

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| date | Day the 24-h value describes (period start; GRIB valid_time minus step) | GloFAS v4.0 | date | date | No |
| discharge_main_river_m3s / discharge_nearest_river_m3s | Mean river discharge over the day at points C / D | GloFAS v4.0 historical | m3/s | float | Yes |
| runoff_district_mean | Runoff water equivalent (surface + subsurface), district mean | GloFAS v4.0 historical | m (water equivalent) per day | float | Yes |
| soil_wetness_index_district_mean | Root-zone soil wetness index, district mean | GloFAS v4.0 historical | dimensionless | float | Yes |

### `environmental/district_surface_water.csv` (JRC Global Surface Water v1.4)

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| pct_ever_water | Share of district area (cos-latitude weighted) that was water at least once 1984-2021 | JRC GSW occurrence | % | float | No |
| pct_intermittent_water_1_to_74 | Share with occurrence 1-74 % (seasonal / flooded land) | JRC GSW | % | float | No |
| pct_permanent_water_ge_75 | Share with occurrence >= 75 % | JRC GSW | % | float | No |
| mean_occurrence_pct | Area-weighted mean occurrence | JRC GSW | % | float | No |

### `desinventar_flood_event_audit.csv`

| Field | Description | Source | Unit | Type | Missing Allowed? |
|---|---|---|---|---|---|
| record_id, serial, event_type, event_date, date_precision, province, district, place_text, location_id | Event identity, date and location as recorded | DesInventar | - | string | Yes (location_id for province-only) |
| record_latitude / record_longitude | Record's own coordinates (only 1 record has them) | DesInventar | deg | float | Yes |
| description, source_reported | Cause + comments text; reporting source | DesInventar | - | string | Yes |
| flood_evidence | explicit_flood_text / rain_or_water_text / category_only | derived from text | - | string | No |
| date_confidence | HIGH-CONFIDENCE / UNCERTAIN / UNLIKELY EVENT DATE / NO EXACT DATE | derived (season, batches, admin text; no rainfall) | - | string | No |
| location_confidence | HIGH (own coordinates) / MEDIUM (district code) / LOW (province only) | derived | - | string | No |
"""


def dictionary(cfg) -> str:
    ext = ROOT / cfg["paths"]["raw_desinventar_extracted"] / "tables"
    dic = pd.read_csv(ext / "diccionario.csv", dtype=str, keep_default_na=False)
    tabs = pd.read_csv(ext / "extensiontabs.csv", dtype=str, keep_default_na=False).set_index("ntab")["svalue_en"]
    ftype = {"0": "text", "1": "integer", "2": "decimal", "3": "currency", "4": "date"}
    rows = ["| Field | Description | Source | Unit | Type | Missing Allowed? |", "|---|---|---|---|---|---|"]
    for r in dic.sort_values(["tabnumber", "orden"], key=lambda s: pd.to_numeric(s, errors="coerce")).itertuples():
        label = r.label_campo_en or r.label_campo
        unit = "count (#)" if "(#)" in label else ("hectares" if "(ha" in label.lower() else "as labelled; not stated")
        tab = tabs.get(r.tabnumber, r.tabnumber)
        rows.append(f"| {r.nombre_campo.lower()} | {label} [tab: {tab}] | DesInventar extension | {unit} | "
                    f"{ftype.get(r.fieldtype, r.fieldtype)} (stored as string) | Yes |")
    return STATIC_DICTIONARY + "\n".join(rows) + "\n" + STAGE2_DICTIONARY + FINAL_DICTIONARY


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("report", cfg)
    vpath = ROOT / cfg["paths"]["reports"] / "validation_report.json"
    if not vpath.exists():
        raise SystemExit("Run scripts/validate_raw_data.py first")
    v = json.loads(vpath.read_text(encoding="utf-8"))
    docs = p(cfg, "docs")
    (docs / "DATA_COLLECTION_REPORT.md").write_text(collection_report(cfg, v), encoding="utf-8")
    (docs / "DATA_DICTIONARY.md").write_text(dictionary(cfg), encoding="utf-8")
    logger.info("Wrote docs/DATA_COLLECTION_REPORT.md and docs/DATA_DICTIONARY.md")


if __name__ == "__main__":
    main()
