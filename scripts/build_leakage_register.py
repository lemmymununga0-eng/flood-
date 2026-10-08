"""Classify every column of every collected table for predictive-leakage risk.

Reads the ACTUAL headers of the files on disk (so nothing is missed) and assigns each variable one of:
  SAFE FOR PREDICTION      usable as a predictor if taken on/before prediction date t (with the stated rule)
  HISTORICAL OBSERVATION   time-stamped observation/reanalysis; safe only for days <= t
  STATIC ENVIRONMENTAL     time-invariant descriptor
  FORECAST VARIABLE        value issued before t about t+lead; safe only in a genuine forecast experiment
  POTENTIAL LEAKAGE        could leak if aligned naively (rule given)
  POST-EVENT               exists only because a flood happened / recorded afterwards — never a predictor
  EXPOSURE ONLY            impact layer, not an occurrence predictor
  NOT A PREDICTOR          identifiers, provenance, quality flags, label metadata
Output: reports/variable_leakage_register.csv

Usage
  python scripts/build_leakage_register.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, p  # noqa: E402

DI_POST = re.compile(r"^(muertos|heridos|desaparece|afectados|vivdest|vivafec|damnificados|evacuados|reubicados|valorloc|valorus|"
                     r"nhectareas|cabezas|kmvias|nhospitales|nescuelas|duracion|socorro|salud|educacion|agropecuario|industrias|"
                     r"acueducto|alcantarillado|energia|comunicaciones|transporte|otros|hay_.*|magnitud2|di_comments|descausa|causa|"
                     r"fuentes|event_end_date_from_duration)$")
META = re.compile(r"(^|_)(id|serial|clave|uu_id|clave_ext|source|raw_file|retriev|created|assessed|note|role|version|"
                  r"source_file|fechafec|fechapor|approved|defaultab|community|time_standard|power_point_|pixel_|"
                  r"cells|nodata_cells|overview_factor|dem_cells|river_proximity_sample_points|records_on_same_date|n_flags)", re.I)


def classify(dataset: str, col: str) -> tuple[str, str]:
    c = col.lower()
    if dataset == "desinventar":
        if DI_POST.match(c) or c in {"muertos"}:
            return "POST-EVENT", "Consequence/response/after-event text. Audit only."
        if c in {"evento", "event_start_date", "date_precision", "date_quality_flag", "fechano", "fechames", "fechadia", "level0",
                 "level1", "level2", "name0", "name1", "name2", "lugar", "latitude", "longitude", "glide",
                 "province_original", "district_original", "location_original"}:
            return "NOT A PREDICTOR", "Label/event metadata (defines the target; never a feature)."
        if META.search(c):
            return "NOT A PREDICTOR", "Identifier/provenance."
        return "POST-EVENT", "DesInventar extension loss/impact field (diccionario). Audit only."
    if dataset in ("flood_date_reliability", "flood_event_audit"):
        return "NOT A PREDICTOR", "Label-quality metadata; must not become a feature."
    if META.search(c) or c in {"location_id", "date", "latitude", "longitude", "year", "month", "location_name", "district",
                               "province", "location_name_original", "district_code", "province_code", "coordinate_source",
                               "coordinate_quality", "spatial_unit", "in_boundary_file", "in_weather_collection",
                               "population_year", "class_at_point"}:
        if c == "class_at_point":
            return "STATIC ENVIRONMENTAL", "Land-cover class at the district point (2021 snapshot)."
        return "NOT A PREDICTOR", "Key/identifier/provenance."
    if dataset in ("nasa_power_weather", "chirps"):
        return "HISTORICAL OBSERVATION", "SAFE FOR PREDICTION only for days <= t (trailing windows); values after t are LEAKAGE."
    if dataset == "nasa_power_soil":
        return "HISTORICAL OBSERVATION", "Model-derived soil wetness; days <= t only (optional experiment)."
    if dataset == "terrain_hydrology":
        if "n_flood" in c:
            return "POTENTIAL LEAKAGE", "Counts all floods incl. future ones — never a feature."
        return "STATIC ENVIRONMENTAL", "Time-invariant terrain/drainage descriptor."
    if dataset == "landcover":
        return "STATIC ENVIRONMENTAL", "2021 snapshot (post-dates most events): quasi-static, optional, flag anachronism."
    if dataset == "surface_water":
        return "POTENTIAL LEAKAGE", "Occurrence aggregates 1984-2021 incl. years after events: static susceptibility only, optional; test with care."
    if dataset == "glofas_points":
        if c.endswith(("_lat", "_lon")) or c in {"district"}:
            return "NOT A PREDICTOR", "Extraction-cell coordinates (where GloFAS is read), not a feature."
        return "STATIC ENVIRONMENTAL", "Static river-network descriptor (upstream area / distance)."
    if dataset == "worldpop":
        return "EXPOSURE ONLY", "Impact/exposure layer — not an occurrence predictor."
    if dataset == "climate_indices":
        if c.startswith("oni"):
            return "POTENTIAL LEAKAGE", "ONI season centred on month m needs month m+1: use season centred on month(t)-2 at the latest."
        return "POTENTIAL LEAKAGE", "Published after month end: use month(t)-1 at the latest."
    if dataset == "dfo":
        return "POST-EVENT", "Observed after the flood — validation only."
    if dataset == "location_master":
        if c.startswith("n_flood"):
            return "POTENTIAL LEAKAGE", "Counts all floods incl. future ones — never a feature."
        return "STATIC ENVIRONMENTAL", "Static location attribute."
    return "NOT A PREDICTOR", "Unclassified — review."


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("leakage", cfg)
    proc = ROOT / cfg["paths"]["processed"]
    files = {
        "desinventar": proc / "desinventar_flood_events.csv",
        "flood_date_reliability": proc / "desinventar_flood_date_reliability.csv",
        "flood_event_audit": proc / "desinventar_flood_event_audit.csv",
        "location_master": proc / "location_master.csv",
        "nasa_power_weather": ROOT / "data/raw/nasa_power/nasa_power_daily.csv",
        "nasa_power_soil": ROOT / "data/raw/nasa_power/nasa_power_daily_soil_moisture.csv",
        "chirps": proc / "chirps_daily_at_locations.csv",
        "terrain_hydrology": proc / "district_terrain_hydrology.csv",
        "landcover": proc / "district_landcover.csv",
        "surface_water": proc / "environmental" / "district_surface_water.csv",
        "worldpop": proc / "exposure" / "worldpop_district_exposure.csv",
        "glofas_points": proc / "hydrology" / "glofas_district_extraction_points.csv",
        "climate_indices": proc / "climate_indices_monthly.csv",
        "dfo": proc / "dfo_zambia_events.csv",
    }
    rows = []
    for ds, f in files.items():
        if not f.exists():
            rows.append({"dataset": ds, "file": str(f.relative_to(ROOT)), "variable": "(file not present)",
                         "category": "n/a", "rule": "dataset not collected"})
            continue
        for col in pd.read_csv(f, nrows=0).columns:
            cat, rule = classify(ds, col)
            rows.append({"dataset": ds, "file": str(f.relative_to(ROOT)).replace("\\", "/"), "variable": col, "category": cat, "rule": rule})
    # GloFAS variables (planned/EWDS) — classified now so the rule exists before any data arrives
    for var, cat, rule in [
        ("historical: river_discharge / runoff_water_equivalent / soil_wetness_index", "HISTORICAL OBSERVATION",
         "ERA5-forced reanalysis: days <= t only. Observed/reanalysed discharge after t is LEAKAGE."),
        ("reforecast: river_discharge at lead L issued on date i", "FORECAST VARIABLE",
         "Safe only if issue date i <= t; never mix with reanalysis values after t."),
        ("forecast (operational): river_discharge / runoff / soil wetness", "FORECAST VARIABLE",
         "Deployment only; system version changes over time (v2.1/v3.1/v4.x)."),
        ("upArea / ldd / chan (static maps)", "STATIC ENVIRONMENTAL", "River-network geometry; used to choose extraction pixels."),
        ("rainfall or discharge observed after t (any source)", "POTENTIAL LEAKAGE",
         "LEAKAGE unless it is a genuine forecast issued at or before t."),
    ]:
        rows.append({"dataset": "glofas", "file": "data/raw/glofas/...", "variable": var, "category": cat, "rule": rule})
    df = pd.DataFrame(rows)
    out = p(cfg, "reports") / "variable_leakage_register.csv"
    df.to_csv(out, index=False)
    logger.info("Leakage register: %d variables -> %s; %s", len(df), out.relative_to(ROOT), df["category"].value_counts().to_dict())


if __name__ == "__main__":
    main()
