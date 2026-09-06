"""
Tests for the new provider layer, caching, freshness, and partial failure handling.

Rules:
- NO live network calls. yfinance is mocked via unittest.mock.
- Tests must pass in CI with no internet access.
- Existing 26 tests must continue passing (verified in test_all run).
"""
import os
os.environ["TESTING"] = "1"

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Symbol map
# ═══════════════════════════════════════════════════════════════════════════════

class TestSymbolMap:
    def test_resolve_known_indian_ticker(self):
        from app.providers.symbol_map import resolve_yahoo_symbol
        assert resolve_yahoo_symbol("TCS") == "TCS.NS"
        assert resolve_yahoo_symbol("RELIANCE") == "RELIANCE.NS"
        assert resolve_yahoo_symbol("INFY") == "INFY.NS"
        assert resolve_yahoo_symbol("HDFCBANK") == "HDFCBANK.NS"
        assert resolve_yahoo_symbol("ICICIBANK") == "ICICIBANK.NS"

    def test_resolve_known_us_ticker(self):
        from app.providers.symbol_map import resolve_yahoo_symbol
        assert resolve_yahoo_symbol("AAPL") == "AAPL"
        assert resolve_yahoo_symbol("NVDA") == "NVDA"
        assert resolve_yahoo_symbol("TSLA") == "TSLA"
        assert resolve_yahoo_symbol("MSFT") == "MSFT"
        assert resolve_yahoo_symbol("GOOGL") == "GOOGL"

    def test_resolve_case_insensitive(self):
        from app.providers.symbol_map import resolve_yahoo_symbol
        assert resolve_yahoo_symbol("tcs") == "TCS.NS"
        assert resolve_yahoo_symbol("aapl") == "AAPL"

    def test_resolve_unknown_returns_none(self):
        from app.providers.symbol_map import resolve_yahoo_symbol
        assert resolve_yahoo_symbol("FAKEXXX") is None
        assert resolve_yahoo_symbol("") is None

    def test_canonical_ticker_roundtrip(self):
        from app.providers.symbol_map import canonical_ticker
        assert canonical_ticker("TCS.NS") == "TCS"
        assert canonical_ticker("AAPL") == "AAPL"
        assert canonical_ticker("RELIANCE.NS") == "RELIANCE"

    def test_is_supported(self):
        from app.providers.symbol_map import is_supported
        assert is_supported("TCS") is True
        assert is_supported("AAPL") is True
        assert is_supported("FAKEXXX") is False
        assert is_supported("tcs") is True      # case-insensitive

    def test_get_all_tickers_contains_expected(self):
        from app.providers.symbol_map import get_all_tickers
        tickers = get_all_tickers()
        for expected in ["TCS", "RELIANCE", "INFY", "AAPL", "NVDA", "TSLA", "MSFT"]:
            assert expected in tickers

    def test_get_company_meta_fields(self):
        from app.providers.symbol_map import get_company_meta
        meta = get_company_meta("TCS")
        assert meta is not None
        assert meta["currency"] == "INR"
        assert meta["yahoo_symbol"] == "TCS.NS"
        assert "name" in meta
        assert "sector" in meta
        assert "avg_volume" in meta

    def test_get_company_meta_unknown(self):
        from app.providers.symbol_map import get_company_meta
        assert get_company_meta("FAKEXXX") is None

    def test_fallback_avg_volume(self):
        from app.providers.symbol_map import get_fallback_avg_volume
        vol = get_fallback_avg_volume("TCS")
        assert vol > 0
        # Unknown ticker returns default
        unknown = get_fallback_avg_volume("FAKEXXX")
        assert unknown == 1_000_000


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Freshness calculation
# ═══════════════════════════════════════════════════════════════════════════════

