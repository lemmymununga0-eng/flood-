"""Manual SMS: authorization, consent, validation, provider outcomes, duplicate prevention,
rate limits, callbacks and history. The provider HTTP layer is mocked (and blocked by an
autouse fixture in conftest.py) - no test can send a real SMS."""
from datetime import datetime

import pytest

from app.core import sms
from app.core.config import get_settings
from app.main import app
from app.models.sms_broadcast import SmsBroadcast
from app.models.sms_subscriber import SmsSubscriber
from tests.conftest import promote_to_role, register_and_login

API = "/api/v1"
PHONE = "+260971234567"


@pytest.fixture
def admin(client, db, seeded_roles):
    token = register_and_login(client, "sms.admin@example.com")
    promote_to_role(db, "sms.admin@example.com", seeded_roles["ADMIN"])
    return {"Authorization": f"Bearer {token}"}


def add_sub(client, admin, phone=PHONE, location_id=None, consent=True):
    return client.post(
        f"{API}/sms-subscribers",
        json={"phone": phone, "name": "Me", "location_id": location_id, "consent": consent,
              "consent_note": "verbal"},
        headers=admin,
    )


def compose(location, **over):
    return {"location_id": location.id, "risk_level": "high", "message": "River rising.", **over}


_n = iter(range(10_000))


def send_body(location, count, **over):
    base = compose(location, idempotency_key=f"key-{next(_n):06d}-abcd", confirm=True,
                   expected_recipient_count=count)
    return base | over


def probe(location, sid, **over):
    base = compose(location, subscriber_id=sid, idempotency_key=f"key-{next(_n):06d}-abcd",
                   confirm=True)
    return base | over


