"""Real flood-risk inference against the validated production model artifact.

The model is a Logistic Regression trained on six NASA POWER daily weather variables
(Experiment A, weather-only), chronologically split and leakage-audited. Its real,
honestly-reported performance is in the artifact's own metadata and in the registered
ModelVersion row: test ROC-AUC 0.777, recall 0.889, and precision 0.0006 — that last
number is not a typo, and it is why every response from this module carries explicit
caveats. This serves a research-grade risk signal, not a deployable public alert.

Artifacts loaded (from settings.model_artifact_dir):
  model.joblib / scaler.joblib / calibrator.joblib / feature_columns.json /
  threshold_metadata.json

Nothing here fabricates a prediction: a missing input raises, and a missing artifact
raises — neither is quietly defaulted.
"""
from __future__ import annotations

import datetime
import json
import pathlib
from functools import lru_cache

import joblib
import numpy as np

from app.core.config import get_settings

# Which artifact to serve. Settable via ACTIVE_MODEL_VERSION so the corrected
# pipeline's artifact can be promoted without editing code; defaults to the
# original so existing behaviour is unchanged until a switch is made deliberately.
DEFAULT_MODEL_VERSION = "flood_risk_lr_v1"
WEATHER_ONLY_FEATURES = ("PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M", "WS10M")


def active_model_version() -> str:
    return get_settings().active_model_version or DEFAULT_MODEL_VERSION


# Retained as a module constant for callers that import it (scripts, tests).
MODEL_VERSION = DEFAULT_MODEL_VERSION
PREDICTION_HORIZON_DAYS = 7
# The feature contract these inputs must satisfy (ml/contracts/feature_contract.json).
FEATURE_CONTRACT_VERSION = "1.0.0"

# Risk bands are percentiles of the calibrated probability distribution measured on the
# VALIDATION split (never test). Sigmoid calibration compresses all outputs toward the
# ~0.2% base rate, so absolute cutoffs like 0.10 would classify every day as LOW and be
# useless. These express RELATIVE risk ranking, which is what the calibration evidence
# actually supports (see the research bundle's docs/CALIBRATION_ANALYSIS.md).
#   validation p90 = 0.00288  -> MODERATE (top ~10% of days)
#   validation p99 = 0.00335  -> HIGH     (top ~1% of days)
_FALLBACK_BANDS = {"MODERATE": 0.0029, "HIGH": 0.0034}


class ModelArtifactsUnavailable(RuntimeError):
    """Raised when the model artifacts are not present/loadable. Callers surface this
    honestly rather than falling back to a synthetic prediction."""


@lru_cache(maxsize=4)
def _artifacts(version: str | None = None) -> dict:
    version = version or active_model_version()
    root = get_settings().model_artifact_path / version
    if not root.exists():
        raise ModelArtifactsUnavailable(
            f"Model artifact directory not found: {root}. No prediction can be served."
        )
    try:
        features = json.loads((root / "feature_columns.json").read_text())
        # Risk bands ship with the artifact when the producing pipeline measured them.
        # Falling back to the v1 constants is explicit rather than silent.
        bands_file = root / "risk_bands.json"
        if bands_file.exists():
            raw_bands = json.loads(bands_file.read_text())
            bands = {k: float(v) for k, v in raw_bands.items()
                     if k in ("MODERATE", "HIGH", "CRITICAL")}
        else:
            bands = dict(_FALLBACK_BANDS)
        return {
            "version": version,
            "model": joblib.load(root / "model.joblib"),
            "scaler": joblib.load(root / "scaler.joblib"),
            "calibrator": joblib.load(root / "calibrator.joblib"),
            "features": features,
            "threshold": json.loads((root / "threshold_metadata.json").read_text())["threshold"],
            "bands": bands,
        }
    except Exception as exc:  # noqa: BLE001 - surfaced honestly to the caller
        raise ModelArtifactsUnavailable(f"Failed to load model artifacts from {root}: {exc}") from exc


def artifacts_available() -> bool:
    """Used by /system-status to report real ML availability instead of guessing."""
    try:
        _artifacts()
        return True
    except ModelArtifactsUnavailable:
        return False


def risk_level(probability: float, bands: dict[str, float] | None = None) -> str:
    """Band the calibrated score. Bands express RELATIVE risk (validation percentiles),
    never an absolute chance of flooding."""
    b = bands or _FALLBACK_BANDS
    for name in ("CRITICAL", "HIGH", "MODERATE"):
        if name in b and probability >= b[name]:
            return name
    return "LOW"


