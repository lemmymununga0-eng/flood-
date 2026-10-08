"""Central configuration for the CORRECTED FloodShield ML pipeline.

Phase 22 (reproducibility): no developer-specific absolute path appears anywhere in
this package. Every path is derived from one configurable root.

    FLOODSHIELD_DATA_ROOT   directory holding the raw research inputs
                            (locations.csv, NASA POWER export, event exports,
                            climate indices). Defaults to ../../flooddata
                            relative to the repository, which is where this
                            project's research bundle currently lives.

    FLOODSHIELD_ML_OUT      directory for everything the corrected pipeline
                            writes. Defaults to <data_root>/corrected so that
                            nothing ever overwrites the preserved baseline.

Nothing in this module writes to the CURRENT_RESEARCH_BASELINE locations. The
baseline is read-only from the corrected pipeline's point of view; see
ml/baseline/ for the frozen inventory that proves it is unchanged.
"""
from __future__ import annotations

import os
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ML_ROOT = REPO_ROOT / "ml"


def _env_path(var: str, default: pathlib.Path) -> pathlib.Path:
    raw = os.environ.get(var, "").strip()
    return pathlib.Path(raw).expanduser().resolve() if raw else default


# --- inputs: the preserved research bundle (read-only) -----------------------
DATA_ROOT = _env_path("FLOODSHIELD_DATA_ROOT", (REPO_ROOT.parent / "flooddata").resolve())

LOCATIONS_CSV = DATA_ROOT / "locations.csv"
WEATHER_CSV = DATA_ROOT / "nasa_power_zambia_flood_locations.csv"
DESINVENTAR_CSV = DATA_ROOT / "zambia_desinventar_flood_events_full.csv"
DFO_CSV = DATA_ROOT / "external" / "dfo_zambia_events.csv"
NINO34_CSV = DATA_ROOT / "noaa_nino34_hadisst_1980_2026.csv"
DMI_CSV = DATA_ROOT / "noaa_dmi_had_1980_2026.csv"
GLOFAS_CSV = DATA_ROOT / "glofas_river_discharge.csv"

# The project's own independently-sourced event log, which lives in the repo.
CURATED_EVENTS_CSV = REPO_ROOT / "ai-engine" / "data" / "external" / "zambia_flood_events_log.csv"

# --- baseline (frozen, never written to) -------------------------------------
BASELINE_MODEL_DIR = DATA_ROOT / "models" / "logistic_regression"
BASELINE_REPORTS_DIR = DATA_ROOT / "data" / "reports"
BASELINE_PROCESSED_DIR = DATA_ROOT / "data" / "processed"

# --- outputs: everything the corrected pipeline produces ---------------------
OUT_ROOT = _env_path("FLOODSHIELD_ML_OUT", DATA_ROOT / "corrected")
PROCESSED_DIR = OUT_ROOT / "processed"
REPORTS_DIR = OUT_ROOT / "reports"
ARTIFACT_DIR = OUT_ROOT / "artifacts"

# In-repo outputs that are small enough to version-control.
CONTRACTS_DIR = ML_ROOT / "contracts"
LABELS_DIR = ML_ROOT / "labels"
ML_REPORTS_DIR = ML_ROOT / "reports"
BASELINE_MANIFEST_DIR = ML_ROOT / "baseline"

# --- pipeline constants ------------------------------------------------------
SEED = 42
TARGET = "flood_next_7d"
MASK_COL = "label_usable"
HORIZON_DAYS = 7

# Chronological split fractions, identical to the baseline so the two pipelines
# remain directly comparable. Split is by GLOBAL DATE, never by row index.
TRAIN_FRAC = 0.70
VAL_FRAC = 0.15


def ensure_out_dirs() -> None:
    for d in (OUT_ROOT, PROCESSED_DIR, REPORTS_DIR, ARTIFACT_DIR,
              CONTRACTS_DIR, LABELS_DIR, ML_REPORTS_DIR, BASELINE_MANIFEST_DIR):
        d.mkdir(parents=True, exist_ok=True)


def describe() -> str:
    return (
        f"REPO_ROOT  = {REPO_ROOT}\n"
        f"DATA_ROOT  = {DATA_ROOT}   (inputs, read-only)\n"
        f"OUT_ROOT   = {OUT_ROOT}   (corrected pipeline outputs)\n"
    )


if __name__ == "__main__":
    print(describe())
    for name, p in [
        ("locations", LOCATIONS_CSV), ("weather", WEATHER_CSV),
        ("desinventar", DESINVENTAR_CSV), ("dfo", DFO_CSV),
        ("curated", CURATED_EVENTS_CSV), ("nino34", NINO34_CSV),
        ("dmi", DMI_CSV), ("glofas", GLOFAS_CSV),
    ]:
        print(f"  {'OK ' if p.exists() else 'MISSING'}  {name:12s} {p}")

# ---------------------------------------------------------------------------
# Stage 3 (2026-10-08 collection). Lives IN the repo under data/, unlike the
# Stage 1/2 research bundle which sits outside it. The Stage 1/2 paths above are
# left untouched so the earlier pipeline stays reproducible.
# ---------------------------------------------------------------------------
S3_DATA = REPO_ROOT / "data"
S3_PROCESSED = S3_DATA / "processed"
S3_RAW = S3_DATA / "raw"
S3_REPORTS = REPO_ROOT / "reports"

S3_CHIRPS = S3_PROCESSED / "chirps_daily_at_locations.csv"
S3_POWER = S3_RAW / "nasa_power" / "nasa_power_daily.csv"
S3_SOIL = S3_RAW / "nasa_power" / "nasa_power_daily_soil_moisture.csv"
S3_TERRAIN = S3_PROCESSED / "district_terrain_hydrology.csv"
S3_LANDCOVER = S3_PROCESSED / "district_landcover.csv"
S3_SURFACE_WATER = S3_PROCESSED / "environmental" / "district_surface_water.csv"
S3_CLIMATE = S3_PROCESSED / "climate_indices_monthly.csv"
S3_EVENT_AUDIT = S3_PROCESSED / "desinventar_flood_event_audit.csv"
S3_DATE_RELIABILITY = S3_PROCESSED / "desinventar_flood_date_reliability.csv"
S3_LOCATIONS = S3_PROCESSED / "location_master.csv"

S3_OUT = _env_path("FLOODSHIELD_S3_OUT", OUT_ROOT / "stage3")
S3_OUT_PROCESSED = S3_OUT / "processed"
S3_OUT_REPORTS = S3_OUT / "reports"
S3_OUT_ARTIFACTS = S3_OUT / "artifacts"

# Forecast horizons under investigation. H+1 is excluded: the collection's own
# readiness report concludes even high-confidence DesInventar dates can be off by a
# day, so a 1-day target is not defensible with these labels.
S3_HORIZONS = (3, 7, 14, 20, 30)
S3_PRIMARY_HORIZON = 7


def ensure_s3_dirs() -> None:
    for d in (S3_OUT, S3_OUT_PROCESSED, S3_OUT_REPORTS, S3_OUT_ARTIFACTS):
        d.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    print(describe())
    for name, p in [
        ("locations", LOCATIONS_CSV), ("weather", WEATHER_CSV),
        ("desinventar", DESINVENTAR_CSV), ("dfo", DFO_CSV),
        ("curated", CURATED_EVENTS_CSV), ("nino34", NINO34_CSV),
        ("dmi", DMI_CSV), ("glofas", GLOFAS_CSV),
    ]:
        print(f"  {'OK ' if p.exists() else 'MISSING'}  {name:12s} {p}")
