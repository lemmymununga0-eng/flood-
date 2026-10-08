"""Stage 3 leakage and target-construction tests.

§10 of the brief asks for an explicit automated leakage audit that demonstrates the
pipeline prevents leakage rather than asserting it. Several of these are guard-on-guard
tests: they construct a deliberately leaky control and assert the check CATCHES it, so a
test that passes vacuously cannot hide.

    python -m pytest ml/tests/test_s3_leakage.py -q
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
from ml.stage3.s2_build_dataset import FORBIDDEN, RAIN_WINDOWS  # noqa: E402


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    for name in ("forecasting_dataset.parquet", "forecasting_dataset.csv"):
        p = C.S3_OUT_PROCESSED / name
        if p.exists():
            d = (pd.read_parquet(p) if p.suffix == ".parquet"
                 else pd.read_csv(p, parse_dates=["date"], low_memory=False))
            return d.sort_values(["location_id", "date"]).reset_index(drop=True)
    pytest.skip("Stage 3 dataset not built; run ml/stage3/s2_build_dataset.py")


@pytest.fixture(scope="module")
def one(df) -> pd.DataFrame:
    loc = df.location_id.value_counts().idxmax()
    return df[df.location_id == loc].sort_values("date").set_index("date")


# ---------------------------------------------------------------------------
# Rolling windows look backward only
# ---------------------------------------------------------------------------

def test_rainfall_windows_are_backward_looking(one):
    for w in RAIN_WINDOWS:
        col = f"chirps_sum_{w}d"
        expected = one["chirps_precip_mm"].rolling(w, min_periods=w).sum()
        both = pd.concat([expected, one[col]], axis=1).dropna()
        np.testing.assert_allclose(
            both.iloc[:, 0].to_numpy(), both.iloc[:, 1].to_numpy(),
            rtol=1e-6, atol=1e-6,
            err_msg=f"{col} is not a strictly backward-looking sum")


def test_a_forward_shifted_window_would_be_caught(one):
    """Guard on the guard. If this passes, the test above proves nothing."""
    leaky = one["chirps_precip_mm"].shift(-3).rolling(7, min_periods=7).sum()
    honest = one["chirps_sum_7d"]
    both = pd.concat([leaky, honest], axis=1).dropna()
    assert len(both) > 100
    assert not np.allclose(both.iloc[:, 0], both.iloc[:, 1]), (
        "a deliberately forward-shifted window matched the shipped column")


def test_soil_wetness_is_lagged_not_same_day(one):
    both = pd.concat([one["GWETROOT"].shift(1), one["gwetroot_lag1"]], axis=1).dropna()
    np.testing.assert_allclose(both.iloc[:, 0].to_numpy(), both.iloc[:, 1].to_numpy(),
                               rtol=1e-9, atol=1e-9)
    same = pd.concat([one["GWETROOT"], one["gwetroot_lag1"]], axis=1).dropna()
    assert not np.allclose(same.iloc[:, 0], same.iloc[:, 1]), (
        "gwetroot_lag1 equals the same-day value — it is not lagged")


def test_rainfall_anomaly_uses_a_trailing_mean_not_a_global_one(one):
    """A whole-period climatology would embed post-t information. The trailing mean must
    change through time; a global mean would be constant."""
    trail = one["chirps_trailing_365d_mean"].dropna()
    assert trail.nunique() > 100, "trailing climatology is suspiciously constant"
    assert not np.isclose(trail.std(), 0.0)


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------

def test_targets_exclude_the_prediction_day_itself(df):
    """A flood ON day t must not make day t positive — that is nowcasting."""
    flood_days = df[df.is_flood_day == 1]
    assert len(flood_days) > 0
    for h in C.S3_HORIZONS:
        # On the onset day itself the (t, t+h] window starts tomorrow, so unless another
        # onset follows within h days the target must be 0.
        solo = flood_days[flood_days[f"target_h{h}"] == 1]
        for r in solo.head(20).itertuples():
            nxt = df[(df.location_id == r.location_id) & (df.date > r.date)
                     & (df.date <= r.date + pd.Timedelta(days=h))]
            assert nxt.is_flood_day.sum() > 0, (
                f"H+{h}: onset day marked positive with no onset in (t, t+{h}]")


def test_horizon_monotonicity(df):
    """A longer window cannot contain fewer events than a shorter one."""
    prev = None
    for h in sorted(C.S3_HORIZONS):
        n = int(df[f"target_h{h}"].sum())
        if prev is not None:
            assert n >= prev, f"H+{h} has fewer positives than the shorter horizon"
        prev = n


def test_masked_rows_are_never_positive(df):
    for h in C.S3_HORIZONS:
        masked = df[df[f"usable_h{h}"] == 0]
        if len(masked):
            assert (masked[f"target_h{h}"] == 0).all(), (
                f"H+{h}: a masked row carries a positive target")


def test_mask_actually_removes_rows(df):
    """The three-state scheme must do something — if nothing is masked it has collapsed
    back to the two-state design it replaces."""
    for h in C.S3_HORIZONS:
        assert (df[f"usable_h{h}"] == 0).sum() > 1000, (
            f"H+{h}: almost nothing masked; the third label state is not working")


def test_every_positive_traces_to_a_high_confidence_onset(df):
    pos = pd.read_csv(C.S3_OUT_PROCESSED / "labels_positive_district_days.csv",
                      parse_dates=["date"])
    rel = pd.read_csv(C.S3_DATE_RELIABILITY)[["record_id", "date_reliability"]]
    merged = pos.merge(rel, on="record_id", how="left")
    assert (merged.date_reliability == "onset_plausible").all(), (
        "a positive label came from a record that is not onset_plausible")


# ---------------------------------------------------------------------------
# Forbidden predictors
# ---------------------------------------------------------------------------

def test_target_leaking_flood_counts_are_absent(df):
    present = [c for c in df.columns if c in FORBIDDEN]
    assert not present, (
        f"{present} count every flood in the archive including post-t ones — "
        "a direct target leak")


def test_post_event_consequence_fields_never_entered(df):
    register = pd.read_csv(C.S3_REPORTS / "variable_leakage_register.csv")
    post = set(register[register.category == "POST-EVENT"].variable.astype(str))
    leaked = [c for c in df.columns if c in post]
    assert not leaked, f"post-event consequence fields present as features: {leaked}"


def test_climate_indices_are_lagged(df):
    assert "oni_lag2m" in df.columns, "ONI must be present only in its lag-2 form"
    assert "oni" not in df.columns, "un-lagged ONI is not final until month m+1"
    for unsafe in ("nino34_anom", "dmi_hadisst"):
        assert unsafe not in df.columns, f"{unsafe} present un-lagged"
