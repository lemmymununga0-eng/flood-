"""Validation, CSV parsing and freshness for dam/reservoir observations.

Pure functions (no DB). Principles:
  * A blank cell is MISSING (None). It is never read as zero.
  * Units are fixed by column name (e.g. inflow_m3s is m^3/s); values are not converted silently.
  * Observation time must be timezone-aware; it is stored apart from retrieval time.
  * Range checks reject only physically impossible values. They are NOT operating thresholds.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import math
from dataclasses import dataclass, field

DATA_KINDS = ("live", "historical", "manual_import", "synthetic_test")

# column -> (unit, min, max). Bounds are physical-plausibility limits only.
MEASUREMENTS: dict[str, tuple[str, float, float]] = {
    "reservoir_level_m": ("m", 0.0, 2000.0),
    "storage_m3": ("m3", 0.0, 1e12),
    "storage_pct": ("%", 0.0, 100.0),
    "inflow_m3s": ("m3/s", 0.0, 1e5),
    "outflow_m3s": ("m3/s", 0.0, 1e5),
    "spillway_m3s": ("m3/s", 0.0, 1e5),
    "turbine_m3s": ("m3/s", 0.0, 1e5),
    "downstream_level_m": ("m", -10.0, 100.0),
    "downstream_discharge_m3s": ("m3/s", 0.0, 1e6),
    "rainfall_observed_mm": ("mm", 0.0, 1500.0),
    "rainfall_forecast_mm": ("mm", 0.0, 1500.0),
}
QUALITY_FLAGS = ("good", "suspect", "estimated", "unverified")
FRESH_HOURS = 48       # heuristic display threshold, not an operational standard
FUTURE_TOLERANCE = dt.timedelta(minutes=5)
_CSV_META = ("observed_at", "source_published_at", "provider", "source_reference", "quality_flag")


class ValidationError(ValueError):
    pass


def parse_timestamp(value: str | dt.datetime, *, now: dt.datetime | None = None) -> dt.datetime:
    """Timezone-aware UTC datetime. Naive input is rejected (ambiguous), future input too."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValidationError("timestamp is empty")
        try:
            parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(f"unparseable timestamp {value!r} (use ISO 8601 with offset)") from exc
    else:
        parsed = value
    if parsed.tzinfo is None:
        raise ValidationError(f"timestamp {value!r} has no timezone offset; refusing to guess one")
    parsed = parsed.astimezone(dt.timezone.utc)
    if parsed > now + FUTURE_TOLERANCE:
        raise ValidationError(f"timestamp {value!r} is in the future")
    return parsed


def validate_measurement(name: str, value) -> float | None:
    """None/blank -> None (missing). Otherwise a finite float inside the physical range."""
    if name not in MEASUREMENTS:
        raise ValidationError(f"unknown measurement {name!r}")
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name}: non-numeric value {value!r}") from exc
    if not math.isfinite(number):
        raise ValidationError(f"{name}: non-finite value")
    unit, lo, hi = MEASUREMENTS[name]
    if not lo <= number <= hi:
        raise ValidationError(f"{name}: {number} {unit} outside physical range [{lo}, {hi}]")
    return number


def validate_observation(raw: dict, *, now: dt.datetime | None = None) -> dict:
    out: dict = {"observed_at": parse_timestamp(raw.get("observed_at") or "", now=now)}
    published = raw.get("source_published_at")
    out["source_published_at"] = parse_timestamp(published, now=now) if published else None
    out["measurements"] = {name: validate_measurement(name, raw.get(name)) for name in MEASUREMENTS}
    flag = (raw.get("quality_flag") or "unverified").strip().lower()
    if flag not in QUALITY_FLAGS:
        raise ValidationError(f"quality_flag {flag!r} not in {QUALITY_FLAGS}")
    out["quality_flag"] = flag
    provider = (raw.get("provider") or "").strip()
    reference = (raw.get("source_reference") or "").strip()
    if not provider or not reference:
        raise ValidationError("provider and source_reference are required (provenance)")
    out["provider"], out["source_reference"] = provider, reference
    if all(v is None for v in out["measurements"].values()):
        raise ValidationError("row has no measurements")
    return out


@dataclass
class CsvParseResult:
    rows: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)   # {"line": int, "error": str}


def parse_csv(text: str, *, now: dt.datetime | None = None) -> CsvParseResult:
    reader = csv.DictReader(io.StringIO(text))
    result = CsvParseResult()
    if not reader.fieldnames or "observed_at" not in reader.fieldnames:
        result.errors.append({"line": 1, "error": "header must include observed_at"})
        return result
    unknown = [c for c in reader.fieldnames if c not in MEASUREMENTS and c not in _CSV_META]
    if unknown:
        result.errors.append({"line": 1, "error": f"unknown column(s): {unknown}"})
        return result
    seen: set[tuple] = set()
    for line, raw in enumerate(reader, start=2):
        try:
            row = validate_observation(raw, now=now)
        except ValidationError as exc:
            result.errors.append({"line": line, "error": str(exc)})
            continue
        key = (row["observed_at"], row["provider"])
        if key in seen:
            result.errors.append({"line": line, "error": "duplicate observed_at for provider in file"})
            continue
        seen.add(key)
        result.rows.append(row)
    return result


def freshness(latest: dt.datetime | None, *, now: dt.datetime | None = None) -> str:
    """'no_data' | 'fresh' | 'stale' based on OBSERVATION time (not retrieval time)."""
    if latest is None:
        return "no_data"
    now = now or dt.datetime.now(dt.timezone.utc)
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=dt.timezone.utc)
    return "fresh" if now - latest <= dt.timedelta(hours=FRESH_HOURS) else "stale"