class TestFreshness:
    def test_none_fetched_at_returns_error(self):
        from app.providers.base import compute_freshness
        result = compute_freshness(None)
        assert result["status"] == "ERROR"
        assert result["fetched_at"] is None
        assert result["age_seconds"] == -1

    def test_fresh_within_ttl(self):
        from app.providers.base import compute_freshness
        now = datetime.utcnow()
        result = compute_freshness(now, ttl_seconds=300, market_state="REGULAR")
        assert result["status"] == "FRESH"
        assert result["age_seconds"] >= 0
        assert result["age_seconds"] < 5     # just fetched

    def test_stale_beyond_ttl(self):
        from app.providers.base import compute_freshness
        old = datetime.utcnow() - timedelta(seconds=400)
        result = compute_freshness(old, ttl_seconds=300, market_state="REGULAR")
        assert result["status"] == "STALE"

    def test_closed_market_state(self):
        from app.providers.base import compute_freshness
        now = datetime.utcnow()
        result = compute_freshness(now, ttl_seconds=300, market_state="CLOSED")
        assert result["status"] == "CLOSED"
        assert "closed" in result["label"].lower()

    def test_post_market_state(self):
        from app.providers.base import compute_freshness
        now = datetime.utcnow()
        result = compute_freshness(now, ttl_seconds=300, market_state="POST")
        assert result["status"] == "CLOSED"

    def test_status_is_always_string(self):
        """Enum values must never leak into the response."""
        from app.providers.base import compute_freshness
        for market_state in ["REGULAR", "CLOSED", "PRE", "POST", None]:
            result = compute_freshness(datetime.utcnow(), market_state=market_state)
            assert isinstance(result["status"], str), (
                f"status should be str, got {type(result['status'])} for market_state={market_state}"
            )

    def test_fetched_at_iso_format(self):
        from app.providers.base import compute_freshness
        result = compute_freshness(datetime.utcnow())
        assert result["fetched_at"].endswith("Z")

    def test_ttl_respected(self):
        from app.providers.base import compute_freshness
        now = datetime.utcnow()
        f1 = compute_freshness(now, ttl_seconds=60)
        assert f1["ttl_seconds"] == 60
        f2 = compute_freshness(now, ttl_seconds=600)
        assert f2["ttl_seconds"] == 600


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DemoProvider
# ═══════════════════════════════════════════════════════════════════════════════

