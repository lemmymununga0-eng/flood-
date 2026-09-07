"""API tests for /api/v1/auth/* against a real Postgres test DB and a real FastAPI
TestClient — no mocked auth layer."""
from tests.conftest import register_and_login


def test_register_creates_real_citizen_user(client, seeded_roles):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "new.user@example.com", "password": "supersecret123", "full_name": "New User"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["role"] == "CITIZEN"
    assert body["user"]["email"] == "new.user@example.com"
    assert "access_token" in body and "refresh_token" in body


def test_register_rejects_duplicate_email(client, seeded_roles):
    client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "supersecret123"},
    )
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "supersecret123"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "email_taken"


def test_register_without_seeded_roles_fails_honestly(client):
    """If roles aren't seeded yet, registration must fail with a real 500 explaining
    why — never silently assign a fabricated role."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "orphan@example.com", "password": "supersecret123"},
    )
    assert resp.status_code == 500
    assert resp.json()["error"] == "roles_not_seeded"


def test_login_with_correct_password_succeeds(client, seeded_roles):
    client.post("/api/v1/auth/register", json={"email": "login@example.com", "password": "correctpassword"})
    resp = client.post("/api/v1/auth/login", json={"email": "login@example.com", "password": "correctpassword"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_with_wrong_password_fails(client, seeded_roles):
    client.post("/api/v1/auth/register", json={"email": "login2@example.com", "password": "correctpassword"})
    resp = client.post("/api/v1/auth/login", json={"email": "login2@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_credentials"


def test_login_with_unknown_email_fails(client, seeded_roles):
    resp = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
    assert resp.status_code == 401


def test_me_requires_a_token(client, seeded_roles):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"] == "not_authenticated"


def test_me_returns_the_authenticated_user(client, seeded_roles):
    token = register_and_login(client, "me@example.com")
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


def test_me_rejects_garbage_token(client, seeded_roles):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_token"
