"""Phase 3 - end-to-end training/inference parity.

The defect this test exists to prevent: production silently fed the model a different
feature vector than training produced, and nothing failed. Specifically it substituted
the daily mean temperature for both daily extremes and supplied 2 m wind where the model
expects 10 m wind. The first of those flipped the alert decision on 49.8% of rows.

The contract is ml/contracts/feature_contract.json. These tests assert that:

  1. the production weather provider requests every contract feature, and requests no
     substitute variable;
  2. for the same real historical observation, the inference path and the training path
     produce the same feature vector and therefore the same probability;
  3. feature ORDER and NAME mapping are correct, not merely feature count;
  4. the previously-shipped substitution is now refused rather than scored.

Run:  python -m pytest ml/tests/test_feature_parity.py -q
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))

from ml import config as C  # noqa: E402

# Bit-level equality is not promised across a float32 CSV round-trip, so parity is
# asserted to a tolerance tight enough that any real semantic swap fails loudly.
PROBABILITY_TOLERANCE = 1e-9
N_PARITY_ROWS = 400


@pytest.fixture(scope="module")
def contract() -> dict:
    return json.loads((C.CONTRACTS_DIR / "feature_contract.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def artifacts() -> dict:
    import joblib
    root = REPO / "backend" / "ml_artifacts" / "flood_risk_lr_v1"
    return {
        "model": joblib.load(root / "model.joblib"),
        "scaler": joblib.load(root / "scaler.joblib"),
        "features": json.loads((root / "feature_columns.json").read_text(encoding="utf-8")),
    }


@pytest.fixture(scope="module")
def historical() -> pd.DataFrame:
    """Real NASA POWER observations, read from the preserved baseline test split."""
    p = C.BASELINE_PROCESSED_DIR / "test.csv"
    if not p.exists():
        pytest.skip(f"baseline split not available at {p}")
    cols = ["date", "location", "PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M", "WS10M"]
    df = pd.read_csv(p, usecols=cols, parse_dates=["date"], low_memory=False)
    # Deterministic spread across the period rather than a contiguous block.
    return df.iloc[:: max(1, len(df) // N_PARITY_ROWS)].head(N_PARITY_ROWS).reset_index(drop=True)


# --------------------------------------------------------------------------
# 1. The provider must request exactly the contract's variables
# --------------------------------------------------------------------------

def test_provider_requests_every_contract_feature(contract):
    from app.integrations.weather_provider import NASA_POWER_PARAMETERS

    requested = {p.strip() for p in NASA_POWER_PARAMETERS.split(",")}
    required = {f["source_parameter"] for f in contract["features"]}

    assert required <= requested, (
        f"weather provider does not request contract feature(s): {sorted(required - requested)}. "
        "A missing parameter is what forced the earlier daily-mean substitution."
    )


def test_provider_requests_no_substitute_variable(contract):
    """WS2M must not reappear. It is a different physical variable from WS10M."""
    from app.integrations.weather_provider import NASA_POWER_PARAMETERS

    requested = {p.strip() for p in NASA_POWER_PARAMETERS.split(",")}
    assert "WS2M" not in requested, (
        "Provider requests WS2M. The model was trained on WS10M (10 m wind); the two "
        "differ by roughly 25-40% under the log wind profile."
    )
    assert "WS10M" in requested


def test_contract_covers_exactly_the_model_feature_columns(contract, artifacts):
    contract_names = [f["name"] for f in contract["features"]]
    assert contract_names == artifacts["features"], (
        "Contract feature list and the model artifact's feature_columns.json disagree. "
        f"contract={contract_names} artifact={artifacts['features']}"
    )
    assert artifacts["scaler"].n_features_in_ == len(contract_names)


def test_no_contract_feature_is_left_unavailable(contract):
    unavailable = [f["name"] for f in contract["features"]
                   if f["status"] not in ("CONFORMANT", "REPAIRED")]
    assert not unavailable, f"Features neither conformant nor repaired: {unavailable}"


# --------------------------------------------------------------------------
# 2 & 3. Feature-vector and probability parity on real observations
# --------------------------------------------------------------------------

def test_inference_path_reproduces_training_feature_vector(historical, artifacts):
    """The inference path builds its vector from a NAME->value mapping; the training
    path from a column-ordered DataFrame. They must agree for every row."""
    from app.ml.predictor import predict_risk

    feats = artifacts["features"]
    coefs = artifacts["model"].coef_[0]
    training_matrix = historical[feats].to_numpy(dtype=float)

    # What the training pipeline's own preprocessing yields, expressed as the same
    # per-feature contributions the inference path reports (coef * scaled value).
    scaled_from_training = artifacts["scaler"].transform(training_matrix)
    expected = np.round(scaled_from_training * coefs, 4)

    reported = []
    for row in historical.itertuples():
        out = predict_risk(
            location_name=row.location,
            latitude=None, longitude=None,
            precipitation_mm=row.PRECTOTCORR,
            temperature_c=row.T2M,
            temperature_max_c=row.T2M_MAX,
            temperature_min_c=row.T2M_MIN,
            relative_humidity_pct=row.RH2M,
            wind_speed_10m_ms=row.WS10M,
            observation_date=row.date.strftime("%Y-%m-%d"),
        )
        # Read the vector the inference path actually scored back out of its own
        # per-feature explanation, keyed by NAME, so a silent reordering cannot pass.
        contrib = {c["feature"]: c["contribution"] for c in out["explanation"]}
        assert set(contrib) == set(feats), (
            f"inference reported features {sorted(contrib)}, contract expects {sorted(feats)}"
        )
        reported.append([contrib[f] for f in feats])

    reported = np.array(reported)
    for j, f in enumerate(feats):
        np.testing.assert_allclose(
            reported[:, j], expected[:, j], rtol=0, atol=1e-9,
            err_msg=(
                f"feature '{f}' (column {j}) differs between the training and inference "
                "paths. A mismatch here means production is scoring a different vector "
                "than the model was validated on."
            ),
        )


def test_inference_probability_matches_training_pipeline(historical, artifacts):
    from app.ml.predictor import predict_risk

    feats = artifacts["features"]
    expected = artifacts["model"].predict_proba(
        artifacts["scaler"].transform(historical[feats].to_numpy(dtype=float))
    )[:, 1]

    got = np.array([
        predict_risk(
            location_name=row.location, latitude=None, longitude=None,
            precipitation_mm=row.PRECTOTCORR, temperature_c=row.T2M,
            temperature_max_c=row.T2M_MAX, temperature_min_c=row.T2M_MIN,
            relative_humidity_pct=row.RH2M, wind_speed_10m_ms=row.WS10M,
        )["risk_probability_raw"]
        for row in historical.itertuples()
    ])

    # predict_risk rounds its reported probability to 4dp, so compare at that scale.
    np.testing.assert_allclose(got, np.round(expected, 4), atol=PROBABILITY_TOLERANCE)


def test_swapped_max_min_would_be_detected(historical, artifacts):
    """Guard on the guard: if T2M_MAX and T2M_MIN were transposed, parity must break.
    A parity test that passes under a swap is not testing anything."""
    from app.ml.predictor import predict_risk

    feats = artifacts["features"]
    row = historical.iloc[0]
    correct = predict_risk(
        location_name="x", latitude=None, longitude=None,
        precipitation_mm=row.PRECTOTCORR, temperature_c=row.T2M,
        temperature_max_c=row.T2M_MAX, temperature_min_c=row.T2M_MIN,
        relative_humidity_pct=row.RH2M, wind_speed_10m_ms=row.WS10M,
    )["risk_probability_raw"]

    # Swapping makes MIN > MAX, which the physical-ordering guard now rejects outright.
    with pytest.raises(ValueError, match="not physically ordered"):
        predict_risk(
            location_name="x", latitude=None, longitude=None,
            precipitation_mm=row.PRECTOTCORR, temperature_c=row.T2M,
            temperature_max_c=row.T2M_MIN, temperature_min_c=row.T2M_MAX,
            relative_humidity_pct=row.RH2M, wind_speed_10m_ms=row.WS10M,
        )
    assert 0.0 <= correct <= 1.0


# --------------------------------------------------------------------------
# 4. The shipped defect must now be refused
# --------------------------------------------------------------------------

def test_daily_mean_substitution_is_refused(historical):
    """The exact call populate_real_data.py used to make."""
    from app.ml.predictor import predict_risk

    row = historical.iloc[0]
    with pytest.raises(ValueError, match="all identical"):
        predict_risk(
            location_name="x", latitude=None, longitude=None,
            precipitation_mm=row.PRECTOTCORR,
            temperature_c=row.T2M,
            temperature_max_c=row.T2M,   # the defect
            temperature_min_c=row.T2M,   # the defect
            relative_humidity_pct=row.RH2M,
            wind_speed_10m_ms=row.WS10M,
        )


def test_missing_feature_is_refused_not_imputed():
    from app.ml.predictor import predict_risk

    with pytest.raises(ValueError, match="Missing required weather value"):
        predict_risk(
            location_name="x", latitude=None, longitude=None,
            precipitation_mm=float("nan"), temperature_c=22.0,
            temperature_max_c=28.0, temperature_min_c=17.0,
            relative_humidity_pct=80.0, wind_speed_10m_ms=3.0,
        )


def test_response_records_the_target_window():
    """A 7-day forecast must record which 7 days it refers to, or it can never be
    verified after the fact."""
    from app.ml.predictor import predict_risk

    out = predict_risk(
        location_name="Lusaka", latitude=-15.4, longitude=28.3,
        precipitation_mm=12.0, temperature_c=22.0,
        temperature_max_c=28.0, temperature_min_c=17.0,
        relative_humidity_pct=85.0, wind_speed_10m_ms=3.0,
        observation_date="2026-01-10",
    )
    assert out["target_window_start"] == "2026-01-11"
    assert out["target_window_end"] == "2026-01-17"
    assert out["feature_contract_version"] == "1.0.0"
