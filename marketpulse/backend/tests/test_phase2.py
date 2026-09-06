"""
Phase 2 tests: RSS news, VADER sentiment, RSI-14+SMA20 technical,
unavailable sentiment handling, caching, and end-to-end dashboard.

Rules:
- NO live network calls. feedparser and yfinance are always mocked.
- All DB interactions use an in-memory SQLite instance.
- Tests cover both happy path AND every failure/fallback path.
"""
import os
os.environ["TESTING"] = "1"

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base


# ── shared DB fixture ─────────────────────────────────────────────────────────

def _make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Technical indicators: RSI-14 and SMA-20
# ═══════════════════════════════════════════════════════════════════════════════

class TestRSI14:
    def _closes(self, values):
        return values

    # --- _compute_rsi14 ---

    def test_returns_none_when_fewer_than_15_prices(self):
        from app.services.attention_scoring import _compute_rsi14
        assert _compute_rsi14([100.0] * 14) is None
        assert _compute_rsi14([]) is None
        assert _compute_rsi14([100.0]) is None

    def test_returns_value_with_exactly_15_prices(self):
        from app.services.attention_scoring import _compute_rsi14
        closes = [100.0 + i for i in range(15)]   # steady uptrend
        rsi = _compute_rsi14(closes)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_all_gains_returns_100(self):
        """All positive days → RSI should be 100 (no losses)."""
        from app.services.attention_scoring import _compute_rsi14
        closes = [float(100 + i) for i in range(20)]   # strict uptrend
        rsi = _compute_rsi14(closes)
        assert rsi == 100.0

    def test_all_losses_returns_0(self):
        """All negative days → RSI should be 0 (no gains)."""
        from app.services.attention_scoring import _compute_rsi14
        closes = [float(200 - i) for i in range(20)]   # strict downtrend
        rsi = _compute_rsi14(closes)
        assert rsi == pytest.approx(0.0, abs=1.0)

    def test_neutral_market_near_50(self):
        """Alternating +1/-1 → RSI near 50."""
        from app.services.attention_scoring import _compute_rsi14
        closes = []
        price = 100.0
        for i in range(20):
            price += 1.0 if i % 2 == 0 else -1.0
            closes.append(price)
        rsi = _compute_rsi14(closes)
        assert rsi is not None
        assert 40 <= rsi <= 60

    def test_overbought_territory(self):
        """Strong uptrend → RSI > 70."""
        from app.services.attention_scoring import _compute_rsi14
        closes = [100.0 + i * 2 for i in range(20)]   # fast uptrend
        rsi = _compute_rsi14(closes)
        assert rsi is not None
        assert rsi > 70

    def test_oversold_territory(self):
        """Strong downtrend → RSI < 30."""
        from app.services.attention_scoring import _compute_rsi14
        closes = [200.0 - i * 2 for i in range(20)]
        rsi = _compute_rsi14(closes)
        assert rsi is not None
        assert rsi < 30

    def test_uses_last_15_prices_only(self):
        """With 20 prices, only the last 15 should matter."""
        from app.services.attention_scoring import _compute_rsi14
        # Pad front with arbitrary noise, end with steady uptrend
        closes = [50.0] * 5 + [float(100 + i) for i in range(15)]
        rsi_padded = _compute_rsi14(closes)
        rsi_only15 = _compute_rsi14([float(100 + i) for i in range(15)])
        assert rsi_padded == rsi_only15


class TestSMA20:
    def test_returns_none_when_fewer_than_20_prices(self):
        from app.services.attention_scoring import _compute_sma20
        assert _compute_sma20([100.0] * 19) is None
        assert _compute_sma20([]) is None

    def test_returns_mean_of_last_20(self):
        from app.services.attention_scoring import _compute_sma20
        closes = [100.0] * 20
        assert _compute_sma20(closes) == pytest.approx(100.0)

    def test_uses_last_20_not_all(self):
        from app.services.attention_scoring import _compute_sma20
        # First 10 irrelevant, last 20 = 200.0
        closes = [50.0] * 10 + [200.0] * 20
        assert _compute_sma20(closes) == pytest.approx(200.0)

    def test_sma_deviation_score(self):
        from app.services.attention_scoring import _score_sma_deviation
        # 10% above SMA → score = min(100, 10*5) = 50
        assert _score_sma_deviation(110.0, 100.0) == pytest.approx(50.0)
        # 5% above → 25
        assert _score_sma_deviation(105.0, 100.0) == pytest.approx(25.0)
        # 20% above → 100 (capped)
        assert _score_sma_deviation(120.0, 100.0) == pytest.approx(100.0)
        # Exactly at SMA → 0
        assert _score_sma_deviation(100.0, 100.0) == pytest.approx(0.0)

    def test_sma_deviation_score_none_sma(self):
        from app.services.attention_scoring import _score_sma_deviation
        assert _score_sma_deviation(100.0, None) == 0.0
        assert _score_sma_deviation(100.0, 0.0) == 0.0


