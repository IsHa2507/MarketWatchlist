import pytest


def test_register_success(client):
    response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "securepass", "full_name": "Test User"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email(client):
    client.post(
        "/auth/register",
        json={"email": "dupe@example.com", "password": "pass123"},
    )
    response = client.post(
        "/auth/register",
        json={"email": "dupe@example.com", "password": "pass456"},
    )
    assert response.status_code == 400


def test_register_short_password(client):
    response = client.post(
        "/auth/register",
        json={"email": "short@example.com", "password": "abc"},
    )
    assert response.status_code == 400


def test_login_success(client, registered_user):
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_login_wrong_password(client, registered_user):
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_get_me(client, registered_user, auth_headers):
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


def test_get_me_unauthorized(client):
    response = client.get("/auth/me")
    assert response.status_code == 403