class TestDemoProvider:
    def setup_method(self):
        from app.providers.demo import DemoProvider
        self.provider = DemoProvider()

    def test_is_always_available(self):
        assert self.provider.is_available() is True

    def test_get_quote_known_ticker(self):
        quote = self.provider.get_quote("TCS")
        assert quote is not None
        assert quote["ticker"] == "TCS"
        assert isinstance(quote["price"], float)
        assert quote["price"] > 0
        assert quote["demo_mode"] is True
        assert quote["data_source"] == "Demo"
        assert quote["currency"] == "INR"

    def test_get_quote_us_ticker(self):
        quote = self.provider.get_quote("AAPL")
        assert quote is not None
        assert quote["currency"] == "USD"
        assert quote["demo_mode"] is True

    def test_get_quote_unknown_returns_none(self):
        assert self.provider.get_quote("FAKEXXX") is None

    def test_get_quote_case_insensitive(self):
        q1 = self.provider.get_quote("tcs")
        q2 = self.provider.get_quote("TCS")
        assert q1 is not None
        assert q2 is not None
        assert q1["price"] == q2["price"]

    def test_get_quote_freshness_is_fresh(self):
        quote = self.provider.get_quote("TCS")
        assert quote["freshness"]["status"] == "FRESH"

    def test_get_quote_has_all_required_fields(self):
        required = [
            "ticker", "company_name", "price", "price_change", "price_change_percent",
            "volume", "average_volume", "volatility", "sentiment_score", "sentiment_label",
            "data_source", "fetched_at", "freshness", "demo_mode",
        ]
        quote = self.provider.get_quote("NVDA")
        for field in required:
            assert field in quote, f"Missing field: {field}"

    def test_get_history_length(self):
        history = self.provider.get_history("TCS", 10)
        assert len(history) == 10

    def test_get_history_default_30_days(self):
        history = self.provider.get_history("TCS")
        assert len(history) == 30

    def test_get_history_first_point_is_checkpoint(self):
        history = self.provider.get_history("TCS", 7)
        assert history[0]["is_checkpoint"] is True
        assert all(not h["is_checkpoint"] for h in history[1:])

    def test_get_history_has_ohlcv(self):
        history = self.provider.get_history("AAPL", 5)
        for point in history:
            for field in ["date", "open", "high", "low", "close", "volume"]:
                assert field in point

    def test_get_history_unknown_ticker(self):
        assert self.provider.get_history("FAKEXXX", 10) == []

    def test_search_by_ticker_fragment(self):
        results = self.provider.search_stocks("TCS")
        tickers = [r["ticker"] for r in results]
        assert "TCS" in tickers

    def test_search_by_company_name(self):
        results = self.provider.search_stocks("infosys")
        tickers = [r["ticker"] for r in results]
        assert "INFY" in tickers

    def test_search_by_bank(self):
        results = self.provider.search_stocks("bank")
        tickers = [r["ticker"] for r in results]
        assert any(t in tickers for t in ["HDFCBANK", "ICICIBANK", "AXISBANK"])

    def test_search_no_results(self):
        results = self.provider.search_stocks("ZZZZFAKE")
        assert results == []

    def test_demo_scenarios_deterministic(self):
        """Same ticker always returns same price (seeded)."""
        q1 = self.provider.get_quote("NVDA")
        q2 = self.provider.get_quote("NVDA")
        assert q1["price"] == q2["price"]

    def test_supported_tickers_not_empty(self):
        tickers = self.provider.get_supported_tickers()
        assert len(tickers) >= 10


# ═══════════════════════════════════════════════════════════════════════════════
# 4. YahooFinanceProvider — all mocked, no network
# ═══════════════════════════════════════════════════════════════════════════════

def _make_mock_ticker(price=3800.0, prev_close=3842.0, volume=2_500_000,
                      avg_volume=1_200_000, market_state="REGULAR"):
    """Build a minimal yfinance Ticker mock."""
    import pandas as pd

    # Mock history DataFrame
    dates = pd.date_range(end=pd.Timestamp.now(), periods=5, freq='D')
    hist = pd.DataFrame({
        "Open":   [price * 0.99] * 5,
        "High":   [price * 1.01] * 5,
        "Low":    [price * 0.98] * 5,
        "Close":  [price - 10, price - 8, price - 5, price - 2, price],
        "Volume": [avg_volume] * 5,
    }, index=dates)

    mock_ticker = MagicMock()
    mock_ticker.history.return_value = hist
    mock_ticker.info = {
        "currentPrice": price,
        "previousClose": prev_close,
        "volume": volume,
        "averageVolume": avg_volume,
        "marketState": market_state,
        "longName": "Tata Consultancy Services",
        "sector": "Information Technology",
        "currency": "INR",
    }
    return mock_ticker


