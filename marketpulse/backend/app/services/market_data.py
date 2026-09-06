"""
MarketDataService
=================
Orchestrates market-data access for the rest of the application.

Phase 2 additions
------------------
- Calls SentimentService to get real news sentiment after provider fetch.
- Passes sentiment provenance (source, timestamp, article_count) through.
- Never treats sentiment=0.0 as neutral if news was unavailable.
- Passes closes[] to change_detection for real RSI-14 calculation.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.market import StockSnapshot
from app.providers import get_provider
from app.providers.base import FreshnessStatus, compute_freshness
from app.providers.demo import DemoProvider
from app.providers.symbol_map import (
    get_all_tickers,
    get_company_meta,
    get_fallback_avg_volume,
    is_supported,
)

from app.providers.symbol_map import SYMBOL_REGISTRY as COMPANY_METADATA  # noqa: F401

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Facade over the provider layer with database caching.

    Instantiated per-request (FastAPI dependency injection passes a db session).
    Provider selection is driven by settings.MARKET_DATA_PROVIDER.
    """

    def __init__(self, db: Session):
        self.db = db
        self._ttl = settings.MARKET_CACHE_TTL_SECONDS  # default 300 s
        self._provider = get_provider(settings.MARKET_DATA_PROVIDER)
        self._fallback = DemoProvider()
        self.demo_mode = settings.MARKET_DATA_PROVIDER.lower() != "yahoo"
        # SentimentService is created lazily to avoid circular imports
        self._sentiment_svc = None

    def _get_sentiment_service(self):
        """Lazy init to avoid import cycles at module load."""
        if self._sentiment_svc is None:
            from app.services.sentiment_service import SentimentService
            self._sentiment_svc = SentimentService(self.db)
        return self._sentiment_svc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_stock(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Primary entry point for a single stock quote.

        Flow:
          1. Check StockSnapshot cache (< TTL seconds old).
          2. If cache hit → return with freshness recalculated.
          3. Else call primary provider.
          4. Inject real sentiment (only in yahoo mode; demo has preset scores).
          5. If provider fails → call demo fallback.
          6. Persist result to cache (not on errors).
          7. Return result.
        """
        ticker = ticker.upper()
        if not is_supported(ticker):
            return None

        # 1. Cache check
        cached = self._get_cached_snapshot(ticker)
        if cached is not None:
            return cached

        # 2. Live fetch
        data = self._fetch_from_provider(ticker)
        if data is None:
            return None

        # 3. Inject sentiment for yahoo/real mode (not for demo — demo has preset scores)
        if not data.get("demo_mode", False):
            data = self._inject_sentiment(ticker, data)

        # 4. Persist to cache
        self._save_snapshot(ticker, data)
        return data

    def _inject_sentiment(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call SentimentService and merge sentiment fields into the stock data dict.
        Never raises — on any failure, marks sentiment as unavailable.
        """
        try:
            svc = self._get_sentiment_service()
            result = svc.get_sentiment(ticker)
            data["sentiment_score"] = result.get("score")       # None if unavailable
            data["sentiment_label"] = result.get("label", "Unavailable")
            data["sentiment_unavailable"] = result.get("unavailable", True)
            data["sentiment_source"] = result.get("source", "Unavailable")
            data["sentiment_timestamp"] = result.get("timestamp")
            data["sentiment_article_count"] = result.get("article_count", 0)
            data["sentiment_confidence"] = result.get("confidence", 0.0)
        except Exception as exc:
            logger.warning("Failed to inject sentiment for '%s': %s", ticker, exc)
            data["sentiment_score"] = None
            data["sentiment_label"] = "Unavailable"
            data["sentiment_unavailable"] = True
            data["sentiment_source"] = "Unavailable"
            data["sentiment_timestamp"] = None
            data["sentiment_article_count"] = 0
            data["sentiment_confidence"] = 0.0
        return data

    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Alias for get_stock — kept for backward compat."""
        return self.get_stock(ticker)

    def get_history(self, ticker: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV history.
        Tries primary provider first; falls back to demo if empty/error.
        History is NOT cached in the database (it's large and stale quickly).
        """
        ticker = ticker.upper()
        if not is_supported(ticker):
            return []

        try:
            history = self._provider.get_history(ticker, days)
            if history:
                return history
        except Exception as exc:
            logger.warning("History fetch failed for '%s' via primary provider: %s", ticker, exc)

        # Fallback to demo
        return self._fallback.get_history(ticker, days)

    def get_volume(self, ticker: str) -> Dict[str, Any]:
        """
        Return volume data for a ticker.
        Derives from get_stock to avoid a second fetch.
        """
        ticker = ticker.upper()
        stock = self.get_stock(ticker)
        if not stock:
            meta = get_company_meta(ticker) or {}
            avg_vol = meta.get("avg_volume", 1_000_000)
            return {
                "ticker": ticker,
                "current_volume": 0.0,
                "average_volume": float(avg_vol),
                "multiplier": 0.0,
            }

        current_vol = stock.get("volume", 0.0)
        avg_vol = stock.get("average_volume", float(get_fallback_avg_volume(ticker)))
        multiplier = (current_vol / avg_vol) if avg_vol > 0 else 1.0

        return {
            "ticker": ticker,
            "current_volume": current_vol,
            "average_volume": avg_vol,
            "multiplier": round(multiplier, 2),
        }

    def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for stocks matching query (ticker fragment or company name).
        Uses provider search (which hits the local registry, not Yahoo Finance).
        Enriches results with live prices if primary provider is yahoo and
        the match set is small (≤ 5) to avoid excessive API calls.
        """
        results = self._provider.search_stocks(query)

        # For Yahoo provider, enrich with real prices if result set is small
        if (
            settings.MARKET_DATA_PROVIDER.lower() == "yahoo"
            and 0 < len(results) <= 5
        ):
            enriched = []
            for r in results:
                quote = self.get_stock(r["ticker"])  # uses cache
                if quote:
                    r["price"] = quote.get("price", 0.0)
                    r["price_change_percent"] = quote.get("price_change_percent", 0.0)
                enriched.append(r)
            return enriched

        return results

    def get_all_tickers(self) -> List[str]:
        """Return all tickers supported by the current provider."""
        return get_all_tickers()

    # ------------------------------------------------------------------
    # Cache layer (StockSnapshot table)
    # ------------------------------------------------------------------

    def _get_cached_snapshot(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Look up the most recent StockSnapshot for ticker.
        Return a hydrated dict if it is younger than TTL; None otherwise.
        Never return a cached error row.
        """
        cutoff = datetime.utcnow() - timedelta(seconds=self._ttl)
        row = (
            self.db.query(StockSnapshot)
            .filter(
                StockSnapshot.ticker == ticker,
                StockSnapshot.timestamp >= cutoff,
            )
            .order_by(StockSnapshot.timestamp.desc())
            .first()
        )
        if row is None:
            return None

        # Reconstruct freshness from cached row
        fetched_at = row.fetched_at or row.timestamp
        market_state = None  # not stored in snapshot; will show as STALE if old

        freshness = compute_freshness(
            fetched_at=fetched_at,
            ttl_seconds=self._ttl,
            market_state=market_state,
        )

        # If freshness resolves to ERROR (shouldn't happen here), skip cache
        if freshness["status"] == FreshnessStatus.ERROR.value:
            return None

        meta = get_company_meta(ticker) or {}
        source = row.data_source or "Demo"

        # Determine if the cached sentiment was actually unavailable
        sentiment_source = getattr(row, "sentiment_source", "Unavailable") or "Unavailable"
        sentiment_unavailable = sentiment_source == "Unavailable"
        cached_sentiment_score = row.sentiment_score if not sentiment_unavailable else None

        return {
            "ticker": ticker,
            "yahoo_symbol": meta.get("yahoo_symbol", ticker),
            "company_name": meta.get("name", ticker),
            "sector": meta.get("sector"),
            "currency": meta.get("currency", "USD"),
            "price": row.price,
            "previous_close": row.price,
            "price_change": 0.0,
            "price_change_percent": row.price_change_percent,
            "volume": row.volume,
            "average_volume": row.average_volume,
            "volatility": row.volatility,
            "sentiment_score": cached_sentiment_score,
            "sentiment_label": self._sentiment_label(row.sentiment_score) if not sentiment_unavailable else "Unavailable",
            "sentiment_unavailable": sentiment_unavailable,
            "sentiment_source": sentiment_source,
            "sentiment_timestamp": getattr(row, "sentiment_timestamp", None),
            "sentiment_article_count": getattr(row, "sentiment_article_count", 0) or 0,
            "sentiment_confidence": 0.0,
            "market_state": None,
            "data_source": f"Cache ({source})",
            "data_timestamp": row.data_timestamp or row.timestamp,
            "fetched_at": fetched_at,
            "freshness": freshness,
            "last_updated": fetched_at,
            "data_confidence": "MEDIUM" if source == "Yahoo Finance" else "HIGH",
            "demo_mode": source == "Demo",
        }

    def _save_snapshot(self, ticker: str, data: Dict[str, Any]) -> None:
        """Upsert a StockSnapshot row. Does not save error/None results."""
        try:
            now = datetime.utcnow()
            freshness = data.get("freshness", {})
            freshness_status = freshness.get("status", FreshnessStatus.FRESH)
            if hasattr(freshness_status, "value"):
                freshness_status = freshness_status.value

            # sentiment_score may be None (unavailable); store as 0.0 in DB
            # but preserve the provenance so we know it was actually unavailable
            sentiment_score_db = data.get("sentiment_score")
            if sentiment_score_db is None:
                sentiment_score_db = 0.0

            row = StockSnapshot(
                ticker=ticker,
                price=data.get("price", 0.0),
                price_change_percent=data.get("price_change_percent", 0.0),
                volume=data.get("volume", 0.0),
                average_volume=data.get("average_volume", float(get_fallback_avg_volume(ticker))),
                volatility=data.get("volatility", 0.015),
                sentiment_score=sentiment_score_db,
                timestamp=now,
                data_source=data.get("data_source", "Demo"),
                data_timestamp=data.get("data_timestamp"),
                fetched_at=data.get("fetched_at", now),
                freshness_status=freshness_status,
                is_stale=False,
                # Phase 2: sentiment provenance
                sentiment_source=data.get("sentiment_source", "Unavailable"),
                sentiment_timestamp=_parse_dt(data.get("sentiment_timestamp")),
                sentiment_article_count=data.get("sentiment_article_count", 0),
            )
            self.db.add(row)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.warning("Failed to save snapshot for '%s': %s", ticker, exc)

    # ------------------------------------------------------------------
    # Provider fetch with fallback
    # ------------------------------------------------------------------

    def _fetch_from_provider(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Try primary provider. On failure, try demo fallback.
        Returns None only if both fail.
        """
        # Primary
        try:
            data = self._provider.get_quote(ticker)
            if data is not None:
                return data
            logger.warning("Primary provider returned None for '%s'", ticker)
        except Exception as exc:
            logger.error("Primary provider error for '%s': %s", ticker, exc)

        # Demo fallback (always works)
        logger.info("Falling back to DemoProvider for '%s'", ticker)
        try:
            fallback_data = self._fallback.get_quote(ticker)
            if fallback_data:
                # Mark clearly as demo fallback
                fallback_data["data_source"] = "Demo (fallback)"
                fallback_data["demo_mode"] = True
                return fallback_data
        except Exception as exc:
            logger.error("DemoProvider fallback also failed for '%s': %s", ticker, exc)

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sentiment_label(score: float) -> str:
        if score > 0.3:
            return "Positive"
        if score < -0.3:
            return "Negative"
        return "Neutral"


def _parse_dt(value) -> Optional[datetime]:
    """Safely convert a string or datetime to datetime; return None on failure."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except Exception:
        return None
