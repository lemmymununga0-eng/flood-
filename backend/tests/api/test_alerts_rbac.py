"""API tests for /api/v1/alerts — real RBAC enforcement, not mocked."""
from tests.conftest import promote_to_role, register_and_login


def _alert_payload(location_id: int) -> dict:
    return {
        "title": "Test alert",
        "risk_level": "high",
        "location_id": location_id,
        "message": "Test message",
    }


def test_create_alert_requires_authentication(client, seeded_roles, seeded_location):
    resp = client.post("/api/v1/alerts", json=_alert_payload(seeded_location.id))
    assert resp.status_code == 401


def test_citizen_cannot_create_alert(client, seeded_roles, seeded_location):
    token = register_and_login(client, "citizen@example.com")
    resp = client.post(
        "/api/v1/alerts",
        json=_alert_payload(seeded_location.id),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "forbidden"


def test_admin_can_create_alert(client, db, seeded_roles, seeded_location):
    token = register_and_login(client, "admin.user@example.com")
    promote_to_role(db, "admin.user@example.com", seeded_roles["ADMIN"])
    resp = client.post(
        "/api/v1/alerts",
        json=_alert_payload(seeded_location.id),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "issued"


def test_analyst_can_create_alert(client, db, seeded_roles, seeded_location):
    token = register_and_login(client, "analyst.user@example.com")
    promote_to_role(db, "analyst.user@example.com", seeded_roles["ANALYST"])
    resp = client.post(
        "/api/v1/alerts",
        json=_alert_payload(seeded_location.id),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


def test_create_alert_rejects_unknown_location(client, db, seeded_roles):
    token = register_and_login(client, "admin2@example.com")
    promote_to_role(db, "admin2@example.com", seeded_roles["ADMIN"])
    resp = client.post(
        "/api/v1/alerts",
        json=_alert_payload(999999),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "unknown_location"


def test_list_alerts_is_public(client, seeded_roles):
    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    assert resp.json() == []
