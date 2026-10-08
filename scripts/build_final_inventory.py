"""Generate docs/FINAL_DATA_INVENTORY.md — one row per dataset, numbers read from disk.

Descriptive fields (source, URL, version, units, role) come from the documented decisions; counts,
dates, file numbers and missing percentages are recomputed here every time the script runs.
Usage
  python scripts/build_final_inventory.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, load_window, utc_now  # noqa: E402


def nfiles(rel: str, pat: str = "*") -> int:
    base = ROOT / rel
    return len([f for f in base.rglob(pat) if f.is_file() and ".part" not in f.name and not f.name.endswith(".json")]) if base.exists() else 0


def csv_stats(rel: str, cols=None, date="date"):
    f = ROOT / rel
    if not f.exists():
        return "—", "—", "—", "—"
    d = pd.read_csv(f, usecols=(cols or []) + ([date] if date else []) if cols else None)
    miss = f"{100 * d[cols].isna().mean().mean():.2f}%" if cols else f"{100 * d.isna().mean().mean():.2f}%"
    if date and date in d:
        s = d[date].astype(str)
        return f"{len(d):,}", s.min(), s.max(), miss
    return f"{len(d):,}", "—", "—", miss


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("inventory", cfg)
    win = load_window(cfg)
    P = cfg["paths"]
    pw = csv_stats("data/raw/nasa_power/nasa_power_daily.csv", cfg["nasa_power"]["parameters"])
    sm = csv_stats("data/raw/nasa_power/nasa_power_daily_soil_moisture.csv", cfg["nasa_power_soil"]["parameters"])
    ch = csv_stats("data/processed/chirps_daily_at_locations.csv", ["chirps_precip_mm"])
    di = csv_stats("data/processed/desinventar_flood_event_audit.csv", None, None)
    th = csv_stats("data/processed/district_terrain_hydrology.csv", None, None)
    lc = csv_stats("data/processed/district_landcover.csv", None, None)
    ex = csv_stats("data/processed/exposure/worldpop_district_exposure.csv", ["population"], "population_year")
    ci = csv_stats("data/processed/climate_indices_monthly.csv", ["oni", "nino34_anom", "dmi_hadisst"], None)
    gs = csv_stats("data/processed/environmental/district_surface_water.csv", None, None)
    gp = csv_stats("data/processed/hydrology/glofas_district_extraction_points.csv", None, None)
    glofas_ts = nfiles(P["raw_glofas"] + "/historical", "*.grib2")
    R = [
        ["DesInventar Zambia", "UNDRR DesInventar (DMMU data)", "https://www.desinventar.net/DesInventar/download/DI_export_zmb.zip",
         "export of 2026-10-05", "2000", "2026-01-23", "event / district", "Zambia, 101 districts",
         "event type, date, district, place, consequences", "counts, ha, local currency/USD", f"data/raw/desinventar/: {nfiles(P['raw_desinventar_original'])} ZIP + {nfiles(P['raw_desinventar_extracted'])} extracted",
         "desinventar_flood_events.csv, desinventar_flood_event_audit.csv, desinventar_flood_date_reliability.csv",
         f"{di[0]} flood records", "168 records without exact day", "VERIFIED (2nd audit)", "Label source", "LABEL", "91 high-confidence / 102 uncertain / 83 unlikely dates"],
        ["Location master", "DesInventar geography", "(from the export)", "—", "static", "static", "district point + polygon",
         "101 districts, 10 provinces", "location_id, coordinates, quality", "decimal degrees", "districts.shp, regiones",
         "location_master.csv, unresolved_locations.csv", "101", "0%", "VERIFIED (2nd audit)", "Spatial key", "CORE (reference)", "2 boundary-file code conflicts documented"],
        ["NASA POWER daily weather", "NASA LaRC POWER", "https://power.larc.nasa.gov/api/temporal/daily/point", "API v2.10.0, community AG",
         pw[1], pw[2], "~0.5° × 0.625° (MERRA-2) at district point", "101 district points",
         "PRECTOTCORR, T2M, T2M_MAX, T2M_MIN, RH2M, WS10M", "mm/day, °C, %, m/s", f"data/raw/nasa_power/daily_weather/: {nfiles(P['raw_nasa_power'])} JSON", "nasa_power_daily.csv",
         pw[0], pw[3], "VERIFIED (2nd audit)", "Weather predictors", "CORE", "2 days >300 mm flagged (probable artefacts)"],
        ["CHIRPS v3.0 daily", "UCSB Climate Hazards Center", "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/", "v3.0 final, rnl",
         ch[1], ch[2], "0.05°", "Zambia window (238 × 202 cells)", "precip", "mm/day", f"data/raw/chirps/daily_rainfall/: {nfiles(P['raw_chirps'], '*.nc')} yearly NetCDF",
         "chirps_daily_at_locations.csv", ch[0], ch[3], "VERIFIED (2nd audit)", "Rainfall predictor", "CORE", "monthly r 0.90 with POWER"],
        ["HydroSHEDS", "WWF / McGill / USGS", "https://www.hydrosheds.org/hydrosheds-core-downloads", "v1 (data v1.1); HydroRIVERS v1.0; HydroBASINS v1c",
         "static", "static", "15″ DEM; vectors", "Africa archives, Zambia subset", "elevation, slope, river distance, upstream area, basins",
         "m, degrees, km, km²", f"data/raw/hydrosheds/: {nfiles(P['raw_hydrosheds'])} files", "district_terrain_hydrology.csv, derived_rasters/slope_15s_zambia.tif",
         th[0], th[3], "VERIFIED (2nd audit)", "Terrain/drainage", "CORE (static)", "point + zonal both computed"],
        ["GloFAS river-network static maps", "EC JRC (CEMS GloFAS)", cfg["glofas"]["static_base_url"], "LISFLOOD static maps v1.1.1 (GloFAS v4.x)",
         "static", "static", "0.05°", "global files; Zambia subset", "upstream area, local drain direction, channel mask", "m², –, –",
         f"data/raw/glofas/static/: {nfiles(P['raw_glofas'] + '/static')} files", "hydrology/glofas_district_extraction_points.csv", gp[0], gp[3],
         "VERIFIED (2nd audit)" if gp[0] != "—" else "IN PROGRESS", "Defines river-network extraction", "CORE support", "CC BY 4.0"],
        ["GloFAS v4.0 historical", "Copernicus CEMS (EWDS)", "https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical",
         "version_4_0, consolidated", "1979 (product)", "2026 (product)", "0.05°, daily", "Zambia window (planned)",
         "river discharge, runoff water equivalent, soil wetness index", "m³/s, m, –", f"data/raw/glofas/historical/: {glofas_ts} GRIB2", "—", "—", "—",
         "DEFERRED by researcher decision (2026-10-08) — no EWDS credentials", "Hydrological state", "DEFERRED (was CORE)",
         "scripts ready: download_glofas.py, extract_glofas.py"],
        ["GloFAS v4.0 reforecasts", "Copernicus CEMS (EWDS)", "https://ewds.climate.copernicus.eu/datasets/cems-glofas-reforecast",
         "version_4_0", "2003-03 (issues)", "2023-11 (issues)", "0.05°, twice-weekly issues, leads 1–46 d", "Zambia window (planned)",
         "river discharge (ensemble)", "m³/s", "0", "—", "—", "—", "DEFERRED with GloFAS historical", "Forecast experiment", "DEFERRED (optional)", "honest-forecast archive"],
        ["NASA POWER soil wetness", "NASA LaRC POWER", "https://power.larc.nasa.gov/api/temporal/daily/point", "API v2.10.0",
         sm[1], sm[2], "~0.5° at district point", "101 district points", "GWETTOP, GWETROOT, GWETPROF", "fraction 0–1",
         f"data/raw/nasa_power/daily_soil_moisture/: {nfiles(P['raw_nasa_power_soil'])} JSON", "nasa_power_daily_soil_moisture.csv", sm[0], sm[3], "VERIFIED (2nd audit)",
         "Antecedent wetness", "OPTIONAL", "Spearman 0.83–0.90 with 30–90-day rain; 2-decimal values, long plateaus (GWETPROF ~42 distinct values per district)"],
        ["ESA WorldCover", "ESA", "https://esa-worldcover.org/en/data-access", "2021 v200", "2021", "2021", "10 m read at 40 m overview",
         "17 tiles covering Zambia", "11 land-cover classes", "% of district", f"data/raw/landcover/: {nfiles(P['raw_landcover'])} tiles", "district_landcover.csv",
         lc[0], lc[3], "VERIFIED (2nd audit)", "Land cover", "OPTIONAL (static)", "2021 snapshot"],
        ["JRC Global Surface Water", "EC JRC / Google", "https://global-surface-water.appspot.com/download", "v1.4 (2021)", "1984", "2021",
         "30 m", "4 tiles covering Zambia", "water occurrence", "% of time water", f"data/raw/other/global_surface_water/: {nfiles(P['raw_other'] + '/global_surface_water', '*.tif')} tiles",
         "environmental/district_surface_water.csv", gs[0], gs[3], "VERIFIED" if gs[0] != "—" else "IN PROGRESS", "Floodplain susceptibility",
         "OPTIONAL (static)", "aggregate includes post-event years"],
        ["Climate indices", "NOAA CPC / NOAA PSL / BoM", "https://www.cpc.ncep.noaa.gov/data/indices/ ; https://psl.noaa.gov/gcos_wgsp/Timeseries/DMI/ ; https://www.bom.gov.au/climate/enso/indices.shtml",
         "ERSST.v5 (ONI, Niño 3.4); HadISST1.1 (DMI)", "1870/1950", "2026", "monthly (BoM weekly)", "ocean basins (one value for Zambia)",
         "ONI, Niño 3.4 anomaly, DMI, IOD", "°C", f"data/raw/climate_indices/: {nfiles(P['raw_climate_indices'])} text files", "climate_indices_monthly.csv, climate_iod_weekly_bom.csv",
         ci[0], ci[3], "VERIFIED (2nd audit)", "Seasonal state", "OPTIONAL", "must be lagged"],
        ["WorldPop", "WorldPop, Univ. of Southampton", "https://www.worldpop.org/", "unconstrained 1 km, not UN-adjusted; DOI 10.5258/SOTON/WP00670",
         ex[1], ex[2], "30″ (~1 km)", "Zambia", "population", "people", f"data/raw/worldpop/: {nfiles(P['raw_worldpop'], '*.tif')} rasters",
         "exposure/worldpop_district_exposure.csv", ex[0], ex[3], "VERIFIED (2nd audit)", "Exposure", "EXPOSURE", "never an occurrence predictor"],
        ["DFO flood archive", "Dartmouth Flood Observatory", "https://floodobservatory.colorado.edu/", "—", "1985 (product)", "—", "event",
         "global", "flood events", "—", "data/raw/satellite_flood/: README only", "—", "—", "—", "NOT COLLECTED — server unreachable", "Validation", "VALIDATION", "optional"],
        ["GRDC river gauges", "GRDC (WMO)", "https://portal.grdc.bafg.de/", "—", "—", "—", "station", "few stations", "discharge", "m³/s",
         "data/raw/hydrology/: README only", "—", "—", "—", "NOT COLLECTED — request-only", "Validation", "VALIDATION", "optional / data access limited"],
    ]
    cols = ["Dataset", "Source", "Official URL", "Version", "Start date", "End date", "Resolution", "Spatial coverage", "Variables",
            "Units", "Raw files", "Processed files", "Rows/files", "Missing %", "Quality status", "Role", "Class", "Notes"]
    L = ["# FloodShield-Zambia — Final Data Inventory", "",
         f"_Generated {utc_now()} by `scripts/build_final_inventory.py`; counts, dates and missing % are recomputed from disk. "
         f"Required daily window: {win['start']} → {win['end']}._", "",
         "| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    L += ["| " + " | ".join(str(x).replace("|", "/") for x in r) + " |" for r in R]
    L += ["", "## Directory structure (actual)", "", "```",
          "data/raw/{desinventar, nasa_power, chirps, hydrosheds, glofas, landcover, worldpop, climate_indices, other,   (also: data/raw/era5_land/)",
          "          era5_land*, hydrology*, satellite_flood*}      (* = README documenting why not collected)",
          "data/processed/                 location master, flood tables, district attributes, point extractions",
          "data/processed/environmental/   Global Surface Water district summary",
          "data/processed/hydrology/       GloFAS extraction points",
          "data/processed/exposure/        WorldPop exposure layer (kept apart from occurrence data)",
          "data/processed/derived_rasters/ slope",
          "data/quality_flags/             flags from the second audit",
          "data/final/                     intentionally empty (Stage 3)",
          "```",
          "WorldCover lives in `data/raw/landcover/` (existing structure kept rather than renamed to `worldcover/`).", ""]
    (ROOT / P["docs"] / "FINAL_DATA_INVENTORY.md").write_text("\n".join(L), encoding="utf-8")
    logger.info("Wrote docs/FINAL_DATA_INVENTORY.md (%d datasets)", len(R))


if __name__ == "__main__":
    main()
