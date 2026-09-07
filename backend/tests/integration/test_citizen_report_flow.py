"""Integration test: the full citizen-report lifecycle end-to-end through real HTTP
calls against the real backend/DB — register -> submit -> moderate -> verify visible."""
from tests.conftest import promote_to_role, register_and_login


def test_full_citizen_report_lifecycle(client, db, seeded_roles, seeded_location):
    citizen_token = register_and_login(client, "reporter@example.com")

    submit_resp = client.post(
        "/api/v1/citizen-reports",
        json={
            "location_id": seeded_location.id,
            "description": "Water rising fast near the bridge, waist-deep in places.",
            "severity": "high",
        },
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert submit_resp.status_code == 201, submit_resp.text
    report = submit_resp.json()
    assert report["status"] == "pending"
    assert report["reviewed_by_user_id"] is None

    listed = client.get("/api/v1/citizen-reports")
    assert listed.status_code == 200
    assert any(r["id"] == report["id"] for r in listed.json())

    citizen_cannot_moderate = client.post(
        f"/api/v1/citizen-reports/{report['id']}/moderate",
        json={"status": "verified"},
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert citizen_cannot_moderate.status_code == 403

    operator_token = register_and_login(client, "operator@example.com")
    promote_to_role(db, "operator@example.com", seeded_roles["OPERATOR"])

    moderate_resp = client.post(
        f"/api/v1/citizen-reports/{report['id']}/moderate",
        json={"status": "verified", "review_note": "Cross-checked with a second report."},
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert moderate_resp.status_code == 200
    moderated = moderate_resp.json()
    assert moderated["status"] == "verified"
    assert moderated["review_note"] == "Cross-checked with a second report."
    assert moderated["reviewed_by_user_id"] is not None

    filtered = client.get("/api/v1/citizen-reports?status=verified")
    assert filtered.status_code == 200
    assert all(r["status"] == "verified" for r in filtered.json())
    assert any(r["id"] == report["id"] for r in filtered.json())


def test_moderate_nonexistent_report_returns_404(client, db, seeded_roles):
    token = register_and_login(client, "operator2@example.com")
    promote_to_role(db, "operator2@example.com", seeded_roles["OPERATOR"])
    resp = client.post(
        "/api/v1/citizen-reports/999999/moderate",
        json={"status": "verified"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
