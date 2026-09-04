import pytest


def test_create_watchlist(client, auth_headers):
    response = client.post(
        "/watchlists",
        json={"name": "My Portfolio"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Portfolio"
    assert data["stocks"] == []


def test_list_watchlists(client, auth_headers):
    client.post("/watchlists", json={"name": "List 1"}, headers=auth_headers)
    client.post("/watchlists", json={"name": "List 2"}, headers=auth_headers)

    response = client.get("/watchlists", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_update_watchlist(client, auth_headers):
    create_resp = client.post("/watchlists", json={"name": "Old Name"}, headers=auth_headers)
    wl_id = create_resp.json()["id"]

    response = client.put(
        f"/watchlists/{wl_id}",
        json={"name": "New Name"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_delete_watchlist(client, auth_headers):
    create_resp = client.post("/watchlists", json={"name": "To Delete"}, headers=auth_headers)
    wl_id = create_resp.json()["id"]

    response = client.delete(f"/watchlists/{wl_id}", headers=auth_headers)
    assert response.status_code == 204

    get_resp = client.get(f"/watchlists/{wl_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_add_stock(client, auth_headers):
    create_resp = client.post("/watchlists", json={"name": "Stocks"}, headers=auth_headers)
    wl_id = create_resp.json()["id"]

    response = client.post(
        f"/watchlists/{wl_id}/stocks",
        json={"ticker": "TCS"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    tickers = [s["ticker"] for s in data["stocks"]]
    assert "TCS" in tickers


def test_add_duplicate_stock(client, auth_headers):
    create_resp = client.post("/watchlists", json={"name": "Stocks"}, headers=auth_headers)
    wl_id = create_resp.json()["id"]

    client.post(f"/watchlists/{wl_id}/stocks", json={"ticker": "TCS"}, headers=auth_headers)
    response = client.post(f"/watchlists/{wl_id}/stocks", json={"ticker": "TCS"}, headers=auth_headers)
    assert response.status_code == 400


def test_add_invalid_stock(client, auth_headers):
    create_resp = client.post("/watchlists", json={"name": "Stocks"}, headers=auth_headers)
    wl_id = create_resp.json()["id"]

    response = client.post(
        f"/watchlists/{wl_id}/stocks",
        json={"ticker": "FAKEXXX"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_remove_stock(client, auth_headers):
    create_resp = client.post("/watchlists", json={"name": "Stocks"}, headers=auth_headers)
    wl_id = create_resp.json()["id"]

    client.post(f"/watchlists/{wl_id}/stocks", json={"ticker": "TCS"}, headers=auth_headers)
    response = client.delete(f"/watchlists/{wl_id}/stocks/TCS", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    tickers = [s["ticker"] for s in data["stocks"]]
    assert "TCS" not in tickers
