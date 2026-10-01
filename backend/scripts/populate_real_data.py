#!/usr/bin/env python3
"""Populate the application with REAL data by actually running the system.

Nothing here is invented. Specifically:
  1. Locations come from the research bundle's locations.csv — 82 real Zambian
     districts whose coordinates were verified against the OpenStreetMap Nominatim
     geocoder; provinces come from the real DesInventar event records.
  2. Weather comes from real live NASA POWER API calls (the same ingestion path the
     app already uses). NASA's -999 "no data yet" sentinel is rejected, not stored.
  3. Predictions are produced by running the real trained model over that real
     weather. No probability is hand-written.

Locations/weather/predictions that cannot be obtained are skipped and reported —
never filled in with a placeholder.

    python scripts/populate_real_data.py [--limit N] [--skip-weather]
"""
import argparse
import csv
import json
import os
import pathlib
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.integrations.weather_provider import NasaPowerWeatherProvider  # noqa: E402
from app.ml.predictor import MODEL_VERSION, predict_risk  # noqa: E402
from app.models.location import Location  # noqa: E402
from app.models.prediction import ModelVersion, Prediction  # noqa: E402
from app.models.weather_observation import WeatherObservation  # noqa: E402
from app.repositories.weather_observation_repository import WeatherObservationRepository  # noqa: E402

# Phase 22: configurable, never a developer-specific absolute path. Resolves the
# same way ml/config.py does, so both pipelines read one location.
RESEARCH = pathlib.Path(
    os.environ.get("FLOODSHIELD_DATA_ROOT")
    or (pathlib.Path(__file__).resolve().parents[2].parent / "flooddata")
).expanduser()
LOCATIONS_CSV = RESEARCH / "locations.csv"
EVENTS_CSV = RESEARCH / "zambia_desinventar_flood_events_full.csv"

EVIDENCE = (
    "Coordinates verified against the OpenStreetMap Nominatim geocoder (2026-09-18); "
    "district identified from real DesInventar (UNDRR) flood-event records."
)
EVIDENCE_URL = "https://www.desinventar.net/DesInventar/profiletab.jsp?countrycode=zmb"


