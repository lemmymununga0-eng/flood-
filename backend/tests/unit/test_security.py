"""Unit tests for app/core/security.py — no DB, no network."""
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_not_plaintext():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$2b$")


def test_verify_password_accepts_correct_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


def test_verify_password_rejects_malformed_hash():
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_password_longer_than_72_bytes_does_not_crash():
    long_password = "x" * 200
    hashed = hash_password(long_password)
    assert verify_password(long_password, hashed) is True


def test_access_token_round_trips():
    token = create_access_token("42")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_refresh_token_has_refresh_type():
    token = create_refresh_token("42")
    payload = decode_token(token)
    assert payload["type"] == "refresh"


def test_decode_token_rejects_garbage():
    assert decode_token("not.a.jwt") is None


def test_decode_token_rejects_tampered_token():
    token = create_access_token("42")
    tampered = token[:-4] + "abcd"
    assert decode_token(tampered) is None