def predict_risk(
    *,
    location_name: str,
    latitude: float | None,
    longitude: float | None,
    precipitation_mm: float,
    temperature_c: float,
    temperature_max_c: float,
    temperature_min_c: float,
    relative_humidity_pct: float,
    wind_speed_10m_ms: float,
    observation_date: str | None = None,
    extra_features: dict[str, float] | None = None,
    model_version: str | None = None,
) -> dict:
    """Run real inference. Returns a risk assessment dict — never a deterministic
    "flood will occur" claim.

    latitude/longitude are echoed for traceability only; the production model is
    weather-only (spatial features were tested and did not improve performance)."""
    art = _artifacts(model_version)

    named = {
        "PRECTOTCORR": precipitation_mm,
        "T2M": temperature_c,
        "T2M_MAX": temperature_max_c,
        "T2M_MIN": temperature_min_c,
        "RH2M": relative_humidity_pct,
        "WS10M": wind_speed_10m_ms,
    }
    missing = [k for k, v in named.items() if v is None or np.isnan(float(v))]
    if missing:
        raise ValueError(
            f"Missing required weather value(s): {missing}. This pipeline never imputes "
            f"weather inputs — supply a real observation for every field."
        )

    # Feature-contract guard. The previous production path substituted the daily MEAN
    # for both temperature extremes, which flipped the alert decision on 49.8% of rows.
    # A degenerate triple is therefore rejected outright rather than scored, because the
    # scaler, calibrator and risk bands were all fitted against real daily extremes.
    if temperature_max_c == temperature_c == temperature_min_c:
        raise ValueError(
            "T2M_MAX, T2M and T2M_MIN are all identical. The model was trained on real "
            "daily temperature extremes (mean observed spread: +6.6 C max, -5.7 C min); "
            "substituting the daily mean for the extremes invalidates the scaler, the "
            "calibrator and the risk bands. Supply real T2M_MAX/T2M_MIN values, or treat "
            "this observation as unavailable — do not score it."
        )
    if not (temperature_min_c <= temperature_c <= temperature_max_c):
        raise ValueError(
            f"Temperature values are not physically ordered: T2M_MIN={temperature_min_c}, "
            f"T2M={temperature_c}, T2M_MAX={temperature_max_c}. Expected MIN <= MEAN <= MAX."
        )

    # Any artifact feature beyond the six weather variables (rainfall accumulation,
    # antecedent soil moisture, climate indices) must be supplied by the caller. It is
    # never derived from the single day's values and never defaulted -- a model trained on
    # a 7-day rainfall sum cannot be fed a one-day value dressed up as one.
    named.update({k: v for k, v in (extra_features or {}).items()})
    unmet = [f for f in art["features"] if f not in named]
    if unmet:
        raise ValueError(
            f"Artifact '{art['version']}' requires feature(s) not supplied: {unmet}. "
            f"Pass them in extra_features. This pipeline never substitutes or derives a "
            f"missing predictor."
        )
    bad = [f for f in art["features"]
           if named[f] is None or np.isnan(float(named[f]))]
    if bad:
        raise ValueError(f"Missing required weather value(s): {bad}.")

    X = np.array([[float(named[f]) for f in art["features"]]])
    X_scaled = art["scaler"].transform(X)
    raw = float(art["model"].predict_proba(X_scaled)[0, 1])
    calibrated = float(art["calibrator"].predict_proba(X_scaled)[0, 1])

    coefs = art["model"].coef_[0]
    explanation = sorted(
        (
            {
                "feature": f,
                "contribution": round(float(c * x), 4),
                "direction": "increases risk" if c * x > 0 else "decreases risk",
            }
            for f, c, x in zip(art["features"], coefs, X_scaled[0])
        ),
        key=lambda d: abs(d["contribution"]),
        reverse=True,
    )

    # The (t, t+7] window this probability actually refers to. Recorded so a stored
    # prediction can be verified against what later happened, instead of being an
    # unfalsifiable number.
    window_start = window_end = None
    if observation_date:
        try:
            obs = datetime.date.fromisoformat(observation_date)
            window_start = (obs + datetime.timedelta(days=1)).isoformat()
            window_end = (obs + datetime.timedelta(days=PREDICTION_HORIZON_DAYS)).isoformat()
        except ValueError:
            pass

    return {
        "location": location_name,
        "latitude": latitude,
        "longitude": longitude,
        "prediction_horizon_days": PREDICTION_HORIZON_DAYS,
        "risk_probability_raw": round(raw, 4),
        "risk_probability_calibrated": round(calibrated, 4),
        "risk_level": risk_level(calibrated, art["bands"]),
        "would_alert_at_threshold": bool(raw >= art["threshold"]),
        "decision_threshold": art["threshold"],
        "model_version": art["version"],
        "generated_at": datetime.datetime.now(datetime.timezone.utc),
        "observation_date": observation_date,
        "target_window_start": window_start,
        "target_window_end": window_end,
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "explanation": explanation,
        "caveats": [
            "Feature contributions are correlational, not causal.",
            "Backtested precision at this threshold is ~0.06% (many false alarms per true "
            "alert). Treat as a research-grade risk signal, not an operational warning.",
            "Trained on NASA POWER MERRA-2 reanalysis, which is model-derived data, not "
            "direct station observation.",
            "risk_level expresses RELATIVE risk (validation-percentile bands), not an "
            "absolute probability of flooding. Calibrated probabilities for real flood "
            "days (mean 0.0022) and non-flood days (mean 0.0019) overlap heavily.",
        ],
    }