class TestYahooFinanceProvider:
    def setup_method(self):
        from app.providers.yahoo_finance import YahooFinanceProvider
        self.provider = YahooFinanceProvider()

    @patch("app.providers.yahoo_finance.yf")
    def test_get_quote_returns_real_price(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(price=3750.0, prev_close=3842.0)

        quote = self.provider.get_quote("TCS")

        assert quote is not None
        assert quote["ticker"] == "TCS"
        assert quote["price"] == 3750.0
        assert quote["demo_mode"] is False
        assert quote["data_source"] == "Yahoo Finance"

    @patch("app.providers.yahoo_finance.yf")
    def test_get_quote_uses_yahoo_symbol(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker()

        self.provider.get_quote("TCS")

        # Must pass the .NS symbol to yfinance, not "TCS"
        mock_yf.Ticker.assert_called_once_with("TCS.NS")

    @patch("app.providers.yahoo_finance.yf")
    def test_get_quote_us_ticker_no_suffix(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(price=189.5, prev_close=188.0)

        quote = self.provider.get_quote("AAPL")

        mock_yf.Ticker.assert_called_once_with("AAPL")
        assert quote["ticker"] == "AAPL"
        assert quote["currency"] == "USD"

    @patch("app.providers.yahoo_finance.yf")
    def test_get_quote_price_change_calculated(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(price=3700.0, prev_close=3842.0)

        quote = self.provider.get_quote("TCS")

        assert quote["price_change"] == pytest.approx(3700.0 - 3842.0, abs=0.01)
        expected_pct = (3700.0 - 3842.0) / 3842.0 * 100
        assert quote["price_change_percent"] == pytest.approx(expected_pct, abs=0.01)

    @patch("app.providers.yahoo_finance.yf")
    def test_get_quote_volume_fields(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(volume=2_500_000, avg_volume=1_200_000)

        quote = self.provider.get_quote("TCS")

        assert quote["volume"] == 2_500_000
        assert quote["average_volume"] == 1_200_000

    @patch("app.providers.yahoo_finance.yf")
    def test_get_quote_freshness_fresh(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(market_state="REGULAR")

        quote = self.provider.get_quote("TCS")

        assert quote["freshness"]["status"] == "FRESH"

    @patch("app.providers.yahoo_finance.yf")
    def test_get_quote_closed_market_state(self, mock_yf):
        mock_yf.Ticker.return_value = _make_mock_ticker(market_state="CLOSED")

        quote = self.provider.get_quote("TCS")

        assert quote["freshness"]["status"] == "CLOSED"

    @patch("app.providers.yahoo_finance.yf")
    def test_get_quote_returns_none_on_zero_price(self, mock_yf):
        """If provider returns price=0, return None rather than bad data."""
        mock = _make_mock_ticker(price=0.0)
        mock.info = {"currentPrice": 0, "regularMarketPrice": 0}
        mock.history.return_value = MagicMock()
        mock.history.return_value.__len__ = lambda s: 0
        mock_yf.Ticker.return_value = mock

        quote = self.provider.get_quote("TCS")
        assert quote is None

    @patch("app.providers.yahoo_finance.yf")
    def test_get_quote_returns_none_on_exception(self, mock_yf):
        """Provider exceptions must return None, not propagate."""
        mock_yf.Ticker.side_effect = Exception("Network error")

        quote = self.provider.get_quote("TCS")
        assert quote is None

    def test_get_quote_unknown_ticker_returns_none(self):
        quote = self.provider.get_quote("FAKEXXX")
        assert quote is None

    @patch("app.providers.yahoo_finance.yf")
    def test_get_history_returns_ohlcv(self, mock_yf):
        import pandas as pd
        dates = pd.date_range(end=pd.Timestamp.now(), periods=7, freq='D')
        hist = pd.DataFrame({
            "Open":   [100.0] * 7,
            "High":   [105.0] * 7,
            "Low":    [95.0]  * 7,
            "Close":  [101.0] * 7,
            "Volume": [1_000_000] * 7,
        }, index=dates)
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist
        mock_yf.Ticker.return_value = mock_ticker

        history = self.provider.get_history("TCS", 7)

        assert len(history) == 7
        assert history[0]["is_checkpoint"] is True
        for point in history:
            for field in ["date", "open", "high", "low", "close", "volume"]:
                assert field in point

    @patch("app.providers.yahoo_finance.yf")
    def test_get_history_returns_empty_on_exception(self, mock_yf):
        mock_yf.Ticker.side_effect = Exception("Timeout")

        history = self.provider.get_history("TCS", 30)
        assert history == []

    def test_get_history_unknown_ticker(self):
        assert self.provider.get_history("FAKEXXX", 10) == []

    def test_search_uses_local_registry(self):
        """Search must NOT call yfinance — uses local registry only."""
        results = self.provider.search_stocks("TCS")
        tickers = [r["ticker"] for r in results]
        assert "TCS" in tickers

    def test_normalize_ticker_indian(self):
        assert self.provider.normalize_ticker("TCS") == "TCS.NS"

    def test_normalize_ticker_us(self):
        assert self.provider.normalize_ticker("AAPL") == "AAPL"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MarketDataService — cache layer (in-memory DB)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketDataServiceCache:
    """Uses a real in-memory SQLite DB so we can test cache read/write."""

    def setup_method(self):
        import os
        os.environ["TESTING"] = "1"
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db.database import Base

        self.engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

    def teardown_method(self):
        self.db.close()

    def _make_service(self, provider_name="demo"):
        """Create a MarketDataService with a mocked provider name."""
        from app.services.market_data import MarketDataService
        svc = MarketDataService(self.db)
        # Override TTL and provider for testing
        svc._ttl = 300
        return svc

    def test_cache_miss_then_hit(self):
        """First call fetches from provider; second call returns from cache."""
        svc = self._make_service()

        # First call — cache miss, fetches from DemoProvider
        result1 = svc.get_stock("TCS")
        assert result1 is not None
        assert result1["ticker"] == "TCS"

        # Second call — should hit cache (data_source contains "Cache")
        result2 = svc.get_stock("TCS")
        assert result2 is not None
        assert "Cache" in result2["data_source"]

    def test_cache_miss_on_stale(self):
        """If the cached snapshot is older than TTL, fetch again."""
        from app.models.market import StockSnapshot

        # Insert an artificially old snapshot
        old_time = datetime.utcnow() - timedelta(seconds=400)
        snapshot = StockSnapshot(
            ticker="AAPL",
            price=180.0,
            price_change_percent=-0.5,
            volume=50_000_000,
            average_volume=55_000_000,
            volatility=0.01,
            sentiment_score=0.0,
            timestamp=old_time,
            fetched_at=old_time,
            data_source="Yahoo Finance",
        )
        self.db.add(snapshot)
        self.db.commit()

        svc = self._make_service()
        svc._ttl = 300   # TTL=5min; old_time is 400s old → cache miss

        result = svc.get_stock("AAPL")
        assert result is not None
        # Should have fetched fresh (from DemoProvider fallback in test mode)
        # Price from new fetch won't be 180.0 (that was the stale cache)
        # The key assertion is that data_source is NOT "Cache (Yahoo Finance)"
        assert not result["data_source"].startswith("Cache (Yahoo Finance)")

    def test_returns_none_for_unknown_ticker(self):
        svc = self._make_service()
        assert svc.get_stock("FAKEXXX") is None

    def test_get_volume_returns_multiplier(self):
        svc = self._make_service()
        vol = svc.get_volume("TCS")
        assert "multiplier" in vol
        assert vol["multiplier"] > 0

    def test_get_volume_unknown_ticker(self):
        svc = self._make_service()
        vol = svc.get_volume("FAKEXXX")
        assert vol["current_volume"] == 0.0

    def test_get_all_tickers(self):
        svc = self._make_service()
        tickers = svc.get_all_tickers()
        assert len(tickers) >= 10
        assert "TCS" in tickers

    def test_search_returns_results(self):
        svc = self._make_service()
        results = svc.search_stocks("TCS")
        assert len(results) > 0

    def test_demo_fallback_when_provider_returns_none(self):
        """If primary provider returns None, demo provider kicks in."""
        svc = self._make_service()

        # Replace primary provider with one that always returns None
        mock_provider = MagicMock()
        mock_provider.get_quote.return_value = None
        svc._provider = mock_provider

        result = svc.get_stock("TCS")
        assert result is not None
        assert "Demo" in result["data_source"]

    def test_demo_fallback_when_provider_raises(self):
        """If primary provider raises, demo provider is used."""
        svc = self._make_service()

        mock_provider = MagicMock()
        mock_provider.get_quote.side_effect = Exception("Network timeout")
        svc._provider = mock_provider

        result = svc.get_stock("RELIANCE")
        assert result is not None
        assert result["ticker"] == "RELIANCE"

    def test_snapshot_is_saved_after_fetch(self):
        """After a live fetch, snapshot must be persisted."""
        from app.models.market import StockSnapshot

        svc = self._make_service()
        svc.get_stock("INFY")   # triggers fetch + save

        row = self.db.query(StockSnapshot).filter(
            StockSnapshot.ticker == "INFY"
        ).first()
        assert row is not None
        assert row.price > 0

    def test_get_history_returns_list(self):
        svc = self._make_service()
        history = svc.get_history("TCS", 10)
        assert isinstance(history, list)
        assert len(history) == 10


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Partial dashboard failure
# ═══════════════════════════════════════════════════════════════════════════════

class TestPartialDashboardFailure:
    """
    Verifies that if one ticker fails during dashboard build,
    the rest still appear and the dashboard does not raise.
    """

    def setup_method(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db.database import Base

        self.engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

    def teardown_method(self):
        self.db.close()

    def _make_dashboard_service(self):
        from app.services.dashboard import DashboardService
        return DashboardService(self.db)

    def test_empty_dashboard_has_errors_field(self):
        svc = self._make_dashboard_service()
        empty = svc._empty_dashboard()
        assert "errors" in empty
        assert "partial_results" in empty
        assert empty["partial_results"] is False
        assert empty["errors"] == []
        assert "error_count" in empty["summary"]

    def test_single_ticker_failure_does_not_crash_dashboard(self, client, auth_headers):
        """
        Integration: add TCS and NVDA; patch change_detector so NVDA raises.
        Dashboard must still return TCS and put NVDA in errors.
        """
        # Create watchlist with two stocks
        wl = client.post("/watchlists", json={"name": "Test"}, headers=auth_headers).json()
        client.post(f"/watchlists/{wl['id']}/stocks", json={"ticker": "TCS"}, headers=auth_headers)
        client.post(f"/watchlists/{wl['id']}/stocks", json={"ticker": "NVDA"}, headers=auth_headers)

        # Patch change_detector.detect_changes so NVDA raises
        original_detect = None
        from app.services.change_detection import ChangeDetectionService

        original_detect = ChangeDetectionService.detect_changes

        def patched_detect(self_cd, user_id, ticker):
            if ticker == "NVDA":
                raise RuntimeError("Simulated provider failure for NVDA")
            return original_detect(self_cd, user_id, ticker)

        with patch.object(ChangeDetectionService, "detect_changes", patched_detect):
            response = client.get("/dashboard", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # NVDA should be in errors
        error_tickers = [e["ticker"] for e in data.get("errors", [])]
        assert "NVDA" in error_tickers

        # Dashboard should have returned partial_results=True
        assert data.get("partial_results") is True

        # TCS should still appear somewhere
        all_tickers = (
            [r["ticker"] for r in data["needs_attention"]]
            + [r["ticker"] for r in data["worth_watching"]]
            + [r["ticker"] for r in data["normal"]]
        )
        assert "TCS" in all_tickers

    def test_no_data_ticker_added_to_errors(self, client, auth_headers):
        """If change_detector returns empty dict, ticker goes to errors not results."""
        from app.services.change_detection import ChangeDetectionService

        wl = client.post("/watchlists", json={"name": "Test2"}, headers=auth_headers).json()
        client.post(f"/watchlists/{wl['id']}/stocks", json={"ticker": "TCS"}, headers=auth_headers)
        client.post(f"/watchlists/{wl['id']}/stocks", json={"ticker": "AAPL"}, headers=auth_headers)

        # Patch AAPL to return empty dict (no data)
        original_detect = ChangeDetectionService.detect_changes

        def patched_detect(self_cd, user_id, ticker):
            if ticker == "AAPL":
                return {}      # empty = no data
            return original_detect(self_cd, user_id, ticker)

        with patch.object(ChangeDetectionService, "detect_changes", patched_detect):
            response = client.get("/dashboard", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        error_tickers = [e["ticker"] for e in data.get("errors", [])]
        assert "AAPL" in error_tickers


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Provider interface compliance
# ═══════════════════════════════════════════════════════════════════════════════

class TestProviderInterface:
    """Both DemoProvider and YahooFinanceProvider must satisfy BaseMarketProvider."""

    def _check_quote_shape(self, quote: dict, ticker: str):
        required = [
            "ticker", "company_name", "price", "price_change_percent",
            "volume", "average_volume", "volatility", "sentiment_score",
            "sentiment_label", "data_source", "fetched_at", "freshness",
            "demo_mode",
        ]
        for f in required:
            assert f in quote, f"Provider quote missing field '{f}'"
        assert quote["ticker"] == ticker
        assert isinstance(quote["freshness"]["status"], str)
        assert isinstance(quote["demo_mode"], bool)

    def test_demo_provider_satisfies_interface(self):
        from app.providers.demo import DemoProvider
        p = DemoProvider()
        assert p.is_available() is True
        for ticker in ["TCS", "AAPL", "NVDA"]:
            quote = p.get_quote(ticker)
            self._check_quote_shape(quote, ticker)

    @patch("app.providers.yahoo_finance.yf")
    def test_yahoo_provider_satisfies_interface(self, mock_yf):
        from app.providers.yahoo_finance import YahooFinanceProvider
        mock_yf.Ticker.return_value = _make_mock_ticker()
        p = YahooFinanceProvider()
        quote = p.get_quote("TCS")
        self._check_quote_shape(quote, "TCS")

    def test_get_provider_factory_demo(self):
        from app.providers import get_provider
        from app.providers.demo import DemoProvider
        p = get_provider("demo")
        assert isinstance(p, DemoProvider)

    def test_get_provider_factory_yahoo(self):
        from app.providers import get_provider
        from app.providers.yahoo_finance import YahooFinanceProvider
        p = get_provider("yahoo")
        assert isinstance(p, YahooFinanceProvider)

    def test_get_provider_factory_unknown_falls_back_to_demo(self):
        from app.providers import get_provider
        from app.providers.demo import DemoProvider
        p = get_provider("unknown_provider")
        assert isinstance(p, DemoProvider)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Demo fallback correctness
# ═══════════════════════════════════════════════════════════════════════════════

class TestDemoFallback:
    """
    When MARKET_DATA_PROVIDER=demo, the system must behave exactly as before
    (backward compat for all existing tests).
    """

    def test_demo_tcs_scenario(self):
        """TCS demo scenario: -3.8% price change."""
        from app.providers.demo import DemoProvider
        p = DemoProvider()
        quote = p.get_quote("TCS")
        assert quote["price_change_percent"] == pytest.approx(-3.8, abs=0.01)

    def test_demo_nvda_scenario(self):
        """NVDA demo scenario: +6.2% price change."""
        from app.providers.demo import DemoProvider
        p = DemoProvider()
        quote = p.get_quote("NVDA")
        assert quote["price_change_percent"] == pytest.approx(6.2, abs=0.01)

    def test_demo_infy_scenario(self):
        """INFY demo scenario: +0.3% (normal/no significant change)."""
        from app.providers.demo import DemoProvider
        p = DemoProvider()
        quote = p.get_quote("INFY")
        assert abs(quote["price_change_percent"]) < 1.0

    def test_all_demo_tickers_return_quotes(self):
        from app.providers.demo import DemoProvider
        from app.providers.symbol_map import get_all_tickers
        p = DemoProvider()
        for ticker in get_all_tickers():
            quote = p.get_quote(ticker)
            assert quote is not None, f"Demo quote returned None for {ticker}"
            assert quote["price"] > 0, f"Demo price <= 0 for {ticker}"