class FakeResp:
    def __init__(self, status_code=201, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def at_ok(numbers_to_ids):
    return {"SMSMessageData": {"Message": "Sent", "Recipients": [
        {"number": n, "status": "Success", "statusCode": 101, "messageId": mid, "cost": "ZMW 0.5000"}
        for n, mid in numbers_to_ids.items()
    ]}}


@pytest.fixture
def real_at(monkeypatch):
    """Africa's Talking sandbox config + a recording fake for the HTTP layer."""
    cfg = get_settings()
    monkeypatch.setattr(cfg, "sms_provider", "africastalking")
    monkeypatch.setattr(cfg, "africastalking_environment", "sandbox")
    monkeypatch.setattr(cfg, "africastalking_username", "sandbox")
    monkeypatch.setattr(cfg, "africastalking_api_key", "test-key")
    calls = []
    state = {"respond": None}

    def fake_post(url, data=None, headers=None, timeout=None, **k):
        calls.append({"url": url, "data": data, "headers": headers})
        if callable(state["respond"]):
            return state["respond"](data)
        numbers = data["to"].split(",")
        return FakeResp(201, at_ok({n: f"ATXid_{i}_{len(calls)}" for i, n in enumerate(numbers)}))

    monkeypatch.setattr(sms.httpx, "post", fake_post)
    return type("R", (), {"calls": calls, "state": state})


# --- authorization --------------------------------------------------------------------------


ENDPOINTS = [
    ("get", "/sms/status"), ("post", "/sms/preview"), ("post", "/sms/test"),
    ("post", "/sms/broadcasts"), ("get", "/sms/broadcasts"), ("get", "/sms/broadcasts/1"),
    ("get", "/sms-subscribers"), ("post", "/sms-subscribers"),
    ("post", "/sms-subscribers/1/opt-out"), ("delete", "/sms-subscribers/1"),
]


@pytest.mark.parametrize("method,path", ENDPOINTS)
def test_anonymous_is_rejected(client, method, path):
    assert getattr(client, method)(API + path).status_code == 401


@pytest.mark.parametrize("role", ["CITIZEN", "ANALYST", "OPERATOR"])
@pytest.mark.parametrize("method,path", ENDPOINTS)
def test_only_admin_may_use_sms(client, db, seeded_roles, role, method, path):
    email = f"{role.lower()}.sms@example.com"
    token = register_and_login(client, email)
    if role != "CITIZEN":
        promote_to_role(db, email, seeded_roles[role])
    r = getattr(client, method)(API + path, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


# --- consent & opt-out ----------------------------------------------------------------------


def test_registration_requires_explicit_consent(client, admin):
    assert add_sub(client, admin, consent=False).status_code == 422
    no_field = client.post(f"{API}/sms-subscribers", json={"phone": PHONE}, headers=admin)
    assert no_field.status_code == 422
    ok = add_sub(client, admin)
    assert ok.status_code == 201
    body = ok.json()
    assert body["consent_at"] and body["can_receive"] is True and body["consent_note"] == "verbal"


@pytest.mark.parametrize("bad", ["0971234567", "abc", "+12", ""])
def test_rejects_non_international_numbers(client, admin, bad):
    assert add_sub(client, admin, phone=bad).status_code == 422


def test_duplicate_number_rejected(client, admin):
    assert add_sub(client, admin).status_code == 201
    assert add_sub(client, admin, phone="+260 97 123 4567").status_code == 409


def test_subscriber_without_recorded_consent_is_never_a_recipient(client, db, admin, seeded_location):
    db.add(SmsSubscriber(phone="+260972222222", name="legacy", active=True, consent_at=None,
                         created_at=datetime(2026, 1, 1)))
    db.commit()
    p = client.post(f"{API}/sms/preview", json=compose(seeded_location), headers=admin).json()
    assert p["recipient_count"] == 0 and p["can_send"] is False


def test_opt_out_excludes_and_resubscribe_needs_consent(client, admin, seeded_location):
    sid = add_sub(client, admin).json()["id"]
    assert client.post(f"{API}/sms/preview", json=compose(seeded_location), headers=admin).json()["recipient_count"] == 1
    out = client.post(f"{API}/sms-subscribers/{sid}/opt-out", headers=admin).json()
    assert out["active"] is False and out["opted_out_at"] and out["can_receive"] is False
    assert client.post(f"{API}/sms/preview", json=compose(seeded_location), headers=admin).json()["recipient_count"] == 0
    assert add_sub(client, admin).status_code == 409  # cannot silently re-add
    assert client.post(f"{API}/sms-subscribers/{sid}/resubscribe", json={"consent": False}, headers=admin).status_code == 422
    back = client.post(f"{API}/sms-subscribers/{sid}/resubscribe", json={"consent": True}, headers=admin).json()
    assert back["can_receive"] is True and back["opted_out_at"] is None


def test_preview_matches_location_and_never_leaks_full_numbers(client, db, admin, seeded_location):
    from app.models.location import Location

    other = Location(name="Elsewhere", province="Copperbelt", latitude=-12.8, longitude=28.2,
                     coordinate_confidence="t", evidence_note="f", evidence_source_url="")
    db.add(other)
    db.commit()
    add_sub(client, admin, "+260971111111")
    add_sub(client, admin, "+260972222222", seeded_location.id)
    add_sub(client, admin, "+260973333333", other.id)
    r = client.post(f"{API}/sms/preview", json=compose(seeded_location), headers=admin)
    p = r.json()
    assert p["recipient_count"] == 2
    assert "+260971111111" not in r.text and "+260972222222" not in r.text
    assert p["body"].startswith("FloodShield DEMO [HIGH] Test Location: River rising.")


# --- validation -----------------------------------------------------------------------------


@pytest.mark.parametrize("over", [
    {"risk_level": "apocalyptic"}, {"message": ""}, {"message": "   "}, {"message": "x" * 201},
    {"idempotency_key": "short"}, {"idempotency_key": "has spaces in it!!"},
    {"expected_recipient_count": -1},
])
def test_send_validation(client, admin, seeded_location, over):
    r = client.post(f"{API}/sms/broadcasts", json=send_body(seeded_location, 0, **over), headers=admin)
    assert r.status_code == 422


def test_unknown_location_and_missing_confirmation(client, admin, seeded_location):
    bad = send_body(seeded_location, 0) | {"location_id": 999999}
    assert client.post(f"{API}/sms/broadcasts", json=bad, headers=admin).status_code == 400
    no_confirm = send_body(seeded_location, 0) | {"confirm": False}
    r = client.post(f"{API}/sms/broadcasts", json=no_confirm, headers=admin)
    assert r.status_code == 400 and r.json()["error"] == "confirmation_required"
    assert client.get(f"{API}/sms/broadcasts", headers=admin).json() == []


def test_test_send_refuses_unconsented_number(client, db, admin, seeded_location):
    s = SmsSubscriber(phone="+260972222222", active=True, consent_at=None, created_at=datetime(2026, 1, 1))
    db.add(s)
    db.commit()
    r = client.post(f"{API}/sms/test", json=probe(seeded_location, s.id), headers=admin)
    assert r.status_code == 400 and r.json()["error"] == "no_consent"


# --- simulated provider ---------------------------------------------------------------------


def test_simulated_send_is_recorded_as_simulated_not_sent(client, admin, seeded_location):
    sid = add_sub(client, admin).json()["id"]
    r = client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "simulated" and d["provider"] == "simulated"
    m = d["messages"][0]
    assert m["submission_status"] == "simulated" and m["delivery_status"] == "not_reported"
    assert m["provider_message_id"] is None and PHONE not in r.text
    assert " TEST " in d["body"]


# --- Africa's Talking: success, failure, unknown --------------------------------------------


def test_real_test_send_records_provider_response_but_not_delivery(client, admin, seeded_location, real_at):
    sid = add_sub(client, admin).json()["id"]
    r = client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "submitted" and d["environment"] == "sandbox"
    m = d["messages"][0]
    assert m["submission_status"] == "accepted"
    assert m["provider_message_id"].startswith("ATXid_") and m["cost"] == "ZMW 0.5000"
    assert m["delivery_status"] == "not_reported" and m["delivery_reported_at"] is None
    assert d["accepted_count"] == 1 and d["delivered_count"] == 0
    call = real_at.calls[0]
    assert "api.sandbox.africastalking.com" in call["url"]
    assert call["headers"]["apiKey"] == "test-key" and call["data"]["to"] == PHONE
    assert "test-key" not in r.text


def test_provider_rejection_is_not_success(client, admin, seeded_location, real_at):
    sid = add_sub(client, admin).json()["id"]
    real_at.state["respond"] = lambda data: FakeResp(201, {"SMSMessageData": {"Recipients": [
        {"number": PHONE, "status": "InvalidPhoneNumber", "statusCode": 403, "messageId": "None", "cost": "0"}]}})
    d = client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin).json()
    assert d["status"] == "failed" and d["accepted_count"] == 0
    assert d["messages"][0]["submission_status"] == "rejected"
    assert "InvalidPhoneNumber" in d["messages"][0]["submission_detail"]


def test_http_401_is_failure_and_network_error_is_unknown(client, admin, seeded_location, real_at, monkeypatch):
    sid = add_sub(client, admin).json()["id"]
    real_at.state["respond"] = lambda data: FakeResp(401)
    d = client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin).json()
    assert d["status"] == "failed" and d["messages"][0]["submission_status"] == "failed"

    def boom(*a, **k):
        raise sms.httpx.ConnectError("down")

    monkeypatch.setattr(sms.httpx, "post", boom)
    d2 = client.post(f"{API}/sms/test", json=probe(seeded_location, sid, message="Second text"), headers=admin).json()
    assert d2["status"] == "unknown"
    assert d2["messages"][0]["submission_status"] == "unknown"
    assert "may or may not" in d2["messages"][0]["submission_detail"]


