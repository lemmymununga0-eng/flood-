"""Experimental, rule-based dam-related flood-concern assessment.

NOT a flood prediction, NOT a public warning, and independent of the production model.
It only reports which documented conditions are present. Thresholds are never absolute
"percent full" rules: a change counts as a signal only when it exceeds the 90th percentile
of that dam's OWN recorded history for the same quantity and window, and only when enough
history exists to compute it. Without that, the signal is reported as not evaluable.

Statuses: insufficient_data | monitoring | elevated_concern | official_release_notice
Synthetic test observations are excluded from every assessment.
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Iterable

from app.services.dam_validation import freshness

INSUFFICIENT_MESSAGE = "Insufficient hydrological data to assess dam-related flood risk."
WINDOW_DAYS = 7
MIN_SPAN_DAYS = 3
MIN_POINTS = 3
MIN_HISTORY_SAMPLES = 30
PERCENTILE = 0.90
MIN_SIGNALS_FOR_CONCERN = 2

# quantity -> signal name. A rise is the documented concern for each.
RISING_SIGNALS = {
    "reservoir_level_m": "reservoir_level_rising",
    "inflow_m3s": "inflow_increasing",
    "downstream_level_m": "downstream_level_rising",
}


def _aware(t: dt.datetime) -> dt.datetime:
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def _series(obs: Iterable, name: str) -> list[tuple[dt.datetime, float]]:
    pts = [(_aware(o.observed_at), getattr(o, name, None)) for o in obs]
    return sorted((t, v) for t, v in pts if v is not None)


def _change_over_window(pts: list[tuple[dt.datetime, float]], end_idx: int) -> float | None:
    """Value at pts[end_idx] minus the earliest value within WINDOW_DAYS before it; None
    unless enough points span enough days."""
    end_t, end_v = pts[end_idx]
    inside = [(t, v) for t, v in pts[: end_idx + 1] if end_t - t <= dt.timedelta(days=WINDOW_DAYS)]
    if len(inside) < MIN_POINTS or (inside[-1][0] - inside[0][0]) < dt.timedelta(days=MIN_SPAN_DAYS):
        return None
    return end_v - inside[0][1]


def _percentile(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[max(0, math.ceil(q * len(s)) - 1)]   # nearest-rank


def _evaluate_rising(obs: list, name: str, now: dt.datetime) -> dict:
    sig = {"signal": RISING_SIGNALS[name], "evaluable": False, "triggered": False, "detail": ""}
    pts = _series(obs, name)
    if len(pts) < MIN_POINTS:
        sig["detail"] = "too few observations"
        return sig
    if now - pts[-1][0] > dt.timedelta(days=WINDOW_DAYS):
        sig["detail"] = "latest value is older than the comparison window"
        return sig
    recent = _change_over_window(pts, len(pts) - 1)
    if recent is None:
        sig["detail"] = "recent observations do not span enough days"
        return sig
    history = []
    for i in range(len(pts) - 1):
        change = _change_over_window(pts, i)
        if change is not None:
            history.append(change)
    if len(history) < MIN_HISTORY_SAMPLES:
        sig["detail"] = (f"only {len(history)} historical comparisons; need {MIN_HISTORY_SAMPLES} "
                         "to judge whether the rise is unusual for this dam")
        return sig
    p90 = _percentile(history, PERCENTILE)
    sig.update(evaluable=True, triggered=recent > 0 and recent > p90,
               detail=f"{WINDOW_DAYS}-day change {recent:+.3f} vs this dam's historical p90 {p90:+.3f}")
    return sig


def _active_notices(notices: Iterable, now: dt.datetime) -> list:
    active = []
    for n in notices:
        published = _aware(n.published_at)
        start = _aware(n.effective_from) if getattr(n, "effective_from", None) else published
        end = _aware(n.effective_to) if getattr(n, "effective_to", None) else None
        if start > now:
            continue
        if end is not None:
            if now <= end:
                active.append(n)
        elif now - published <= dt.timedelta(days=WINDOW_DAYS):
            active.append(n)
    return active


def assess(observations: list, notices: list | None = None, *, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    obs = [o for o in observations if getattr(o, "data_kind", "") != "synthetic_test"]
    latest = max((_aware(o.observed_at) for o in obs), default=None)
    fresh = freshness(latest, now=now)
    base = {"experimental": True, "generated_at": now.isoformat(), "data_freshness": fresh,
            "latest_observation_at": latest.isoformat() if latest else None,
            "disclaimer": "Experimental transparency aid. Not a flood prediction or public warning."}

    active = _active_notices(notices or [], now)
    if active:
        return {**base, "status": "official_release_notice", "signals": [],
                "message": "An official release notice is on record. Refer to the notice itself.",
                "notices": [{"published_at": _aware(n.published_at).isoformat(),
                             "description": n.description, "source_reference": n.source_reference}
                            for n in active]}

    if latest is None or fresh == "stale":
        return {**base, "status": "insufficient_data", "signals": [], "message": INSUFFICIENT_MESSAGE,
                "reason": "no observations" if latest is None else "latest observation is stale"}

    signals = [_evaluate_rising(obs, name, now) for name in RISING_SIGNALS]
    release = {"signal": "release_reported", "evaluable": False, "triggered": False, "detail": ""}
    spill = getattr(max(obs, key=lambda o: _aware(o.observed_at)), "spillway_m3s", None)
    if spill is None:
        release["detail"] = "spillway discharge not reported"
    else:
        release.update(evaluable=True, triggered=spill > 0,
                       detail=f"spillway discharge {spill} m3/s reported" if spill > 0
                       else "no spillway discharge reported")
    signals.append(release)

    evaluable = [s for s in signals if s["evaluable"]]
    if not evaluable:
        return {**base, "status": "insufficient_data", "signals": signals, "message": INSUFFICIENT_MESSAGE,
                "reason": "no signal could be evaluated from the available history"}
    triggered = [s for s in evaluable if s["triggered"]]
    if len(triggered) >= MIN_SIGNALS_FOR_CONCERN:
        return {**base, "status": "elevated_concern", "signals": signals,
                "message": f"{len(triggered)} documented conditions are present: "
                           + ", ".join(s["signal"] for s in triggered)
                           + ". This is not a flood prediction."}
    return {**base, "status": "monitoring", "signals": signals,
            "message": "Data available; fewer than two documented concern conditions present."}
