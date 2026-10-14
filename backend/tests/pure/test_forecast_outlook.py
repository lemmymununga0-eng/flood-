import datetime as dt

from app.services.forecast_outlook import WindowPrediction, build_outlook, local_today, outlook_dates

D = dt.date


def test_seven_consecutive_unique_ordered_dates_starting_tomorrow():
    ds = outlook_dates(D(2026, 10, 14))
    assert ds[0] == D(2026, 10, 15) and len(ds) == 7 == len(set(ds))
    assert all((b - a).days == 1 for a, b in zip(ds, ds[1:]))


def test_month_and_year_end():
    assert outlook_dates(D(2026, 10, 28))[-1] == D(2026, 11, 4)
    ds = outlook_dates(D(2026, 12, 29))
    assert [d.isoformat() for d in ds][:4] == ["2026-12-30", "2026-12-31", "2027-01-01", "2027-01-02"]
    assert D(2028, 2, 29) in outlook_dates(D(2028, 2, 25))   # leap day


def test_zambia_timezone_boundary():
    # 22:30 UTC on 14 Oct is already 00:30 on 15 Oct in Lusaka (UTC+2)
    assert local_today(dt.datetime(2026, 10, 14, 22, 30, tzinfo=dt.timezone.utc)) == D(2026, 10, 15)
    assert local_today(dt.datetime(2026, 10, 14, 21, 59, tzinfo=dt.timezone.utc)) == D(2026, 10, 14)


def test_labels_and_weekday():
    out = build_outlook(D(2026, 10, 14), None)
    assert out["days"][0]["label"] == "Day 1 — Thursday, 15 October 2026"
    assert out["days"][6]["weekday"] == "Wednesday"


def _pred(start, end, obs):
    return WindowPrediction("HIGH", 0.004, start, end, obs, "flood_risk_lr_v1", None)


def test_no_prediction_means_no_fabricated_values():
    out = build_outlook(D(2026, 10, 14), None)
    assert out["status"] == "no_prediction" and out["window_prediction"] is None
    assert all(d["window_risk_level"] is None and d["daily_flood_prediction"] is None
               and d["weather_forecast"] is None for d in out["days"])


def test_window_prediction_is_attributed_to_window_not_per_day():
    out = build_outlook(D(2026, 10, 14), _pred(D(2026, 10, 15), D(2026, 10, 21), D(2026, 10, 14)))
    assert out["status"] == "complete" and not out["stale"]
    assert all(d["in_prediction_window"] and d["window_risk_level"] == "HIGH" for d in out["days"])
    assert all(d["daily_flood_prediction"] is None for d in out["days"])
    assert out["window_prediction"]["scope"] == "window"


def test_partial_and_outside_and_stale():
    out = build_outlook(D(2026, 10, 14), _pred(D(2026, 10, 12), D(2026, 10, 18), D(2026, 10, 10)))
    assert out["status"] == "partial"
    assert [d["in_prediction_window"] for d in out["days"]] == [True] * 4 + [False] * 3
    assert out["stale"]   # observation 4 days old exceeds the 3-day limit
    old = build_outlook(D(2026, 10, 14), _pred(D(2026, 10, 1), D(2026, 10, 7), D(2026, 9, 30)))
    assert old["status"] == "window_outside_outlook" and old["stale"]
    assert not any(d["window_risk_level"] for d in old["days"])
