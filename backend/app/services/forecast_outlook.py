"""Seven-day outlook: dated calendar skeleton + honest attachment of the existing model output.

The production model emits ONE probability per scored observation, describing the window
(t, t+7] -- see app/ml/predictor.py. It does not produce seven daily predictions, and no
weather-forecast provider is integrated. This module therefore:

  * generates seven consecutive local dates (Africa/Lusaka),
  * marks which of them fall inside a stored prediction's target window,
  * attaches that WINDOW-level result to those days, labelled as window-level,
  * never fabricates a per-day probability or per-day weather.

Convention (matches the model's own window): Day 1 is the day AFTER the reference date,
i.e. tomorrow in Zambia local time.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

ZAMBIA_TZ = ZoneInfo("Africa/Lusaka")  # UTC+2, no DST
OUTLOOK_DAYS = 7


def local_today(now: dt.datetime | None = None) -> dt.date:
    """Calendar date in Zambia. `now` must be tz-aware (or is assumed UTC)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    return now.astimezone(ZAMBIA_TZ).date()


def outlook_dates(today: dt.date, days: int = OUTLOOK_DAYS) -> list[dt.date]:
    """Consecutive dates; Day 1 = today + 1."""
    return [today + dt.timedelta(days=i) for i in range(1, days + 1)]


@dataclass(frozen=True)
class WindowPrediction:
    risk_level: str
    probability: float
    window_start: dt.date
    window_end: dt.date
    observation_date: dt.date | None
    model_version: str | None
    predicted_at: dt.datetime | None


def build_outlook(
    today: dt.date,
    prediction: WindowPrediction | None,
    *,
    now: dt.datetime | None = None,
    stale_after_days: int = 3,
) -> dict:
    """Return the outlook payload. `prediction` is the latest stored window prediction for
    the location (or None). Nothing is derived beyond date membership."""
    now = now or dt.datetime.now(dt.timezone.utc)
    dates = outlook_dates(today)
    window_dates = (
        {prediction.window_start + dt.timedelta(days=i)
         for i in range((prediction.window_end - prediction.window_start).days + 1)}
        if prediction else set()
    )
    covered = [d for d in dates if d in window_dates]

    stale = False
    status = "no_prediction"
    if prediction:
        stale = prediction.window_end < dates[0] or (
            prediction.observation_date is not None
            and (today - prediction.observation_date).days > stale_after_days
        )
        if not covered:
            status = "window_outside_outlook"
        elif len(covered) < len(dates):
            status = "partial"
        else:
            status = "complete"

    days = []
    for n, d in enumerate(dates, start=1):
        in_window = d in window_dates
        days.append({
            "day_number": n,
            "date": d.isoformat(),
            "weekday": d.strftime("%A"),
            "label": f"Day {n} — {d.strftime('%A')}, {d.day} {d.strftime('%B %Y')}",
            # Window-level attribution only. Never a per-day probability.
            "in_prediction_window": in_window,
            "window_risk_level": prediction.risk_level if (prediction and in_window) else None,
            "daily_flood_prediction": None,       # the model does not produce one
            "weather_forecast": None,             # no forecast provider integrated
            "weather_forecast_status": "unavailable_no_provider",
        })

    return {
        "timezone": "Africa/Lusaka",
        "day_1_convention": "Day 1 is tomorrow (Africa/Lusaka), matching the model's (t, t+7] window.",
        "generated_at": now.isoformat(),
        "today_local": today.isoformat(),
        "status": status,
        "stale": stale,
        "days": days,
        "window_prediction": None if not prediction else {
            "scope": "window",
            "description": "One model-derived risk estimate for the whole window, "
                           "not a separate prediction for each day.",
            "risk_level": prediction.risk_level,
            "probability_calibrated": prediction.probability,
            "window_start": prediction.window_start.isoformat(),
            "window_end": prediction.window_end.isoformat(),
            "observation_date": prediction.observation_date.isoformat() if prediction.observation_date else None,
            "model_version": prediction.model_version,
            "predicted_at": prediction.predicted_at.isoformat() if prediction.predicted_at else None,
        },
        "notes": [
            "Risk level is relative (validation-percentile bands), not an absolute chance of flooding.",
            "Per-day flood predictions and weather forecasts are unavailable: the model scores a "
            "7-day window and no forecast provider is configured.",
        ],
    }