class TestRSIScoring:
    def test_overbought_scores_high(self):
        from app.services.attention_scoring import _score_rsi
        assert _score_rsi(80.0) == 100.0
        assert _score_rsi(75.0) >= 75.0

    def test_oversold_scores_high(self):
        from app.services.attention_scoring import _score_rsi
        assert _score_rsi(20.0) == 100.0
        assert _score_rsi(25.0) >= 75.0

    def test_neutral_scores_low(self):
        from app.services.attention_scoring import _score_rsi
        score_50 = _score_rsi(50.0)
        assert score_50 <= 25.0   # neutral zone

    def test_none_returns_zero(self):
        from app.services.attention_scoring import _score_rsi
        assert _score_rsi(None) == 0.0

    def test_monotonic_above_60(self):
        """RSI 60→80 should produce non-decreasing scores (leaving neutral zone)."""
        from app.services.attention_scoring import _score_rsi
        scores = [_score_rsi(float(r)) for r in range(60, 82, 5)]
        for i in range(len(scores) - 1):
            assert scores[i] <= scores[i + 1], f"Not monotonic at RSI {60 + i*5}"

    def test_u_shaped_scoring(self):
        """RSI near 50 should score lower than RSI near 30 or 70."""
        from app.services.attention_scoring import _score_rsi
        score_50 = _score_rsi(50.0)
        score_70 = _score_rsi(70.0)
        score_30 = _score_rsi(30.0)
        assert score_50 < score_70
        assert score_50 < score_30