def test_missing_credentials_report_exactly_what_is_missing(client, admin, seeded_location, monkeypatch):
    monkeypatch.setattr(get_settings(), "sms_provider", "africastalking")
    st = client.get(f"{API}/sms/status", headers=admin).json()
    assert st["configured"] is False
    assert "AFRICASTALKING_USERNAME" in st["missing"] and "AFRICASTALKING_API_KEY" in st["missing"]
    sid = add_sub(client, admin).json()["id"]
    r = client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin)
    assert r.status_code == 409 and r.json()["error"] == "send_blocked"
    assert client.get(f"{API}/sms/broadcasts", headers=admin).json() == []


def test_environment_username_mismatch_is_flagged(admin, client, monkeypatch):
    cfg = get_settings()
    monkeypatch.setattr(cfg, "sms_provider", "africastalking")
    monkeypatch.setattr(cfg, "africastalking_api_key", "k")
    monkeypatch.setattr(cfg, "africastalking_username", "myapp")  # sandbox env needs 'sandbox'
    assert any("sandbox" in m for m in client.get(f"{API}/sms/status", headers=admin).json()["missing"])
    monkeypatch.setattr(cfg, "africastalking_environment", "production")
    assert client.get(f"{API}/sms/status", headers=admin).json()["configured"] is True


# --- group broadcast gating, confirmation, duplicates ---------------------------------------


