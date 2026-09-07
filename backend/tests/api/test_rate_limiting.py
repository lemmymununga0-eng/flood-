"""Verifies rate limiting is actually wired up on the login endpoint (every other
test disables it — see tests/conftest.py — so this is the one place it's checked)."""
from app.main import app


def test_login_is_rate_limited_after_repeated_attempts(client, seeded_roles):
    app.state.limiter.enabled = True
    try:
        responses = [
            client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
            for _ in range(15)
        ]
    finally:
        app.state.limiter.enabled = False
    statuses = [r.status_code for r in responses]
    assert 429 in statuses, "Expected the login endpoint to start rate-limiting after repeated attempts"
