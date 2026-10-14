import datetime as dt
from types import SimpleNamespace as NS

from app.services.dam_assessment import INSUFFICIENT_MESSAGE, assess

NOW = dt.datetime(2026, 10, 14, 12, tzinfo=dt.timezone.utc)


def obs(days_ago, **vals):
    base = dict(reservoir_level_m=None, inflow_m3s=None, downstream_level_m=None, spillway_m3s=None,
                data_kind="historical")
    base.update(vals)
    return NS(observed_at=NOW - dt.timedelta(days=days_ago), **base)


def history(fn, n=80):
    return [obs(n - 1 - i, **fn(i)) for i in range(n)]


def _rising(i):
    # flat noisy history, then a sharp rise over the final days
    lvl = 480 + 0.02 * (i % 3)
    inflow = 100 + (i % 3)
    if i >= 75:
        lvl += (i - 74) * 0.5
        inflow += (i - 74) * 40
    return dict(reservoir_level_m=lvl, inflow_m3s=inflow)


def test_no_data_is_insufficient_never_a_risk_label():
    r = assess([], now=NOW)
    assert r["status"] == "insufficient_data" and r["message"] == INSUFFICIENT_MESSAGE


def test_stale_is_insufficient():
    assert assess([obs(30, reservoir_level_m=480)], now=NOW)["status"] == "insufficient_data"


def test_synthetic_data_is_ignored():
    o = obs(0, reservoir_level_m=480)
    o.data_kind = "synthetic_test"
    assert assess([o], now=NOW)["status"] == "insufficient_data"


def test_very_full_reservoir_alone_is_not_a_flood_claim():
    # no percent-full rule exists: a single high reading cannot yield any concern status
    r = assess([obs(0, reservoir_level_m=499)], now=NOW)
    assert r["status"] == "insufficient_data"


def test_short_history_cannot_trigger_rise_signals():
    r = assess(history(lambda i: dict(reservoir_level_m=480 + i * 0.5), n=10), now=NOW)
    sigs = {s["signal"]: s for s in r["signals"]}
    assert not sigs["reservoir_level_rising"]["evaluable"]
    assert r["status"] == "insufficient_data"


def test_two_unusual_rises_give_elevated_concern():
    r = assess(history(_rising), now=NOW)
    assert r["status"] == "elevated_concern", r
    assert "not a flood prediction" in r["message"]


def test_one_signal_is_only_monitoring():
    def f(i):
        d = _rising(i)
        d["inflow_m3s"] = 100 + (i % 3)
        return d
    assert assess(history(f), now=NOW)["status"] == "monitoring"


def test_official_notice_takes_precedence_and_is_quoted():
    n = NS(published_at=NOW - dt.timedelta(days=1), effective_from=None, effective_to=None,
           description="Notice text", source_reference="ref-1")
    r = assess([obs(0, reservoir_level_m=480)], [n], now=NOW)
    assert r["status"] == "official_release_notice" and r["notices"][0]["description"] == "Notice text"
    old = NS(published_at=NOW - dt.timedelta(days=30), effective_from=None, effective_to=None,
             description="x", source_reference="r")
    assert assess([obs(0, reservoir_level_m=480)], [old], now=NOW)["status"] != "official_release_notice"