def test_group_broadcast_locked_until_enabled_and_real_test_accepted(client, admin, seeded_location, real_at, monkeypatch):
    sid = add_sub(client, admin).json()["id"]
    body = lambda: send_body(seeded_location, 1)  # noqa: E731
    r = client.post(f"{API}/sms/broadcasts", json=body(), headers=admin)
    assert r.status_code == 409 and "SMS_BROADCAST_ENABLED" in r.json()["message"]

    monkeypatch.setattr(get_settings(), "sms_broadcast_enabled", True)
    r = client.post(f"{API}/sms/broadcasts", json=body(), headers=admin)
    assert r.status_code == 409 and "test SMS" in r.json()["message"]
    assert real_at.calls == []

    assert client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin).status_code == 200
    r = client.post(f"{API}/sms/broadcasts", json=body(), headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "broadcast" and r.json()["status"] == "submitted"
    assert "TEST" not in r.json()["body"]


def test_failed_test_does_not_unlock_broadcasts(client, admin, seeded_location, real_at, monkeypatch):
    monkeypatch.setattr(get_settings(), "sms_broadcast_enabled", True)
    sid = add_sub(client, admin).json()["id"]
    real_at.state["respond"] = lambda data: FakeResp(500)
    client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin)
    real_at.state["respond"] = None
    r = client.post(f"{API}/sms/broadcasts", json=send_body(seeded_location, 1), headers=admin)
    assert r.status_code == 409


def test_recipient_count_must_match_what_admin_saw(client, admin, seeded_location):
    add_sub(client, admin)
    r = client.post(f"{API}/sms/broadcasts", json=send_body(seeded_location, 5), headers=admin)
    assert r.status_code == 409 and r.json()["error"] == "recipient_count_changed"


def test_recipient_cap(client, admin, seeded_location, monkeypatch):
    monkeypatch.setattr(get_settings(), "sms_max_recipients", 1)
    add_sub(client, admin, "+260971111111")
    add_sub(client, admin, "+260972222222")
    r = client.post(f"{API}/sms/broadcasts", json=send_body(seeded_location, 2), headers=admin)
    assert r.status_code == 400 and r.json()["error"] == "too_many_recipients"


def test_allowlist_excludes_other_numbers(client, admin, seeded_location, monkeypatch):
    monkeypatch.setattr(get_settings(), "sms_allowed_numbers", PHONE)
    add_sub(client, admin, PHONE)
    add_sub(client, admin, "+260979999999")
    p = client.post(f"{API}/sms/preview", json=compose(seeded_location), headers=admin).json()
    assert p["recipient_count"] == 1 and p["skipped_not_allowlisted"] == 1


def test_same_idempotency_key_does_not_send_twice(client, admin, seeded_location, real_at):
    sid = add_sub(client, admin).json()["id"]
    payload = probe(seeded_location, sid)
    first = client.post(f"{API}/sms/test", json=payload, headers=admin).json()
    again = client.post(f"{API}/sms/test", json=payload, headers=admin).json()
    assert len(real_at.calls) == 1
    assert again["id"] == first["id"] and again["replayed"] is True and first["replayed"] is False


def test_identical_message_to_same_recipients_is_blocked_within_window(client, admin, seeded_location, real_at):
    sid = add_sub(client, admin).json()["id"]
    assert client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin).status_code == 200
    r = client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin)  # new key, same text
    assert r.status_code == 409 and r.json()["error"] == "duplicate_send"
    assert len(real_at.calls) == 1
    other = client.post(f"{API}/sms/test", json=probe(seeded_location, sid, message="Different text"), headers=admin)
    assert other.status_code == 200


def test_definitely_failed_send_may_be_retried(client, admin, seeded_location, real_at):
    sid = add_sub(client, admin).json()["id"]
    real_at.state["respond"] = lambda data: FakeResp(401)
    assert client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin).json()["status"] == "failed"
    real_at.state["respond"] = None
    retry = client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin)
    assert retry.status_code == 200 and retry.json()["status"] == "submitted"


def test_unknown_outcome_blocks_blind_retry(client, admin, seeded_location, real_at):
    sid = add_sub(client, admin).json()["id"]
    real_at.state["respond"] = lambda data: FakeResp(503)
    assert client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin).json()["status"] == "unknown"
    r = client.post(f"{API}/sms/test", json=probe(seeded_location, sid), headers=admin)
    assert r.status_code == 409 and r.json()["error"] == "duplicate_send"


# --- no automatic sending -------------------------------------------------------------------


def test_creating_an_alert_never_sends_sms(client, db, admin, seeded_location, real_at):
    add_sub(client, admin)
    r = client.post(f"{API}/alerts", headers=admin, json={
        "title": "T", "risk_level": "high", "location_id": seeded_location.id,
        "message": "m", "channels": "Dashboard,SMS"})
    assert r.status_code == 201
    assert real_at.calls == []
    assert db.query(SmsBroadcast).count() == 0


# --- callbacks ------------------------------------------------------------------------------


def _sent_message(client, admin, location):
    sid = add_sub(client, admin).json()["id"]
    return client.post(f"{API}/sms/test", json=probe(location, sid), headers=admin).json()


