"""The production model must be byte-identical and behave identically to the recorded baseline
(tests/pure/prediction_baseline.json, captured before any change in this work)."""
import hashlib
import json
import pathlib

import pytest

from app.ml.predictor import predict_risk

BASE = json.loads((pathlib.Path(__file__).parent / "prediction_baseline.json").read_text())
ART = pathlib.Path(__file__).resolve().parents[2] / "ml_artifacts" / BASE["model_version"]


def test_artifact_files_unchanged():
    now = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ART.iterdir())}
    assert now == BASE["artifact_sha256"]


@pytest.mark.parametrize("case", BASE["cases"])
def test_fixed_inputs_give_baseline_outputs(case):
    r = predict_risk(location_name="X", latitude=None, longitude=None,
                     observation_date="2026-10-14", **case["input"])
    assert r["risk_probability_raw"] == case["raw"]
    assert r["risk_probability_calibrated"] == case["calibrated"]
    assert r["risk_level"] == case["level"]
    assert r["would_alert_at_threshold"] == case["alert"]
    assert [r["target_window_start"], r["target_window_end"]] == case["window"]
    assert r["model_version"] == BASE["model_version"]


def test_existing_routes_still_registered():
    from app.main import app
    paths = {(m, r.path) for r in app.routes for m in getattr(r, "methods", [])}
    assert ("POST", "/api/v1/predictions/predict") in paths
    assert ("GET", "/api/v1/predictions") in paths


def test_dam_and_outlook_modules_do_not_use_the_model():
    # api/forecast.py is deliberately excluded: its refresh action CALLS predict_risk (read-only use).
    root = pathlib.Path(__file__).resolve().parents[2] / "app"
    for f in ("api/dams.py", "services/dam_assessment.py",
              "services/dam_validation.py", "services/forecast_outlook.py", "models/dam.py"):
        text = (root / f).read_text()
        imports = [l for l in text.splitlines() if l.startswith(("import ", "from "))]
        assert not any("app.ml" in l or "predict_risk" in l for l in imports), f
        assert "predict_risk(" not in text, f
