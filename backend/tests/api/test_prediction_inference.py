"""Tests for POST /api/v1/predictions/predict — real inference against the registered
model artifact. These exercise the real model (no mocked predictor): if the artifacts
are missing the endpoint must say so honestly rather than return a synthetic result."""
import pytest
from fastapi.testclient import TestClient

from app.ml.predictor import artifacts_available

pytestmark = pytest.mark.skipif(
    not artifacts_available(),
    reason="Model artifacts not present in MODEL_ARTIFACT_DIR — inference tests skipped "
           "rather than faked.",
)

WET = {
    "precipitation_mm": 48.2, "temperature_c": 23.4, "temperature_max_c": 27.1,
    "temperature_min_c": 20.2, "relative_humidity_pct": 91.5, "wind_speed_10m_ms": 2.4,
}
DRY = {
    "precipitation_mm": 0.0, "temperature_c": 29.5, "temperature_max_c": 36.0,
    "temperature_min_c": 21.0, "relative_humidity_pct": 28.0, "wind_speed_10m_ms": 4.5,
}


def test_predict_with_known_location_returns_full_schema(client: TestClient, seeded_location):
    resp = client.post("/api/v1/predictions/predict",
                       json={"location_id": seeded_location.id, **WET})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in ["location", "prediction_horizon_days", "risk_probability_raw",
                "risk_probability_calibrated", "risk_level", "model_version",
                "generated_at", "explanation", "caveats"]:
        assert key in body
    assert body["location"] == seeded_location.name
    assert body["prediction_horizon_days"] == 7
    assert body["risk_level"] in {"LOW", "MODERATE", "HIGH"}
    assert 0.0 <= body["risk_probability_calibrated"] <= 1.0
    assert len(body["explanation"]) == 6  # one per model feature
    assert body["caveats"], "response must always carry its limitations"


def test_wet_conditions_score_higher_than_dry(client: TestClient, seeded_location):
    wet = client.post("/api/v1/predictions/predict",
                      json={"location_id": seeded_location.id, **WET}).json()
    dry = client.post("/api/v1/predictions/predict",
                      json={"location_id": seeded_location.id, **DRY}).json()
    assert wet["risk_probability_raw"] > dry["risk_probability_raw"], (
        "humid/rainy conditions must not score below hot/dry conditions"
    )


def test_predict_accepts_location_name_without_id(client: TestClient):
    resp = client.post("/api/v1/predictions/predict",
                       json={"location_name": "Ad-hoc Site", **WET})
    assert resp.status_code == 200
    assert resp.json()["location"] == "Ad-hoc Site"


def test_predict_requires_a_location(client: TestClient):
    resp = client.post("/api/v1/predictions/predict", json=WET)
    assert resp.status_code == 422


def test_predict_unknown_location_id_is_404(client: TestClient):
    resp = client.post("/api/v1/predictions/predict", json={"location_id": 999999, **WET})
    assert resp.status_code == 404


def test_predict_rejects_out_of_range_humidity(client: TestClient, seeded_location):
    bad = {**WET, "relative_humidity_pct": 150.0}
    resp = client.post("/api/v1/predictions/predict",
                       json={"location_id": seeded_location.id, **bad})
    assert resp.status_code == 422


def test_predict_rejects_missing_weather_field(client: TestClient, seeded_location):
    partial = {k: v for k, v in WET.items() if k != "relative_humidity_pct"}
    resp = client.post("/api/v1/predictions/predict",
                       json={"location_id": seeded_location.id, **partial})
    assert resp.status_code == 422, "missing weather input must be rejected, never imputed"


def test_response_never_asserts_a_flood_will_occur(client: TestClient, seeded_location):
    body = client.post("/api/v1/predictions/predict",
                       json={"location_id": seeded_location.id, **WET}).json()
    serialized = str(body).lower()
    for forbidden in ["will flood", "will occur", "guaranteed", "certain to flood"]:
        assert forbidden not in serialized
