"""Registered SMS subscribers: staff-only management, and automatic delivery on alerts."""
import pytest

from tests.conftest import promote_to_role, register_and_login


@pytest.fixture
def staff(client, db, seeded_roles):
    token = register_and_login(client, "subs.admin@example.com")
    promote_to_role(db, "subs.admin@example.com", seeded_roles["ADMIN"])
    return {"Authorization": f"Bearer {token}"}


def _alert(location_id):
    return {
        "title": "Subscriber demo",
        "risk_level": "high",
        "location_id": location_id,
        "message": "Water rising.",
        "channels": "Dashboard,SMS",
    }


def test_management_requires_staff(client, seeded_roles):
    assert client.get("/api/v1/sms-subscribers").status_code == 401
    token = register_and_login(client, "subs.citizen@example.com")
    resp = client.post(
        "/api/v1/sms-subscribers",
        json={"phone": "+260971234567"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_add_list_duplicate_and_remove(client, staff):
    r = client.post(
        "/api/v1/sms-subscribers",
        json={"phone": "+260 97 123 4567", "name": "Demo phone"},
        headers=staff,
    )
    assert r.status_code == 201, r.text
    sub = r.json()
    assert sub["phone"] == "+260971234567" and sub["location_id"] is None

    dup = client.post("/api/v1/sms-subscribers", json={"phone": "+260971234567"}, headers=staff)
    assert dup.status_code == 409

    lr = client.get("/api/v1/sms-subscribers", headers=staff)
    assert lr.status_code == 200, lr.text
    listed = lr.json()
    assert [s["id"] for s in listed] == [sub["id"]]

    assert client.delete(f"/api/v1/sms-subscribers/{sub['id']}", headers=staff).status_code == 200
    assert client.get("/api/v1/sms-subscribers", headers=staff).json() == []
    assert client.delete(f"/api/v1/sms-subscribers/{sub['id']}", headers=staff).status_code == 404


@pytest.mark.parametrize("bad", ["0971234567", "abc", "+12", ""])
def test_rejects_non_international_numbers(client, staff, bad):
    r = client.post("/api/v1/sms-subscribers", json={"phone": bad}, headers=staff)
    assert r.status_code == 422


def test_unknown_location_rejected(client, staff):
    r = client.post(
        "/api/v1/sms-subscribers",
        json={"phone": "+260971234567", "location_id": 999999},
        headers=staff,
    )
    assert r.status_code == 400


def test_alert_texts_matching_subscribers_only(client, db, staff, seeded_location):
    from app.models.location import Location

    elsewhere = Location(
        name="Elsewhere", province="Copperbelt", latitude=-12.8, longitude=28.2,
        coordinate_confidence="test-fixture", evidence_note="fixture", evidence_source_url="",
    )
    db.add(elsewhere)
    db.commit()
    db.refresh(elsewhere)

    def add(phone, location_id=None):
        r = client.post(
            "/api/v1/sms-subscribers",
            json={"phone": phone, "location_id": location_id},
            headers=staff,
        )
        assert r.status_code == 201, r.text

    add("+260971111111")  # all areas -> texted
    add("+260972222222", seeded_location.id)  # this area -> texted
    add("+260973333333", elsewhere.id)  # a different area -> must NOT be texted

    resp = client.post("/api/v1/alerts", json=_alert(seeded_location.id), headers=staff)
    assert resp.status_code == 201, resp.text
    deliveries = resp.json()["sms_delivery"]
    assert sorted(d["to"] for d in deliveries) == ["+260***11", "+260***22"]
    assert all(d["status"] == "simulated" for d in deliveries)


def test_dashboard_only_alert_ignores_subscribers(client, staff, seeded_location):
    client.post("/api/v1/sms-subscribers", json={"phone": "+260971111111"}, headers=staff)
    payload = _alert(seeded_location.id) | {"channels": "Dashboard"}
    resp = client.post("/api/v1/alerts", json=payload, headers=staff)
    assert resp.json()["sms_delivery"] == []


def test_test_message_action(client, staff):
    sub = client.post("/api/v1/sms-subscribers", json={"phone": "+260971234567"}, headers=staff).json()
    r = client.post(f"/api/v1/sms-subscribers/{sub['id']}/test", headers=staff)
    assert r.status_code == 200
    assert r.json()[0]["status"] == "simulated"