def test_callbacks_disabled_without_secret(client):
    assert client.post(f"{API}/sms/delivery-report?token=x", data={"id": "a"}).status_code == 503
    assert client.post(f"{API}/sms/inbound?token=x", data={"from": PHONE, "text": "STOP"}).status_code == 503


def test_callbacks_reject_wrong_token(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "sms_webhook_secret", "s3cret")
    assert client.post(f"{API}/sms/delivery-report?token=nope", data={"id": "a"}).status_code == 403
    assert client.post(f"{API}/sms/delivery-report", data={"id": "a"}).status_code == 403


def test_delivery_report_is_the_only_thing_that_sets_delivery(client, admin, seeded_location, real_at, monkeypatch):
    monkeypatch.setattr(get_settings(), "sms_webhook_secret", "s3cret")
    d = _sent_message(client, admin, seeded_location)
    mid = d["messages"][0]["provider_message_id"]
    url = f"{API}/sms/delivery-report?token=s3cret"

    assert client.post(url, data={"id": mid, "status": "Success"}).status_code == 200
    got = client.get(f"{API}/sms/broadcasts/{d['id']}", headers=admin).json()
    assert got["messages"][0]["delivery_status"] == "delivered" and got["delivered_count"] == 1
    assert got["messages"][0]["delivery_reported_at"]

    client.post(url, data={"id": mid, "status": "Buffered"})  # late/out-of-order report
    got = client.get(f"{API}/sms/broadcasts/{d['id']}", headers=admin).json()
    assert got["messages"][0]["delivery_status"] == "delivered"

    assert client.post(url, data={"id": "unknown-id", "status": "Success"}).status_code == 200


def test_failed_delivery_report_records_reason(client, admin, seeded_location, real_at, monkeypatch):
    monkeypatch.setattr(get_settings(), "sms_webhook_secret", "s3cret")
    d = _sent_message(client, admin, seeded_location)
    mid = d["messages"][0]["provider_message_id"]
    client.post(f"{API}/sms/delivery-report?token=s3cret",
                data={"id": mid, "status": "Failed", "failureReason": "UserInBlacklist"})
    m = client.get(f"{API}/sms/broadcasts/{d['id']}", headers=admin).json()
    assert m["messages"][0]["delivery_status"] == "failed" and m["delivery_failed_count"] == 1
    assert m["messages"][0]["failure_reason"] == "UserInBlacklist"


def test_stop_reply_opts_out_and_footer_only_when_enabled(client, admin, seeded_location, monkeypatch):
    sid = add_sub(client, admin).json()["id"]
    body = lambda: client.post(f"{API}/sms/preview", json=compose(seeded_location), headers=admin).json()["body"]  # noqa: E731
    assert "STOP" not in body()  # not advertised while the callback is not configured
    monkeypatch.setattr(get_settings(), "sms_webhook_secret", "s3cret")
    assert body().endswith("Reply STOP to opt out.")
    assert client.post(f"{API}/sms/inbound?token=s3cret", data={"from": PHONE, "text": " stop "}).status_code == 200
    sub = [s for s in client.get(f"{API}/sms-subscribers", headers=admin).json() if s["id"] == sid][0]
    assert sub["active"] is False and sub["opted_out_at"]


# --- history, rate limit --------------------------------------------------------------------


def test_history_lists_attempts_newest_first(client, admin, seeded_location, real_at):
    sid = add_sub(client, admin).json()["id"]
    client.post(f"{API}/sms/test", json=probe(seeded_location, sid, message="First"), headers=admin)
    real_at.state["respond"] = lambda data: FakeResp(401)
    client.post(f"{API}/sms/test", json=probe(seeded_location, sid, message="Second"), headers=admin)
    rows = client.get(f"{API}/sms/broadcasts", headers=admin).json()
    assert [r["status"] for r in rows] == ["failed", "submitted"]
    assert rows[1]["accepted_count"] == 1 and rows[0]["accepted_count"] == 0
    assert PHONE not in str(rows)
    assert client.get(f"{API}/sms/broadcasts/9999", headers=admin).status_code == 404


def test_send_endpoints_are_rate_limited(client, admin, seeded_location):
    app.state.limiter.reset()
    app.state.limiter.enabled = True
    try:
        codes = [
            client.post(f"{API}/sms/broadcasts", json=send_body(seeded_location, 0) | {"confirm": False}, headers=admin).status_code
            for _ in range(5)
        ]
    finally:
        app.state.limiter.enabled = False
        app.state.limiter.reset()
    assert 429 in codes
