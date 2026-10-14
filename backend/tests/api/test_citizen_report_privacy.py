"""Public visibility rules for citizen reports (audit finding F-02)."""
from tests.conftest import promote_to_role, register_and_login


def _submit(client, token, location_id, text):
    r = client.post("/api/v1/citizen-reports", json={"location_id": location_id, "description": text, "severity": "high"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_visibility_by_audience(client, db, seeded_roles, seeded_location):
    alice = register_and_login(client, "alice@example.com")
    bob = register_and_login(client, "bob@example.com")
    staff = register_and_login(client, "staff@example.com")
    promote_to_role(db, "staff@example.com", seeded_roles["OPERATOR"])

    pending = _submit(client, alice, seeded_location.id, "Pending report from alice, unreviewed.")
    verified = _submit(client, alice, seeded_location.id, "Verified report from alice, checked.")
    client.post(f"/api/v1/citizen-reports/{verified}/moderate", json={"status": "verified"},
                headers={"Authorization": f"Bearer {staff}"})

    def ids(headers=None):
        return {r["id"]: r for r in client.get("/api/v1/citizen-reports", headers=headers or {}).json()}

    anon = ids()
    assert set(anon) == {verified}
    assert anon[verified]["reporter_user_id"] is None and anon[verified]["reviewed_by_user_id"] is None

    other = ids({"Authorization": f"Bearer {bob}"})
    assert set(other) == {verified} and other[verified]["reporter_user_id"] is None

    own = ids({"Authorization": f"Bearer {alice}"})
    assert set(own) == {pending, verified} and own[pending]["reporter_user_id"] is not None

    everything = ids({"Authorization": f"Bearer {staff}"})
    assert set(everything) == {pending, verified} and everything[pending]["reporter_user_id"] is not None


def test_invalid_token_is_treated_as_anonymous(client, seeded_location):
    r = client.get("/api/v1/citizen-reports", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 200 and r.json() == []
