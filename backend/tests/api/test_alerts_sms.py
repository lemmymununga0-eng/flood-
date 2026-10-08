"""SMS delivery on alert creation. The default provider is simulated, so no test sends a
real message; the Twilio path is exercised against a faked HTTP layer."""
import pytest

from app.core import sms
from app.core.config import get_settings
from tests.conftest import promote_to_role, register_and_login


@pytest.fixture
def admin_headers(client, db, seeded_roles):
    token = register_and_login(client, "sms.admin@example.com")
    promote_to_role(db, "sms.admin@example.com", seeded_roles["ADMIN"])
    return {"Authorization": f"Bearer {token}"}


def _payload(location_id, recipients, channels="Dashboard,SMS"):
    return {
        "title": "Demo",
        "risk_level": "high",
        "location_id": location_id,
        "message": "River levels rising.",
        "channels": channels,
        "sms_recipients": recipients,
    }


def test_simulated_sms_reports_without_sending(client, admin_headers, seeded_location):
    resp = client.post(
        "/api/v1/alerts",
        json=_payload(seeded_location.id, ["+260971234567"]),
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["sms_provider"] == "simulated"
    assert body["sms_delivery"] == [
        {"to": "+260***67", "status": "simulated", "detail": "no message sent (SMS_PROVIDER=simulated)"}
    ]
    assert "+260971234567" not in resp.text  # full number is never echoed back


def test_dashboard_only_alert_sends_no_sms(client, admin_headers, seeded_location):
    resp = client.post(
        "/api/v1/alerts",
        json=_payload(seeded_location.id, ["+260971234567"], channels="Dashboard"),
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["sms_delivery"] == []


def test_invalid_duplicate_and_excess_numbers(client, admin_headers, seeded_location, monkeypatch):
    monkeypatch.setattr(get_settings(), "sms_max_recipients", 2)
    numbers = ["0971234567", "+260 97 123 4567", "+260971234567", "+260972222222", "+260973333333"]
    resp = client.post(
        "/api/v1/alerts", json=_payload(seeded_location.id, numbers), headers=admin_headers
    )
    assert resp.status_code == 201
    by_status = {}
    for d in resp.json()["sms_delivery"]:
        by_status.setdefault(d["status"], []).append(d)
    assert len(by_status["simulated"]) == 2  # duplicate collapsed, cap of 2 applied
    assert {d["detail"] for d in by_status["rejected"]} >= {
        "not an international (+...) number",
        "over the 2-recipient limit",
    }


def test_allowlist_blocks_other_numbers(client, admin_headers, seeded_location, monkeypatch):
    monkeypatch.setattr(get_settings(), "sms_allowed_numbers", "+260971234567")
    resp = client.post(
        "/api/v1/alerts",
        json=_payload(seeded_location.id, ["+260971234567", "+260979999999"]),
        headers=admin_headers,
    )
    statuses = sorted(d["status"] for d in resp.json()["sms_delivery"])
    assert statuses == ["rejected", "simulated"]


def test_provider_failure_does_not_lose_the_alert(client, admin_headers, seeded_location, monkeypatch):
    monkeypatch.setattr(get_settings(), "sms_provider", "twilio")
    monkeypatch.setattr(get_settings(), "twilio_account_sid", "ACtest")
    monkeypatch.setattr(get_settings(), "twilio_auth_token", "tok")
    monkeypatch.setattr(get_settings(), "twilio_from_number", "+15005550006")

    def boom(*a, **k):
        raise sms.httpx.ConnectError("down")

    monkeypatch.setattr(sms.httpx, "post", boom)
    resp = client.post(
        "/api/v1/alerts",
        json=_payload(seeded_location.id, ["+260971234567"]),
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["sms_delivery"][0]["status"] == "failed"
    assert any(a["title"] == "Demo" for a in client.get("/api/v1/alerts").json())


def test_twilio_success_path(client, admin_headers, seeded_location, monkeypatch):
    monkeypatch.setattr(get_settings(), "sms_provider", "twilio")
    monkeypatch.setattr(get_settings(), "twilio_account_sid", "ACtest")
    monkeypatch.setattr(get_settings(), "twilio_auth_token", "tok")
    monkeypatch.setattr(get_settings(), "twilio_from_number", "+15005550006")
    sent = {}

    class FakeResp:
        status_code = 201

    def fake_post(url, data=None, auth=None, timeout=None, **k):
        sent.update(url=url, data=data, auth=auth)
        return FakeResp()

    monkeypatch.setattr(sms.httpx, "post", fake_post)
    resp = client.post(
        "/api/v1/alerts",
        json=_payload(seeded_location.id, ["+260971234567"]),
        headers=admin_headers,
    )
    assert resp.json()["sms_delivery"][0]["status"] == "sent"
    assert sent["data"]["To"] == "+260971234567"
    assert sent["data"]["Body"].startswith("FloodShield DEMO [HIGH]")


def test_sms_body_is_capped():
    assert len(sms.build_body("high", "X", "a" * 1000)) <= sms.MAX_BODY