def district_to_province() -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not EVENTS_CSV.exists():
        return mapping
    with EVENTS_CSV.open(encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            district = (row.get("district") or "").strip()
            province = (row.get("province") or "").strip()
            if district and province and district not in mapping:
                mapping[district] = province
    return mapping


def seed_locations(db, limit: int | None) -> list[Location]:
    provinces = district_to_province()
    rows = list(csv.DictReader(LOCATIONS_CSV.open(encoding="utf-8")))
    if limit:
        rows = rows[:limit]

    created = updated = 0
    for row in rows:
        name = row["name"].strip()
        existing = db.scalar(select(Location).where(Location.name == name))
        province = provinces.get(name, "Unspecified")
        if existing is None:
            db.add(Location(
                name=name,
                province=province,
                latitude=float(row["lat"]),
                longitude=float(row["lon"]),
                coordinate_confidence=row["coord_status"].strip(),
                evidence_note=EVIDENCE,
                evidence_source_url=EVIDENCE_URL,
            ))
            created += 1
        else:
            existing.coordinate_confidence = row["coord_status"].strip()
            if existing.province in ("", "Unspecified"):
                existing.province = province
            updated += 1
    db.commit()
    print(f"Locations: {created} created, {updated} updated (source: {LOCATIONS_CSV.name})")
    return list(db.scalars(select(Location).order_by(Location.id)))


def ingest_weather(db, locations: list[Location]) -> dict[int, WeatherObservation]:
    """Real NASA POWER calls. Returns the latest usable observation per location."""
    provider = NasaPowerWeatherProvider()
    repo = WeatherObservationRepository(db)
    end = datetime.now(timezone.utc).date() - timedelta(days=3)  # NASA POWER lag
    start = end - timedelta(days=10)
    ok = failed = 0

    for loc in locations:
        outcome = provider.fetch_daily_point(
            latitude=loc.latitude, longitude=loc.longitude,
            start=start.strftime("%Y%m%d"), end=end.strftime("%Y%m%d"),
        )
        if outcome.status == "failed":
            print(f"  ! {loc.name}: NASA POWER failed — {outcome.error_detail}")
            failed += 1
            continue
        # Every contract feature must be present. A day missing any of them is
        # skipped, not patched -- the previous version substituted the daily mean for
        # the two temperature extremes, which flipped half of all alert decisions.
        usable = [
            r for r in outcome.records
            if None not in (r.precipitation_mm, r.temperature_c, r.temperature_max_c,
                            r.temperature_min_c, r.relative_humidity_pct,
                            r.wind_speed_10m_ms)
        ]
        if not usable:
            print(f"  ! {loc.name}: no usable (non-sentinel) days returned — skipped")
            failed += 1
            continue
        existing_dates = {
            d for (d,) in db.execute(
                select(WeatherObservation.observed_date).where(
                    WeatherObservation.location_id == loc.id)
            ).all()
        }
        fresh = [r for r in usable if r.observed_date not in existing_dates]
        if fresh:
            repo.bulk_add(loc.id, fresh)
        ok += 1

    print(f"Weather: {ok} locations ingested, {failed} skipped (real NASA POWER calls)")

    latest: dict[int, WeatherObservation] = {}
    for loc in locations:
        obs = db.scalars(
            select(WeatherObservation)
            .where(WeatherObservation.location_id == loc.id)
            .order_by(WeatherObservation.observed_date.desc())
        ).first()
        if obs and None not in (obs.precipitation_mm, obs.temperature_c,
                                obs.temperature_max_c, obs.temperature_min_c,
                                obs.relative_humidity_pct, obs.wind_speed_10m_ms):
            latest[loc.id] = obs
    return latest


def generate_predictions(db, locations: list[Location], latest: dict[int, WeatherObservation]) -> None:
    mv = db.scalar(select(ModelVersion).where(ModelVersion.version == MODEL_VERSION))
    if mv is None:
        print("! No registered ModelVersion — run scripts/register_model.py first. Aborting.")
        return

    made = skipped = 0
    for loc in locations:
        obs = latest.get(loc.id)
        if obs is None:
            skipped += 1
            continue
        # Real daily extremes and real 10 m wind, straight from the stored
        # observation. No substitution: predict_risk() now rejects a degenerate
        # max==mean==min triple outright.
        result = predict_risk(
            location_name=loc.name, latitude=loc.latitude, longitude=loc.longitude,
            precipitation_mm=obs.precipitation_mm,
            temperature_c=obs.temperature_c,
            temperature_max_c=obs.temperature_max_c,
            temperature_min_c=obs.temperature_min_c,
            relative_humidity_pct=obs.relative_humidity_pct,
            wind_speed_10m_ms=obs.wind_speed_10m_ms,
            observation_date=obs.observed_date.strftime("%Y-%m-%d"),
        )
        top = ", ".join(
            f"{c['feature']} {c['contribution']:+.3f}" for c in result["explanation"][:3]
        )
        # Any earlier prediction for this location is superseded, not silently left
        # to display forever alongside the new one.
        for old in db.scalars(
            select(Prediction).where(
                Prediction.location_id == loc.id, Prediction.is_stale.is_(False))
        ).all():
            old.is_stale = True

        db.add(Prediction(
            location_id=loc.id,
            model_version_id=mv.id,
            predicted_at=datetime.now(timezone.utc).replace(tzinfo=None),
            prediction_probability=result["risk_probability_calibrated"],
            risk_level=result["risk_level"].lower(),
            prediction_horizon=f"{result['prediction_horizon_days']} days",
            observation_date=obs.observed_date,
            target_window_start=obs.observed_date + timedelta(days=1),
            target_window_end=obs.observed_date + timedelta(
                days=result["prediction_horizon_days"]),
            feature_contract_version=result["feature_contract_version"],
            is_stale=False,
            explanation=json.dumps({
                "observation_date": obs.observed_date.strftime("%Y-%m-%d"),
                "raw_score": result["risk_probability_raw"],
                "top_contributions": top,
                "feature_contract_version": result["feature_contract_version"],
            }),
        ))
        made += 1
    db.commit()
    print(f"Predictions: {made} generated from real weather, {skipped} skipped (no usable observation)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip-weather", action="store_true")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        locations = seed_locations(db, args.limit)
        latest = {} if args.skip_weather else ingest_weather(db, locations)
        if not args.skip_weather:
            generate_predictions(db, locations, latest)
    finally:
        db.close()


if __name__ == "__main__":
    main()
