from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings


def test_registration_login_and_password_privacy(client, account):
    headers = account("Owner@example.com", "  password-with-spaces  ")
    profile = client.get("/api/v1/auth/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["email"] == "owner@example.com"
    assert "password_hash" not in profile.json()
    assert (
        client.post(
            "/api/v1/auth/login",
            json={
                "email": "owner@example.com",
                "password": "password-with-spaces",
            },
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "OWNER@example.com",
                "name": "Other",
                "password": "another-password-123",
            },
        ).status_code
        == 409
    )


def test_invalid_authentication(client, account):
    account()
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad"}).status_code == 401
    for email in ("owner@example.com", "absent@example.com"):
        response = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"


def test_expired_token(client, account):
    headers = account()
    user = client.get("/api/v1/auth/me", headers=headers).json()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": user["id"],
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "iss": "cognitive-second-brain",
            "aud": "brain-api",
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": "Bearer " + token,
            },
        ).status_code
        == 401
    )


def test_validation(client):
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid",
                "name": "Name",
                "password": "short",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@example.com",
                "name": "  ",
                "password": "long-password-123",
            },
        ).status_code
        == 422
    )


def test_authentication_rate_limit(client):
    for _ in range(get_settings().auth_rate_limit):
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422
    response = client.post("/api/v1/auth/login", json={})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


def test_health_and_request_headers(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"
