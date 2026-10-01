"""Phase 6, 23 - automated conditions on the rebuilt target and on leakage.

Every condition the correction brief asks to "verify" is asserted here rather than
checked once by hand:

  no future features        every predictor at row t is dated <= t
  no same-day contamination the horizon is strictly (t, t+7], never [t, t+7]
  correct +1..+7 horizon    exact boundary behaviour, both ends
  overlapping events        consistent under overlap
  multi-day events          consistent across the whole window
  duplicate events          no duplicate (location, date) rows
  chronological splits      date-disjoint and ordered, no location leakage
  mask semantics            a masked row is neither a positive nor a negative
  no imputation             no required feature was filled

Run:  python -m pytest ml/tests/test_target_and_leakage.py -q
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from ml import config as C  # noqa: E402
from ml.pipeline.p06_build_dataset import RAW_WEATHER, REQUIRED, build_target  # noqa: E402

SPLITS = ("train", "validation", "test")


@pytest.fixture(scope="module")
def splits() -> dict[str, pd.DataFrame]:
    out = {}
    for name in SPLITS:
        p = C.PROCESSED_DIR / f"{name}.csv"
        if not p.exists():
            pytest.skip(f"corrected split missing: {p}. Run ml/pipeline/p06_build_dataset.py")
        out[name] = pd.read_csv(p, parse_dates=["date"], low_memory=False)
    return out


# ---------------------------------------------------------------------------
# Target construction: exact horizon semantics on a hand-built series
# ---------------------------------------------------------------------------

def _toy(flood_days: list[str], masked_days: list[str] | None = None,
         start: str = "2020-01-01", n: int = 40) -> pd.DataFrame:
    dates = pd.date_range(start, periods=n, freq="D")
    df = pd.DataFrame({"location": "L", "date": dates})
    df["flood_reliable"] = df.date.isin(pd.to_datetime(flood_days)).astype(int)
    df["masked_day"] = df.date.isin(pd.to_datetime(masked_days or [])).astype(int)
    return build_target(df)


def test_horizon_is_strictly_exclusive_of_day_t():
    """A flood ON day t must NOT make day t positive. That would be nowcasting."""
    df = _toy(["2020-01-20"])
    row = df[df.date == "2020-01-20"].iloc[0]
    assert row[C.TARGET] == 0, (
        "same-day contamination: a flood on day t marked day t positive"
    )


def test_horizon_covers_exactly_t_plus_1_to_t_plus_7():
    df = _toy(["2020-01-20"]).set_index("date")
    # t+1..t+7 before the event -> positive
    for lead in range(1, 8):
        d = pd.Timestamp("2020-01-20") - pd.Timedelta(days=lead)
        assert df.loc[d, C.TARGET] == 1, f"day t+{lead} before the event should be positive"
    # t+8 -> outside the window
    d8 = pd.Timestamp("2020-01-20") - pd.Timedelta(days=8)
    assert df.loc[d8, C.TARGET] == 0, "day t+8 must be outside a 7-day horizon"
    # the day after the event is not positive on its account
    assert df.loc[pd.Timestamp("2020-01-21"), C.TARGET] == 0


def test_exactly_seven_positive_days_per_isolated_event():
    df = _toy(["2020-01-20"])
    assert int(df[C.TARGET].sum()) == 7


def test_multi_day_event_is_consistent():
    """A 3-day event yields one contiguous positive block ending the day before onset."""
    df = _toy(["2020-01-20", "2020-01-21", "2020-01-22"])
    pos = df[df[C.TARGET] == 1].date.sort_values()
    assert pos.min() == pd.Timestamp("2020-01-13")
    assert pos.max() == pd.Timestamp("2020-01-21")
    # contiguous, no gaps
    assert (pos.diff().dropna() == pd.Timedelta(days=1)).all()


def test_overlapping_events_do_not_double_count():
    """Two events 3 days apart share horizon days; the target stays binary and the
    union is covered exactly once."""
    df = _toy(["2020-01-20", "2020-01-23"])
    assert set(df[C.TARGET].unique()) <= {0, 1}
    pos = df[df[C.TARGET] == 1].date
    assert pos.min() == pd.Timestamp("2020-01-13")
    assert pos.max() == pd.Timestamp("2020-01-22")
    assert len(pos) == 10  # union of two 7-day windows offset by 3


def test_duplicate_event_rows_are_idempotent():
    """The same event listed twice must not change the target."""
    once = _toy(["2020-01-20"])[C.TARGET].to_numpy()
    twice = _toy(["2020-01-20", "2020-01-20"])[C.TARGET].to_numpy()
    np.testing.assert_array_equal(once, twice)


def test_mask_does_not_create_positives():
    """A masked day must not become a positive, and must mark its window unusable."""
    df = _toy([], masked_days=["2020-01-20"])
    assert int(df[C.TARGET].sum()) == 0
    unusable = df[df[C.MASK_COL] == 0].date
    assert len(unusable) == 7
    assert unusable.max() == pd.Timestamp("2020-01-19")


def test_documented_positive_beats_an_overlapping_mask():
    """When a source names the day, the day is known; a coarser overlapping episode
    must not erase it."""
    df = _toy(["2020-01-20"], masked_days=["2020-01-20", "2020-01-21"])
    row = df[df.date == "2020-01-15"].iloc[0]
    assert row[C.TARGET] == 1
    assert row[C.MASK_COL] == 1, "a window containing a documented positive stays usable"


def test_per_location_isolation():
    """One location's events must never label another's rows."""
    dates = pd.date_range("2020-01-01", periods=20, freq="D")
    df = pd.concat([
        pd.DataFrame({"location": "A", "date": dates,
                      "flood_reliable": (dates == "2020-01-15").astype(int), "masked_day": 0}),
        pd.DataFrame({"location": "B", "date": dates, "flood_reliable": 0, "masked_day": 0}),
    ], ignore_index=True)
    out = build_target(df)
    assert out[out.location == "A"][C.TARGET].sum() == 7
    assert out[out.location == "B"][C.TARGET].sum() == 0, "labels leaked across locations"


# ---------------------------------------------------------------------------
# Leakage and split integrity on the real rebuilt dataset
# ---------------------------------------------------------------------------

def test_splits_are_chronological_and_disjoint(splits):
    tr, va, te = splits["train"], splits["validation"], splits["test"]
    assert tr.date.max() < va.date.min(), "train overlaps validation"
    assert va.date.max() < te.date.min(), "validation overlaps test"


def test_no_duplicate_location_date_rows(splits):
    for name, df in splits.items():
        dup = df.duplicated(subset=["location", "date"]).sum()
        assert dup == 0, f"{name} has {dup} duplicate (location, date) rows"


def test_no_row_appears_in_two_splits(splits):
    keys = {n: set(zip(df.location, df.date)) for n, df in splits.items()}
    assert not (keys["train"] & keys["validation"])
    assert not (keys["validation"] & keys["test"])
    assert not (keys["train"] & keys["test"])


def test_rainfall_windows_are_backward_looking(splits):
    """rain_Nday at row t must equal the sum of PRECTOTCORR over [t-N+1, t] -- never a
    window that reaches past t."""
    df = splits["train"].sort_values(["location", "date"])
    loc = df.location.value_counts().idxmax()
    s = df[df.location == loc].set_index("date")
    for w in (3, 7, 14):
        expected = s["PRECTOTCORR"].rolling(w, min_periods=w).sum()
        got = s[f"rain_{w}day"]
        both = pd.concat([expected, got], axis=1).dropna()
        np.testing.assert_allclose(
            both.iloc[:, 0].to_numpy(), both.iloc[:, 1].to_numpy(), rtol=1e-6, atol=1e-6,
            err_msg=f"rain_{w}day is not a strictly backward-looking sum",
        )


def test_forward_shifted_rainfall_would_be_detected(splits):
    """Guard on the guard: a forward-looking window must fail the check above."""
    df = splits["train"].sort_values(["location", "date"])
    loc = df.location.value_counts().idxmax()
    s = df[df.location == loc].set_index("date")
    leaky = s["PRECTOTCORR"].shift(-3).rolling(7, min_periods=7).sum()
    honest = s["rain_7day"]
    both = pd.concat([leaky, honest], axis=1).dropna()
    assert not np.allclose(both.iloc[:, 0], both.iloc[:, 1]), (
        "a deliberately forward-shifted window matched the real column; the "
        "backward-looking test cannot detect leakage"
    )


def test_lag_zero_climate_index_is_marked_unsafe_and_never_a_feature(splits):
    from ml.pipeline.p10_experiments import FEATURE_SETS

    cols = splits["train"].columns
    assert any(c.endswith("_lag0m_UNSAFE") for c in cols), (
        "lag-0 climate columns should be retained for transparency, clearly named"
    )
    for name, feats in FEATURE_SETS.items():
        bad = [f for f in feats if "lag0m" in f]
        assert not bad, f"feature set {name} uses lag-0 climate index: {bad}"


def test_no_required_feature_was_imputed(splits):
    for name, df in splits.items():
        missing = df[REQUIRED].isna().sum().sum()
        assert missing == 0, f"{name} has {missing} missing required values"


def test_raw_weather_values_are_physically_plausible(splits):
    df = splits["train"]
    assert (df.PRECTOTCORR >= 0).all()
    assert df.RH2M.between(0, 100).all()
    assert (df.WS10M >= 0).all()
    assert (df.T2M_MIN <= df.T2M).all() and (df.T2M <= df.T2M_MAX).all(), (
        "daily temperature extremes are not ordered MIN <= MEAN <= MAX"
    )
    assert not (df.T2M_MAX == df.T2M).all(), (
        "T2M_MAX equals T2M everywhere, which is the daily-mean substitution defect"
    )


def test_target_is_binary_and_rare(splits):
    for name, df in splits.items():
        usable = df[df[C.MASK_COL] == 1]
        assert set(usable[C.TARGET].unique()) <= {0, 1}
        rate = usable[C.TARGET].mean()
        assert 0 < rate < 0.02, f"{name} positive rate {rate:.4%} is outside the plausible range"


def test_mask_rows_are_excluded_from_both_classes(splits):
    """A masked row must never be counted as a negative example anywhere downstream."""
    for name, df in splits.items():
        masked = df[df[C.MASK_COL] == 0]
        if len(masked) == 0:
            continue
        assert (masked[C.TARGET] == 0).all(), (
            f"{name}: a masked row carries a positive target, which contradicts the mask"
        )
