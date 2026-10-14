import datetime as dt

import pytest

from app.services.dam_validation import (ValidationError, freshness, parse_csv, parse_timestamp,
                                         validate_measurement, validate_observation)

NOW = dt.datetime(2026, 10, 14, 12, 0, tzinfo=dt.timezone.utc)
HEAD = "observed_at,reservoir_level_m,inflow_m3s,spillway_m3s,provider,source_reference,quality_flag\n"


def test_blank_is_missing_not_zero():
    assert validate_measurement("inflow_m3s", "") is None
    assert validate_measurement("inflow_m3s", None) is None
    assert validate_measurement("inflow_m3s", "0") == 0.0


def test_physical_ranges_and_garbage_rejected():
    for name, bad in [("storage_pct", "120"), ("inflow_m3s", "-5"), ("rainfall_observed_mm", "abc"),
                      ("reservoir_level_m", "nan"), ("nope", "1")]:
        with pytest.raises(ValidationError):
            validate_measurement(name, bad)


def test_timestamps():
    assert parse_timestamp("2026-10-14T10:00:00+02:00", now=NOW) == dt.datetime(2026, 10, 14, 8, tzinfo=dt.timezone.utc)
    assert parse_timestamp("2026-10-14T10:00:00Z", now=NOW).tzinfo is not None
    for bad in ("2026-10-14T10:00:00", "", "yesterday", "2026-10-20T00:00:00Z"):
        with pytest.raises(ValidationError):
            parse_timestamp(bad, now=NOW)


def test_provenance_and_empty_rows_required():
    with pytest.raises(ValidationError):
        validate_observation({"observed_at": "2026-10-01T00:00:00Z", "inflow_m3s": "5"}, now=NOW)
    with pytest.raises(ValidationError):
        validate_observation({"observed_at": "2026-10-01T00:00:00Z", "provider": "p", "source_reference": "r"}, now=NOW)


def test_csv_good_and_bad_rows():
    text = HEAD + ("2026-10-01T00:00:00Z,480.5,,0,ZRA,report-1,good\n"
                   "2026-10-02T00:00:00Z,abc,10,,ZRA,report-1,good\n"
                   "2026-10-01T00:00:00Z,480.6,,,ZRA,report-1,good\n")
    r = parse_csv(text, now=NOW)
    assert len(r.rows) == 1 and len(r.errors) == 2
    m = r.rows[0]["measurements"]
    assert m["inflow_m3s"] is None and m["spillway_m3s"] == 0.0 and m["reservoir_level_m"] == 480.5


def test_csv_header_checks():
    assert parse_csv("a,b\n1,2\n").errors
    assert parse_csv("observed_at,bogus\n2026-10-01T00:00:00Z,1\n", now=NOW).errors


def test_freshness_uses_observation_time():
    assert freshness(None) == "no_data"
    assert freshness(NOW - dt.timedelta(hours=47), now=NOW) == "fresh"
    assert freshness(NOW - dt.timedelta(hours=49), now=NOW) == "stale"
