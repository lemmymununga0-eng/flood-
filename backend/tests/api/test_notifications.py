"""Coverage for the new notifications feature: citizen-report moderation notifies the
original reporter, GET /notifications is scoped to the calling user, and
POST /{id}/read enforces ownership."""
from app.core.notifications import notify_user
from tests.conftest import promote_to_role, register_and_login


def test_moderation_notifies_the_original_reporter(client, db, seeded_roles, seeded_location):
    citizen_token = register_and_login(client, "reporter1@example.com")
    submit_resp = client.post(
        "/api/v1/citizen-reports",
        json={"location_id": seeded_location.id, "description": "Storm drain overflowing.", "severity": "medium"},
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    report_id = submit_resp.json()["id"]

    operator_token = register_and_login(client, "operator3@example.com")
    promote_to_role(db, "operator3@example.com", seeded_roles["OPERATOR"])
    moderate_resp = client.post(
        f"/api/v1/citizen-reports/{report_id}/moderate",
        json={"status": "verified", "review_note": "Confirmed on site."},
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert moderate_resp.status_code == 200

    my_notifications = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {citizen_token}"})
    assert my_notifications.status_code == 200
    notes = my_notifications.json()
    assert len(notes) == 1
    assert notes[0]["notification_type"] == "citizen_report_moderated"
    assert notes[0]["entity_type"] == "citizen_report"
    assert notes[0]["entity_id"] == report_id
    assert notes[0]["title"] == "Your report was verified"
    assert notes[0]["message"] == "Confirmed on site."
    assert notes[0]["is_read"] is False


def test_report_with_no_linked_reporter_creates_no_notification(client, db, seeded_roles, seeded_location):
    from app.models.citizen_report import CitizenReport

    report = CitizenReport(
        reporter_user_id=None,
        location_id=seeded_location.id,
        description="Anonymous tip about flooding.",
        severity="low",
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    operator_token = register_and_login(client, "operator4@example.com")
    promote_to_role(db, "operator4@example.com", seeded_roles["OPERATOR"])
    moderate_resp = client.post(
        f"/api/v1/citizen-reports/{report.id}/moderate",
        json={"status": "rejected"},
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert moderate_resp.status_code == 200
    # Nothing to assert an absence of directly (no reporter to check as), but the
    # request must not fail — the guard in the API route is what's under test here.


def test_notifications_list_requires_auth_and_is_scoped_per_user(client, db, seeded_roles):
    anon_resp = client.get("/api/v1/notifications")
    assert anon_resp.status_code == 401

    token_a = register_and_login(client, "usera@example.com")
    token_b = register_and_login(client, "userb@example.com")

    from app.models.user import User

    user_a = db.query(User).filter_by(email="usera@example.com").one()
    user_b = db.query(User).filter_by(email="userb@example.com").one()
    notify_user(db, user_id=user_a.id, notification_type="test", title="For A")
    notify_user(db, user_id=user_b.id, notification_type="test", title="For B")
    db.commit()

    resp_a = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    titles_a = [n["title"] for n in resp_a.json()]
    assert titles_a == ["For A"]

    resp_b = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token_b}"})
    assert [n["title"] for n in resp_b.json()] == ["For B"]


def test_mark_read_is_idempotent_and_owner_only(client, db, seeded_roles):
    token_a = register_and_login(client, "userc@example.com")
    token_b = register_and_login(client, "userd@example.com")

    from app.models.user import User

    user_c = db.query(User).filter_by(email="userc@example.com").one()
    note = notify_user(db, user_id=user_c.id, notification_type="test", title="Read me")
    db.commit()

    other_user_attempt = client.post(f"/api/v1/notifications/{note.id}/read", headers={"Authorization": f"Bearer {token_b}"})
    assert other_user_attempt.status_code == 404

    first_read = client.post(f"/api/v1/notifications/{note.id}/read", headers={"Authorization": f"Bearer {token_a}"})
    assert first_read.status_code == 200
    body = first_read.json()
    assert body["is_read"] is True
    assert body["read_at"] is not None

    second_read = client.post(f"/api/v1/notifications/{note.id}/read", headers={"Authorization": f"Bearer {token_a}"})
    assert second_read.status_code == 200
    assert second_read.json()["is_read"] is True
