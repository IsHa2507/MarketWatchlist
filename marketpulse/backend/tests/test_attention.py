import pytest
from app.services.attention_scoring import AttentionScoringService, classify_score


def test_classify_normal():
    assert classify_score(15) == "NORMAL"
    assert classify_score(0) == "NORMAL"
    assert classify_score(30) == "NORMAL"


def test_classify_worth_watching():
    assert classify_score(31) == "WORTH_WATCHING"
    assert classify_score(45) == "WORTH_WATCHING"
    assert classify_score(60) == "WORTH_WATCHING"


def test_classify_important():
    assert classify_score(61) == "IMPORTANT"
    assert classify_score(75) == "IMPORTANT"
    assert classify_score(80) == "IMPORTANT"


def test_classify_critical():
    assert classify_score(81) == "CRITICAL"
    assert classify_score(95) == "CRITICAL"
    assert classify_score(100) == "CRITICAL"


def test_tcs_scenario():
    """TCS: -3.8%, volume 2.1x, negative sentiment → IMPORTANT (~79)"""
    svc = AttentionScoringService()
    result = svc.calculate({
        "price_change_pct": -3.8,
        "volume_multiplier": 2.1,
        "current_sentiment": -0.42,
        "sentiment_change": "Neutral → Negative",
        "volatility_change_pct": 34.0,
    })
    assert result["classification"] in ("IMPORTANT", "CRITICAL")
    assert result["attention_score"] >= 61


def test_nvda_scenario():
    """NVDA: +6.2%, volume 2.8x, positive sentiment → IMPORTANT or CRITICAL (>78)"""
    svc = AttentionScoringService()
    result = svc.calculate({
        "price_change_pct": 6.2,
        "volume_multiplier": 2.8,
        "current_sentiment": 0.71,
        "sentiment_change": "Neutral → Positive",
        "volatility_change_pct": 50.0,
    })
    assert result["classification"] in ("CRITICAL", "IMPORTANT")
    assert result["attention_score"] >= 78


def test_infy_scenario():
    """INFY: +0.3%, volume normal, neutral → NORMAL (~15)"""
    svc = AttentionScoringService()
    result = svc.calculate({
        "price_change_pct": 0.3,
        "volume_multiplier": 1.0,
        "current_sentiment": 0.02,
        "sentiment_change": "Neutral",
        "volatility_change_pct": 2.0,
    })
    assert result["classification"] == "NORMAL"
    assert result["attention_score"] <= 30


def test_reliance_scenario():
    """RELIANCE: +2.4%, volume 1.8x, positive → WORTH_WATCHING (~62)"""
    svc = AttentionScoringService()
    result = svc.calculate({
        "price_change_pct": 2.4,
        "volume_multiplier": 1.8,
        "current_sentiment": 0.35,
        "sentiment_change": "Neutral → Positive",
        "volatility_change_pct": 20.0,
    })
    assert result["classification"] in ("WORTH_WATCHING", "IMPORTANT")
    assert result["attention_score"] >= 31


def test_key_reasons_populated(test_change_data=None):
    svc = AttentionScoringService()
    result = svc.calculate({
        "price_change_pct": -3.8,
        "volume_multiplier": 2.1,
        "current_sentiment": -0.42,
        "sentiment_change": "Neutral → Negative",
        "volatility_change_pct": 34.0,
    })
    assert len(result["key_reasons"]) > 0
    assert result["components"]["price"] > 0
    assert result["components"]["volume"] > 0


def test_checkpoint_order(client, auth_headers):
    """Verifies that dashboard reads old checkpoint before updating it."""
    # Create watchlist with TCS
    wl = client.post("/watchlists", json={"name": "Test"}, headers=auth_headers).json()
    client.post(f"/watchlists/{wl['id']}/stocks", json={"ticker": "TCS"}, headers=auth_headers)

    # First visit — is_first_visit should be True
    r1 = client.get("/dashboard", headers=auth_headers)
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["is_first_visit"] is True

    # Second visit — checkpoint should now exist
    r2 = client.get("/dashboard", headers=auth_headers)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["is_first_visit"] is False