class TestTechnicalScoring:
    def test_real_method_used_when_closes_available(self):
        from app.services.attention_scoring import score_technical
        closes = [float(100 + i) for i in range(25)]
        result = score_technical(
            price_change_pct=2.0,
            volume_multiplier=1.5,
            closes=closes,
            current_price=closes[-1],
        )
        assert result["method"] == "RSI14_SMA20"
        assert result["rsi14"] is not None
        assert result["sma20"] is not None
        assert 0.0 <= result["score"] <= 100.0

    def test_fallback_when_no_closes(self):
        from app.services.attention_scoring import score_technical
        result = score_technical(
            price_change_pct=3.0,
            volume_multiplier=2.0,
            closes=None,
        )
        assert result["method"] == "price_volume_fallback"
        assert result["rsi14"] is None
        assert result["sma20"] is None

    def test_fallback_when_insufficient_closes(self):
        from app.services.attention_scoring import score_technical
        result = score_technical(
            price_change_pct=3.0,
            volume_multiplier=2.0,
            closes=[100.0] * 10,  # only 10, need 15
            current_price=100.0,
        )
        assert result["method"] == "price_volume_fallback"

    def test_fallback_formula_correctness(self):
        """Fallback = abs(pct)/10 × min(vol/2, 1) × 100."""
        from app.services.attention_scoring import _score_technical_fallback
        # 5% move, 2x volume: strength=0.5, vol_confirm=1.0 → 50
        assert _score_technical_fallback(5.0, 2.0) == pytest.approx(50.0)
        # 10% move, 3x volume: strength=1.0, vol_confirm=1.0 → 100
        assert _score_technical_fallback(10.0, 3.0) == pytest.approx(100.0)
        # 0% move → 0
        assert _score_technical_fallback(0.0, 2.0) == pytest.approx(0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Attention scoring: sentiment unavailable weight redistribution
# ═══════════════════════════════════════════════════════════════════════════════

class TestAttentionScoreWithUnavailableSentiment:
    def _svc(self):
        from app.services.attention_scoring import AttentionScoringService
        return AttentionScoringService()

    def test_sentiment_unavailable_redistributes_weights(self):
        """
        When sentiment_unavailable=True, effective weights must sum to 1.0
        and sentiment weight must be 0.
        """
        svc = self._svc()
        result = svc.calculate({
            "price_change_pct": 3.0,
            "volume_multiplier": 1.5,
            "current_sentiment": None,
            "sentiment_change": "Unavailable",
            "sentiment_unavailable": True,
            "volatility_change_pct": 15.0,
        })
        ew = result["effective_weights"]
        assert ew["sentiment"] == 0.0
        total = sum(ew.values())
        assert total == pytest.approx(1.0, abs=0.001)
        assert result["sentiment_used"] is False

    def test_sentiment_available_uses_standard_weights(self):
        """When sentiment is available, standard 35/20/20/15/10 weights apply."""
        svc = self._svc()
        result = svc.calculate({
            "price_change_pct": 3.0,
            "volume_multiplier": 1.5,
            "current_sentiment": 0.5,
            "sentiment_change": "Neutral → Positive",
            "sentiment_unavailable": False,
            "volatility_change_pct": 15.0,
        })
        ew = result["effective_weights"]
        assert ew["price"] == pytest.approx(0.35)
        assert ew["volume"] == pytest.approx(0.20)
        assert ew["sentiment"] == pytest.approx(0.20)
        assert ew["volatility"] == pytest.approx(0.15)
        assert ew["technical"] == pytest.approx(0.10)
        assert result["sentiment_used"] is True

    def test_unavailable_score_lower_than_available_with_same_signal(self):
        """
        A stock with positive sentiment should score higher than
        the same stock with unavailable sentiment.
        """
        svc = self._svc()
        data_base = {
            "price_change_pct": 4.0,
            "volume_multiplier": 2.0,
            "volatility_change_pct": 20.0,
        }
        result_with = svc.calculate({
            **data_base,
            "current_sentiment": 0.7,
            "sentiment_change": "Neutral → Positive",
            "sentiment_unavailable": False,
        })
        result_without = svc.calculate({
            **data_base,
            "current_sentiment": None,
            "sentiment_change": "Unavailable",
            "sentiment_unavailable": True,
        })
        # Positive sentiment should push score higher
        assert result_with["attention_score"] > result_without["attention_score"]

    def test_none_sentiment_treated_as_unavailable(self):
        """current_sentiment=None must trigger redistribution automatically."""
        svc = self._svc()
        result = svc.calculate({
            "price_change_pct": 2.0,
            "volume_multiplier": 1.2,
            "current_sentiment": None,   # None, no explicit flag
            "sentiment_change": "Neutral",
            "volatility_change_pct": 5.0,
        })
        assert result["effective_weights"]["sentiment"] == 0.0
        assert result["sentiment_used"] is False

    def test_key_reasons_mention_unavailable(self):
        """When sentiment unavailable, key_reasons should note it."""
        svc = self._svc()
        result = svc.calculate({
            "price_change_pct": 0.5,
            "volume_multiplier": 1.0,
            "current_sentiment": None,
            "sentiment_change": "Unavailable",
            "sentiment_unavailable": True,
            "volatility_change_pct": 5.0,
        })
        reasons_text = " ".join(result["key_reasons"]).lower()
        assert "unavailable" in reasons_text or "redistributed" in reasons_text

    def test_score_always_in_range(self):
        """Score must be in [0, 100] for all edge cases."""
        svc = self._svc()
        for pct in [-15.0, -5.0, 0.0, 5.0, 15.0]:
            for sent in [None, -1.0, 0.0, 1.0]:
                result = svc.calculate({
                    "price_change_pct": pct,
                    "volume_multiplier": 2.0,
                    "current_sentiment": sent,
                    "sentiment_unavailable": sent is None,
                    "sentiment_change": "Neutral",
                    "volatility_change_pct": 10.0,
                })
                assert 0.0 <= result["attention_score"] <= 100.0

    def test_rsi_overbought_adds_reason(self):
        """When closes show RSI≥70, key_reasons should mention overbought."""
        svc = self._svc()
        closes = [float(100 + i * 2) for i in range(25)]  # strong uptrend
        result = svc.calculate({
            "price_change_pct": 5.0,
            "volume_multiplier": 2.0,
            "current_sentiment": 0.3,
            "sentiment_unavailable": False,
            "sentiment_change": "Neutral",
            "volatility_change_pct": 20.0,
            "closes": closes,
            "current_price": closes[-1],
        })
        assert result["rsi14"] is not None
        if result["rsi14"] >= 70:
            reasons_text = " ".join(result["key_reasons"])
            assert "overbought" in reasons_text.lower() or "RSI" in reasons_text

    def test_technical_method_reported_in_result(self):
        svc = self._svc()
        # With closes → RSI14_SMA20
        closes = [float(100 + i) for i in range(25)]
        result = svc.calculate({
            "price_change_pct": 1.0,
            "volume_multiplier": 1.0,
            "current_sentiment": None,
            "sentiment_unavailable": True,
            "sentiment_change": "Unavailable",
            "volatility_change_pct": 5.0,
            "closes": closes,
            "current_price": closes[-1],
        })
        assert result["technical_method"] == "RSI14_SMA20"

        # Without closes → fallback
        result2 = svc.calculate({
            "price_change_pct": 1.0,
            "volume_multiplier": 1.0,
            "current_sentiment": None,
            "sentiment_unavailable": True,
            "sentiment_change": "Unavailable",
            "volatility_change_pct": 5.0,
        })
        assert result2["technical_method"] == "price_volume_fallback"

    def test_classification_thresholds_unchanged(self):
        """CRITICAL/IMPORTANT/WORTH_WATCHING/NORMAL thresholds must not have changed."""
        from app.services.attention_scoring import classify_score
        assert classify_score(0) == "NORMAL"
        assert classify_score(30) == "NORMAL"
        assert classify_score(31) == "WORTH_WATCHING"
        assert classify_score(60) == "WORTH_WATCHING"
        assert classify_score(61) == "IMPORTANT"
        assert classify_score(80) == "IMPORTANT"
        assert classify_score(81) == "CRITICAL"
        assert classify_score(100) == "CRITICAL"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Keyword sentiment model (zero-dependency fallback)
# ═══════════════════════════════════════════════════════════════════════════════

class TestKeywordSentimentModel:
    def _model(self):
        from app.services.sentiment_service import _KeywordModel
        return _KeywordModel()

    def test_always_available(self):
        assert self._model().is_available is True

    def test_positive_headlines(self):
        m = self._model()
        score = m.score_headlines(["Stock surges to record high on strong earnings beat"])
        assert score > 0

    def test_negative_headlines(self):
        m = self._model()
        score = m.score_headlines(["Company reports massive loss, stock crashes"])
        assert score < 0

    def test_neutral_headlines(self):
        m = self._model()
        score = m.score_headlines(["Company files quarterly report with SEC"])
        assert score == 0.0

    def test_empty_headlines(self):
        m = self._model()
        assert m.score_headlines([]) == 0.0

    def test_mixed_headlines_averaged(self):
        m = self._model()
        positive = "Earnings surge to record profit"
        negative = "Stock crashes on fraud scandal"
        # Should be roughly neutral
        score = m.score_headlines([positive, negative])
        assert -0.3 <= score <= 0.3

    def test_score_in_range(self):
        m = self._model()
        for headline in [
            "Best quarter ever, profits record high",
            "Terrible crash, stock falls, loss, decline, weak",
            "Regular quarterly update filed with regulators",
        ]:
            score = m.score_headlines([headline])
            assert -1.0 <= score <= 1.0

    def test_method_type(self):
        assert self._model().method_type == "keyword_baseline"

    def test_name(self):
        assert self._model().name == "Keyword"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. VADER sentiment model
# ═══════════════════════════════════════════════════════════════════════════════

class TestVADERModel:
    def _model(self):
        from app.services.sentiment_service import _VADERModel
        return _VADERModel()

    def test_is_available(self):
        """vaderSentiment must be installed."""
        assert self._model().is_available is True

    def test_positive_financial_headline(self):
        m = self._model()
        score = m.score_headlines(["Stocks surge on strong quarterly earnings beat"])
        assert score > 0

    def test_negative_financial_headline(self):
        m = self._model()
        score = m.score_headlines(["Markets crash on recession fears, massive losses"])
        assert score < 0

    def test_compound_in_range(self):
        m = self._model()
        for headline in [
            "Company announces major acquisition",
            "Fraud probe launched against executive",
            "Quarterly results in line with estimates",
        ]:
            score = m.score_headlines([headline])
            assert -1.0 <= score <= 1.0, f"Score out of range for: {headline}"

    def test_empty_returns_zero(self):
        m = self._model()
        assert m.score_headlines([]) == 0.0
        assert m.score_headlines([""]) == 0.0

    def test_multiple_headlines_averaged(self):
        m = self._model()
        h1 = "Record profit beats all estimates"
        h2 = "Massive loss, disappointing quarter"
        single1 = m.score_headlines([h1])
        single2 = m.score_headlines([h2])
        combined = m.score_headlines([h1, h2])
        assert combined == pytest.approx((single1 + single2) / 2, abs=0.001)

    def test_method_type_label(self):
        """MUST be labelled as lexicon_rule_based, NOT machine learning."""
        m = self._model()
        assert m.method_type == "lexicon_rule_based"

    def test_name(self):
        assert self._model().name == "VADER"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SentimentService result shapes
# ═══════════════════════════════════════════════════════════════════════════════

class TestSentimentServiceResultShape:
    def _make_service(self, headlines):
        """Create SentimentService with a mock NewsService that returns given headlines."""
        _, db = _make_db()
        from app.services.sentiment_service import SentimentService
        svc = SentimentService(db)
        mock_news = MagicMock()
        mock_news.get_headlines.return_value = headlines
        mock_news.update_cache_sentiment.return_value = None
        svc._news_svc = mock_news
        return svc

    def test_unavailable_result_shape(self):
        from app.services.sentiment_service import _unavailable_result
        result = _unavailable_result()
        assert result["score"] is None
        assert result["unavailable"] is True
        assert result["label"] == "Unavailable"
        assert result["source"] == "Unavailable"
        assert result["article_count"] == 0
        assert "timestamp" in result

    def test_available_result_shape(self):
        from app.services.sentiment_service import _make_result
        result = _make_result(
            score=0.45, article_count=5,
            source="VADER", method="lexicon_rule_based", confidence=0.7
        )
        assert result["score"] == pytest.approx(0.45)
        assert result["unavailable"] is False
        assert result["label"] == "Positive"
        assert result["article_count"] == 5
        assert result["source"] == "VADER"

    def test_label_thresholds(self):
        from app.services.sentiment_service import _make_result
        assert _make_result(0.2, 1, "VADER", "lr", 0.5)["label"] == "Positive"
        assert _make_result(-0.2, 1, "VADER", "lr", 0.5)["label"] == "Negative"
        assert _make_result(0.05, 1, "VADER", "lr", 0.5)["label"] == "Neutral"
        assert _make_result(-0.05, 1, "VADER", "lr", 0.5)["label"] == "Neutral"

    def test_no_headlines_returns_unavailable(self):
        svc = self._make_service(headlines=[])
        result = svc.get_sentiment("TCS")
        assert result["unavailable"] is True
        assert result["score"] is None

    def test_headlines_present_returns_real_score(self):
        headlines = [
            {"title": "TCS earnings surge on strong demand", "url": "", "published": ""},
            {"title": "Record profits beat analyst estimates", "url": "", "published": ""},
        ]
        svc = self._make_service(headlines=headlines)
        result = svc.get_sentiment("TCS")
        assert result["unavailable"] is False
        assert result["score"] is not None
        assert -1.0 <= result["score"] <= 1.0
        assert result["article_count"] == 2

    def test_sentiment_service_never_raises(self):
        """get_sentiment must always return a dict, never raise."""
        _, db = _make_db()
        from app.services.sentiment_service import SentimentService
        svc = SentimentService(db)
        # Make news service raise
        mock_news = MagicMock()
        mock_news.get_headlines.side_effect = Exception("Network error")
        svc._news_svc = mock_news

        result = svc.get_sentiment("TCS")
        assert isinstance(result, dict)
        assert result["unavailable"] is True

    def test_vader_source_correctly_labelled(self):
        headlines = [{"title": "Strong earnings beat expectations", "url": "", "published": ""}]
        svc = self._make_service(headlines=headlines)
        result = svc.get_sentiment("TCS")
        if not result["unavailable"]:
            assert result["source"] == "VADER"
            assert result["method"] == "lexicon_rule_based"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. NewsService — RSS fetch (all network calls mocked)
# ═══════════════════════════════════════════════════════════════════════════════

def _make_feedparser_entry(title: str, url: str = "https://example.com",
                            published: str = "Thu, 17 Apr 2025 10:00:00 GMT") -> MagicMock:
    entry = MagicMock()
    entry.get.side_effect = lambda key, default="": {
        "title": title,
        "link": url,
        "published": published,
        "published_parsed": None,
    }.get(key, default)
    return entry


class TestNewsServiceFetching:
    def _svc(self, db=None):
        if db is None:
            _, db = _make_db()
        from app.services.news_service import NewsService
        return NewsService(db), db

    @patch("app.services.news_service.NewsService._fetch_rss")
    def test_returns_headlines_from_yahoo_rss(self, mock_fetch):
        mock_fetch.return_value = [
            {"title": "TCS reports strong Q4 results", "url": "https://...", "published": "", "source": "Yahoo Finance RSS"},
            {"title": "TCS wins new contract worth $500M", "url": "https://...", "published": "", "source": "Yahoo Finance RSS"},
        ]
        svc, _ = self._svc()
        headlines = svc._fetch_headlines("TCS")
        assert len(headlines) == 2
        assert headlines[0]["title"] == "TCS reports strong Q4 results"

    @patch("app.services.news_service.NewsService._fetch_rss")
    def test_falls_back_to_google_news_when_yahoo_empty(self, mock_fetch):
        def side_effect(url, source):
            if "yahoo" in url:
                return []
            return [{"title": "Google news headline", "url": "", "published": "", "source": "Google News"}]
        mock_fetch.side_effect = side_effect

        svc, _ = self._svc()
        headlines = svc._fetch_headlines("AAPL")
        assert len(headlines) == 1
        assert headlines[0]["title"] == "Google news headline"

    @patch("app.services.news_service.NewsService._fetch_rss")
    def test_returns_empty_when_all_sources_fail(self, mock_fetch):
        mock_fetch.return_value = []
        svc, _ = self._svc()
        headlines = svc._fetch_headlines("TCS")
        assert headlines == []

    @patch("app.services.news_service.NewsService._fetch_rss")
    def test_exception_in_source_does_not_crash(self, mock_fetch):
        mock_fetch.side_effect = Exception("Network error")
        svc, _ = self._svc()
        headlines = svc._fetch_headlines("TCS")
        assert headlines == []  # graceful

    def test_get_headlines_returns_empty_when_news_disabled(self):
        svc, _ = self._svc()
        svc._enabled = False
        headlines = svc.get_headlines("TCS")
        assert headlines == []

    def test_unknown_ticker_returns_empty(self):
        svc, _ = self._svc()
        headlines = svc._fetch_headlines("FAKEXXX")
        assert headlines == []

    @patch("app.services.news_service.NewsService._fetch_rss")
    def test_cache_hit_skips_network(self, mock_fetch):
        """If cache is fresh, _fetch_rss must not be called."""
        from app.models.market import SentimentCache
        _, db = _make_db()
        from app.services.news_service import NewsService
        svc = NewsService(db)

        cached_headlines = [{"title": "Cached headline", "url": "", "published": "", "source": "Yahoo Finance RSS"}]
        row = SentimentCache(
            ticker="TCS",
            score=None, label="Unavailable", confidence=0.0, article_count=1,
            source="Unavailable",
            headlines_json=json.dumps(cached_headlines),
            unavailable=False,
            fetched_at=datetime.utcnow(),
        )
        db.add(row)
        db.commit()

        result = svc.get_headlines("TCS")
        mock_fetch.assert_not_called()
        assert result == cached_headlines

    @patch("app.services.news_service.NewsService._fetch_rss")
    def test_stale_cache_triggers_refetch(self, mock_fetch):
        """If cache is expired, _fetch_rss must be called."""
        from app.models.market import SentimentCache
        _, db = _make_db()
        from app.services.news_service import NewsService
        svc = NewsService(db)
        svc._ttl = 60  # 1 minute TTL

        old_time = datetime.utcnow() - timedelta(seconds=120)  # expired
        row = SentimentCache(
            ticker="AAPL",
            score=None, label="Unavailable", confidence=0.0, article_count=1,
            source="Unavailable",
            headlines_json=json.dumps([{"title": "Old", "url": "", "published": "", "source": "test"}]),
            unavailable=False,
            fetched_at=old_time,
        )
        db.add(row)
        db.commit()

        mock_fetch.return_value = [{"title": "Fresh headline", "url": "", "published": "", "source": "Yahoo Finance RSS"}]
        result = svc.get_headlines("AAPL")
        mock_fetch.assert_called()
        assert result[0]["title"] == "Fresh headline"

    @patch("app.services.news_service.NewsService._fetch_rss")
    def test_db_write_failure_does_not_crash(self, mock_fetch):
        """If DB write fails, get_headlines should still return results."""
        mock_fetch.return_value = [{"title": "Headline", "url": "", "published": "", "source": "test"}]
        svc, _ = self._svc()
        svc.db = MagicMock()
        svc.db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        svc.db.add.side_effect = Exception("DB error")
        svc.db.commit.side_effect = Exception("DB error")
        svc.db.rollback = MagicMock()

        result = svc._fetch_headlines("TCS")
        assert len(result) >= 0   # didn't crash


class TestParseFeedEntries:
    def test_basic_parsing(self):
        from app.services.news_service import _parse_feed_entries
        entries = [
            MagicMock(**{"get.side_effect": lambda k, d="": {"title": "Test headline", "link": "https://x.com", "published": "", "published_parsed": None}.get(k, d)}),
        ]
        result = _parse_feed_entries(entries, "Test Source", 10)
        assert len(result) == 1
        assert result[0]["title"] == "Test headline"
        assert result[0]["source"] == "Test Source"

    def test_empty_title_skipped(self):
        from app.services.news_service import _parse_feed_entries
        entry = MagicMock()
        entry.get.side_effect = lambda k, d="": {"title": "", "link": ""}.get(k, d)
        result = _parse_feed_entries([entry], "Test", 10)
        assert result == []

    def test_max_articles_respected(self):
        from app.services.news_service import _parse_feed_entries
        entries = []
        for i in range(15):
            e = MagicMock()
            e.get.side_effect = lambda k, d="", i=i: {"title": f"Headline {i}", "link": "", "published": "", "published_parsed": None}.get(k, d)
            entries.append(e)
        result = _parse_feed_entries(entries, "Test", 5)
        assert len(result) == 5


# ═══════════════════════════════════════════════════════════════════════════════
# 7. MarketDataService — sentiment injection
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketDataSentimentInjection:
    def _make_service(self):
        _, db = _make_db()
        from app.services.market_data import MarketDataService
        svc = MarketDataService(db)
        svc._ttl = 300
        return svc, db

    def test_demo_mode_skips_sentiment_injection(self):
        """Demo data has preset sentiment scores; _inject_sentiment must not be called."""
        svc, _ = self._make_service()
        injected = []

        original_inject = svc._inject_sentiment
        def track_inject(ticker, data):
            injected.append(ticker)
            return original_inject(ticker, data)
        svc._inject_sentiment = track_inject

        result = svc.get_stock("TCS")
        assert result is not None
        # Demo mode — injection should NOT have been called
        assert "TCS" not in injected

    def test_inject_sentiment_merges_fields(self):
        """_inject_sentiment must add sentiment fields to the data dict."""
        svc, _ = self._make_service()
        mock_svc = MagicMock()
        mock_svc.get_sentiment.return_value = {
            "score": 0.42,
            "label": "Positive",
            "confidence": 0.8,
            "article_count": 5,
            "source": "VADER",
            "method": "lexicon_rule_based",
            "unavailable": False,
            "timestamp": "2025-01-01T10:00:00",
        }
        svc._sentiment_svc = mock_svc

        data = {"ticker": "TCS", "price": 100.0, "demo_mode": False}
        result = svc._inject_sentiment("TCS", data)

        assert result["sentiment_score"] == 0.42
        assert result["sentiment_label"] == "Positive"
        assert result["sentiment_unavailable"] is False
        assert result["sentiment_source"] == "VADER"
        assert result["sentiment_article_count"] == 5

    def test_inject_sentiment_marks_unavailable_on_failure(self):
        """If SentimentService raises, inject must mark sentiment as unavailable."""
        svc, _ = self._make_service()
        mock_svc = MagicMock()
        mock_svc.get_sentiment.side_effect = Exception("Service down")
        svc._sentiment_svc = mock_svc

        data = {"ticker": "TCS", "price": 100.0, "demo_mode": False}
        result = svc._inject_sentiment("TCS", data)

        assert result["sentiment_score"] is None
        assert result["sentiment_unavailable"] is True
        assert result["sentiment_source"] == "Unavailable"

    def test_snapshot_saves_sentiment_source(self):
        """Saved snapshot must include sentiment_source and article_count."""
        from app.models.market import StockSnapshot
        svc, db = self._make_service()
        data = {
            "ticker": "AAPL", "price": 180.0, "price_change_percent": 1.0,
            "volume": 50_000_000, "average_volume": 55_000_000,
            "volatility": 0.015, "sentiment_score": 0.3,
            "data_source": "Yahoo Finance", "data_timestamp": datetime.utcnow(),
            "fetched_at": datetime.utcnow(), "freshness": {"status": "FRESH"},
            "sentiment_source": "VADER", "sentiment_timestamp": "2025-01-01T10:00:00",
            "sentiment_article_count": 7,
        }
        svc._save_snapshot("AAPL", data)
        row = db.query(StockSnapshot).filter(StockSnapshot.ticker == "AAPL").first()
        assert row is not None
        assert row.sentiment_source == "VADER"
        assert row.sentiment_article_count == 7

    def test_cached_snapshot_restores_sentiment_unavailable(self):
        """If cached row has sentiment_source='Unavailable', score must be None."""
        from app.models.market import StockSnapshot
        svc, db = self._make_service()

        row = StockSnapshot(
            ticker="NVDA", price=500.0, price_change_percent=2.0,
            volume=40_000_000, average_volume=42_000_000,
            volatility=0.02, sentiment_score=0.0,
            timestamp=datetime.utcnow(),
            data_source="Yahoo Finance",
            sentiment_source="Unavailable",
        )
        db.add(row)
        db.commit()

        cached = svc._get_cached_snapshot("NVDA")
        assert cached is not None
        assert cached["sentiment_score"] is None
        assert cached["sentiment_unavailable"] is True
        assert cached["sentiment_label"] == "Unavailable"

    def test_cached_snapshot_with_real_sentiment(self):
        """If cached row has sentiment_source='VADER', score must be restored."""
        from app.models.market import StockSnapshot
        svc, db = self._make_service()

        row = StockSnapshot(
            ticker="MSFT", price=400.0, price_change_percent=1.5,
            volume=20_000_000, average_volume=22_000_000,
            volatility=0.012, sentiment_score=0.45,
            timestamp=datetime.utcnow(),
            data_source="Yahoo Finance",
            sentiment_source="VADER",
            sentiment_article_count=8,
        )
        db.add(row)
        db.commit()

        cached = svc._get_cached_snapshot("MSFT")
        assert cached is not None
        assert cached["sentiment_score"] == pytest.approx(0.45)
        assert cached["sentiment_unavailable"] is False
        assert cached["sentiment_source"] == "VADER"
        assert cached["sentiment_article_count"] == 8


# ═══════════════════════════════════════════════════════════════════════════════
# 8. DB migration: SentimentCache table and new columns
# ═══════════════════════════════════════════════════════════════════════════════

class TestSentimentCacheModel:
    def _db(self):
        _, db = _make_db()
        return db

    def test_sentiment_cache_table_created(self):
        from sqlalchemy import inspect as sa_inspect
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        inspector = sa_inspect(engine)
        assert "sentiment_cache" in inspector.get_table_names()

    def test_sentiment_cache_has_required_columns(self):
        from sqlalchemy import inspect as sa_inspect
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        inspector = sa_inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("sentiment_cache")}
        for required in ["id", "ticker", "score", "label", "confidence",
                         "article_count", "source", "headlines_json",
                         "unavailable", "fetched_at"]:
            assert required in cols, f"Missing column: {required}"

    def test_stock_snapshot_has_sentiment_provenance_columns(self):
        from sqlalchemy import inspect as sa_inspect
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        inspector = sa_inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("stock_snapshots")}
        for required in ["sentiment_source", "sentiment_timestamp", "sentiment_article_count"]:
            assert required in cols, f"Missing column: {required}"

    def test_write_and_read_sentiment_cache_row(self):
        from app.models.market import SentimentCache
        db = self._db()
        row = SentimentCache(
            ticker="TCS", score=-0.3, label="Negative",
            confidence=0.65, article_count=4, source="VADER",
            headlines_json='[{"title": "TCS misses estimates"}]',
            unavailable=False, fetched_at=datetime.utcnow(),
        )
        db.add(row)
        db.commit()

        result = db.query(SentimentCache).filter(SentimentCache.ticker == "TCS").first()
        assert result is not None
        assert result.score == pytest.approx(-0.3)
        assert result.label == "Negative"
        assert result.source == "VADER"
        parsed = json.loads(result.headlines_json)
        assert parsed[0]["title"] == "TCS misses estimates"

    def test_ttl_expiry_logic(self):
        """Row older than TTL should not be returned by cache query."""
        from app.models.market import SentimentCache
        db = self._db()
        old_time = datetime.utcnow() - timedelta(hours=2)
        row = SentimentCache(
            ticker="RELIANCE", score=0.1, label="Neutral",
            confidence=0.3, article_count=2, source="VADER",
            headlines_json="[]", unavailable=False,
            fetched_at=old_time,
        )
        db.add(row)
        db.commit()

        cutoff = datetime.utcnow() - timedelta(seconds=3600)
        result = (db.query(SentimentCache)
                    .filter(SentimentCache.ticker == "RELIANCE",
                            SentimentCache.fetched_at >= cutoff)
                    .first())
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# 9. End-to-end: dashboard with unavailable sentiment (integration)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardWithUnavailableSentiment:
    """
    Integration tests using the test client + SQLite.
    No live network — sentiment service is mocked to return unavailable.
    """

    def test_dashboard_works_when_sentiment_unavailable(self, client, auth_headers):
        """
        Dashboard must return results even when all sentiment from the
        sentiment service is unavailable. In demo mode the DemoProvider
        provides preset sentiment, so we verify the dashboard succeeds
        and scores are in range — not that sentiment is marked unavailable
        (that only applies in yahoo mode where SentimentService is called).
        """
        from app.services.sentiment_service import SentimentService, _unavailable_result

        wl = client.post("/watchlists", json={"name": "Phase2Test"}, headers=auth_headers).json()
        client.post(f"/watchlists/{wl['id']}/stocks", json={"ticker": "TCS"}, headers=auth_headers)

        with patch.object(SentimentService, "get_sentiment", return_value=_unavailable_result()):
            response = client.get("/dashboard", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        all_stocks = (
            data["needs_attention"] + data["worth_watching"] + data["normal"]
        )
        assert len(all_stocks) > 0

        tcs = next((s for s in all_stocks if s["ticker"] == "TCS"), None)
        assert tcs is not None
        # Score must always be in valid range regardless of sentiment availability
        assert 0.0 <= tcs["attention_score"] <= 100.0
        # Dashboard must not crash
        assert data.get("partial_results", False) is False

    def test_dashboard_sentiment_provenance_exposed(self, client, auth_headers):
        """Dashboard response should include sentiment_source and article_count."""
        from app.services.sentiment_service import SentimentService

        mock_result = {
            "score": 0.35,
            "label": "Positive",
            "confidence": 0.7,
            "article_count": 6,
            "source": "VADER",
            "method": "lexicon_rule_based",
            "unavailable": False,
            "timestamp": "2025-01-01T10:00:00",
        }

        wl = client.post("/watchlists", json={"name": "SentTest"}, headers=auth_headers).json()
        client.post(f"/watchlists/{wl['id']}/stocks", json={"ticker": "TCS"}, headers=auth_headers)

        with patch.object(SentimentService, "get_sentiment", return_value=mock_result):
            response = client.get("/dashboard", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        all_stocks = data["needs_attention"] + data["worth_watching"] + data["normal"]
        tcs = next((s for s in all_stocks if s["ticker"] == "TCS"), None)
        assert tcs is not None
        # Provenance fields should be in dashboard result
        assert "sentiment_source" in tcs or "sentiment_article_count" in tcs

    def test_effective_weights_sum_to_one(self, client, auth_headers):
        """Effective weights in dashboard result must always sum to 1.0."""
        from app.services.sentiment_service import SentimentService, _unavailable_result

        wl = client.post("/watchlists", json={"name": "WeightTest"}, headers=auth_headers).json()
        client.post(f"/watchlists/{wl['id']}/stocks", json={"ticker": "AAPL"}, headers=auth_headers)

        with patch.object(SentimentService, "get_sentiment", return_value=_unavailable_result()):
            response = client.get("/dashboard", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        all_stocks = data["needs_attention"] + data["worth_watching"] + data["normal"]
        for stock in all_stocks:
            ew = stock.get("effective_weights")
            if ew:
                total = sum(ew.values())
                assert total == pytest.approx(1.0, abs=0.001), \
                    f"Weights don't sum to 1 for {stock['ticker']}: {ew}"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. get_model factory
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetModelFactory:
    def test_vader_returns_vader_when_available(self):
        from app.services.sentiment_service import _get_model, _VADERModel
        m = _get_model("vader")
        assert isinstance(m, _VADERModel)

    def test_keyword_returns_keyword(self):
        from app.services.sentiment_service import _get_model, _KeywordModel
        m = _get_model("keyword")
        assert isinstance(m, _KeywordModel)

    def test_unknown_returns_vader_if_available(self):
        from app.services.sentiment_service import _get_model, _VADERModel
        m = _get_model("unknown_model_xyz")
        assert isinstance(m, _VADERModel)

    def test_vader_falls_back_to_keyword_if_not_installed(self):
        """If vaderSentiment import fails, must fall back to keyword model."""
        from app.services.sentiment_service import _VADERModel, _KeywordModel
        m = _VADERModel()
        with patch.object(m, "_get_analyzer", return_value=None):
            assert m.is_available is False
        # The factory should return keyword if vader is unavailable
        with patch("app.services.sentiment_service._VADERModel.is_available",
                   new_callable=PropertyMock, return_value=False):
            from app.services.sentiment_service import _get_model
            result = _get_model("vader")
            assert isinstance(result, _KeywordModel)
