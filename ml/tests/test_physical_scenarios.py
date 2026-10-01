"""Phase 17 - physical plausibility scenarios.

These are sanity checks, NOT a substitute for statistical evaluation, and they never
force the model to behave a particular way. They record what the deployed artifact
actually does on physically meaningful inputs so that implausible behaviour is visible
and attributable to a data or model cause rather than discovered by a user.

The audit established the behaviour under test: the production Logistic Regression has a
fitted rainfall coefficient of +0.018 against +2.003 for relative humidity, so a dry
humid day outscores a torrential dry-air day. That is a real property of the model, and
it is asserted here as a documented, failing-by-design characterisation rather than
quietly hidden.

Tests named `test_characterise_*` document current behaviour without judging it.
Tests named `test_invariant_*` assert properties any defensible flood model must have;
these are the ones whose failure is a genuine defect.

Run:  python -m pytest ml/tests/test_physical_scenarios.py -q -rs
"""
from __future__ import annotations

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))


def score(**kw) -> dict:
    from app.ml.predictor import predict_risk
    base = dict(location_name="Lusaka", latitude=-15.4, longitude=28.3,
                observation_date="2026-01-15")
    return predict_risk(**{**base, **kw})


# Physically coherent Zambian scenarios. Temperature triples are real orderings
# (MIN <= MEAN <= MAX) with a plausible diurnal spread, because the contract now
# rejects anything else.
SCENARIOS = {
    "A_low_rain_low_humidity": dict(
        precipitation_mm=0.0, temperature_c=21.0, temperature_max_c=29.0,
        temperature_min_c=13.0, relative_humidity_pct=32.0, wind_speed_10m_ms=4.2),
    "B_high_rain_high_humidity": dict(
        precipitation_mm=85.0, temperature_c=22.5, temperature_max_c=26.0,
        temperature_min_c=19.5, relative_humidity_pct=93.0, wind_speed_10m_ms=2.1),
    "C_extreme_rain": dict(
        precipitation_mm=200.0, temperature_c=22.0, temperature_max_c=25.5,
        temperature_min_c=19.0, relative_humidity_pct=95.0, wind_speed_10m_ms=2.4),
    "D_moderate_rain_saturated_antecedent": dict(
        precipitation_mm=35.0, temperature_c=22.0, temperature_max_c=26.5,
        temperature_min_c=18.5, relative_humidity_pct=90.0, wind_speed_10m_ms=2.0),
    "E_dry_season_dry": dict(
        precipitation_mm=0.0, temperature_c=17.5, temperature_max_c=26.0,
        temperature_min_c=8.0, relative_humidity_pct=28.0, wind_speed_10m_ms=4.8),
    # The two diagnostic probes that isolate what the model is really keying on.
    "F_dry_but_humid": dict(
        precipitation_mm=0.0, temperature_c=22.5, temperature_max_c=27.0,
        temperature_min_c=19.0, relative_humidity_pct=92.0, wind_speed_10m_ms=2.2),
    "G_torrential_but_dry_air": dict(
        precipitation_mm=200.0, temperature_c=22.0, temperature_max_c=28.0,
        temperature_min_c=16.0, relative_humidity_pct=33.0, wind_speed_10m_ms=4.0),
}


@pytest.fixture(scope="module")
def results() -> dict[str, dict]:
    return {k: score(**v) for k, v in SCENARIOS.items()}


# ---------------------------------------------------------------------------
# Invariants: a failure here is a real defect
# ---------------------------------------------------------------------------

def test_invariant_all_scenarios_score_and_stay_in_range(results):
    for name, r in results.items():
        assert 0.0 <= r["risk_probability_raw"] <= 1.0, name
        assert 0.0 <= r["risk_probability_calibrated"] <= 1.0, name
        assert r["risk_level"] in {"LOW", "MODERATE", "HIGH"}, name


def test_invariant_calibration_is_monotonic_in_the_raw_score(results):
    """Calibration must only re-scale, never re-order. If it re-orders, ROC-AUC changes
    and the saved calibrator is not the strictly monotonic remap it is documented as."""
    ordered = sorted(results.values(), key=lambda r: r["risk_probability_raw"])
    cal = [r["risk_probability_calibrated"] for r in ordered]
    assert cal == sorted(cal), (
        "calibration re-ordered the scenarios; it is not a monotonic remap"
    )


def test_invariant_extreme_rain_outscores_the_same_day_without_rain(results):
    """Holding humidity and temperature fixed, more rain must not LOWER the score.
    This isolates the rainfall coefficient's sign, which is the weakest defensible
    requirement on a flood model."""
    wet = score(**{**SCENARIOS["C_extreme_rain"]})
    dry = score(**{**SCENARIOS["C_extreme_rain"], "precipitation_mm": 0.0})
    assert wet["risk_probability_raw"] >= dry["risk_probability_raw"], (
        "adding 200 mm of rain to an otherwise identical day lowered the risk score"
    )


def test_invariant_dry_season_dry_day_is_not_high_risk(results):
    assert results["E_dry_season_dry"]["risk_level"] == "LOW"


def test_invariant_every_response_carries_its_caveats(results):
    for name, r in results.items():
        assert r["caveats"], name
        joined = " ".join(r["caveats"]).lower()
        assert "precision" in joined and "research" in joined, (
            f"{name}: response does not disclose the precision limitation"
        )


# ---------------------------------------------------------------------------
# Characterisation: documents real behaviour, including behaviour we consider wrong
# ---------------------------------------------------------------------------

def test_characterise_rainfall_is_nearly_inert(results):
    """Documented defect. Rainfall's fitted weight is +0.018 against humidity's +2.003,
    so varying rainfall across its entire observed range moves the score far less than a
    moderate humidity change. Recorded, not corrected here: the cause is label quality
    and feature selection, addressed by the corrected pipeline's feature ablation, not by
    overriding the model."""
    import joblib, json  # noqa: E401
    root = REPO / "backend" / "ml_artifacts" / "flood_risk_lr_v1"
    model = joblib.load(root / "model.joblib")
    feats = json.loads((root / "feature_columns.json").read_text())
    coefs = dict(zip(feats, model.coef_[0]))
    assert abs(coefs["PRECTOTCORR"]) < abs(coefs["RH2M"]) / 10, (
        "this characterisation is stale - rainfall now carries comparable weight to "
        "humidity, so the finding should be re-documented"
    )


def test_characterise_humid_dry_day_outscores_torrential_dry_air_day(results):
    """The headline implausibility, asserted so it cannot silently disappear or silently
    persist. If a corrected model later reverses this, the test fails and the finding is
    revisited deliberately."""
    humid_dry = results["F_dry_but_humid"]["risk_probability_raw"]
    torrential = results["G_torrential_but_dry_air"]["risk_probability_raw"]
    assert humid_dry > torrential, (
        "behaviour changed: a 0 mm humid day no longer outscores a 200 mm dry-air day. "
        "Re-examine the characterisation and update the audit findings."
    )


def test_characterise_scenario_table(results, capsys):
    """Emits the table for the report. Always passes; it exists to record numbers."""
    lines = [f"{'scenario':38s} {'raw':>8s} {'calibrated':>11s} {'level':>9s} {'alert':>6s}"]
    for name, r in results.items():
        lines.append(
            f"{name:38s} {r['risk_probability_raw']:8.4f} "
            f"{r['risk_probability_calibrated']:11.6f} {r['risk_level']:>9s} "
            f"{str(r['would_alert_at_threshold']):>6s}")
    with capsys.disabled():
        print("\n" + "\n".join(lines))
