"""
BaseMarketProvider — abstract interface every provider must implement.

All providers return the same dict shapes so MarketDataService
is completely decoupled from any specific data source.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum


class FreshnessStatus(str, Enum):
    """
    Represents how fresh the market data is.

    FRESH   — fetched within the configured TTL (e.g. < 5 min)
    STALE   — older than TTL but still usable
    CLOSED  — market is closed; data is from the last session close
    ERROR   — data could not be fetched; showing last known snapshot
    """
    FRESH = "FRESH"
    STALE = "STALE"
    CLOSED = "CLOSED"
    ERROR = "ERROR"


def compute_freshness(
    fetched_at: Optional[datetime],
    ttl_seconds: int = 300,
    market_state: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute a freshness dict that both the backend API and
    frontend can consume directly.

    Args:
        fetched_at:    When the data was last retrieved.
        ttl_seconds:   Cache TTL in seconds (default 300 = 5 min).
        market_state:  Yahoo market state string: PRE / REGULAR / POST / CLOSED.

    Returns a dict:
        {
            "status": "FRESH" | "STALE" | "CLOSED" | "ERROR",
            "fetched_at": "ISO string or None",
            "age_seconds": int,
            "ttl_seconds": int,
            "market_state": str | None,
            "label": "🟢 Live" | "🟡 4 min ago" | etc.,
        }
    """
    now = datetime.utcnow()

    if fetched_at is None:
        return {
            "status": FreshnessStatus.ERROR.value,
            "fetched_at": None,
            "age_seconds": -1,
            "ttl_seconds": ttl_seconds,
            "market_state": market_state,
            "label": "🔴 No data",
        }

    age_seconds = int((now - fetched_at).total_seconds())

    # Determine status
    if market_state in ("CLOSED", "POST"):
        status = FreshnessStatus.CLOSED
        label = "⚪ Market closed"
    elif age_seconds <= ttl_seconds:
        status = FreshnessStatus.FRESH
        label = "🟢 Live"
    elif age_seconds <= ttl_seconds * 6:   # up to 30 min = STALE
        mins = age_seconds // 60
        status = FreshnessStatus.STALE
        label = f"🟡 {mins}m ago"
    else:
        status = FreshnessStatus.STALE
        mins = age_seconds // 60
        label = f"🟡 {mins}m ago"

    return {
        "status": status.value,          # always a plain string, never an enum
        "fetched_at": fetched_at.isoformat() + "Z",
        "age_seconds": age_seconds,
        "ttl_seconds": ttl_seconds,
        "market_state": market_state,
        "label": label,
    }


class BaseMarketProvider(ABC):
    """
    Abstract base class for all market data providers.

    Every concrete provider (Yahoo Finance, Demo, future providers)
    must implement these three methods and return the documented dict shapes.
    """

    # ------------------------------------------------------------------
    # Required interface
    # ------------------------------------------------------------------

    @abstractmethod
    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the latest quote for a single ticker.

        Returns None if the ticker is unknown or the fetch fails.

        Return shape (all fields should be present; use None for unavailable):
            {
                "ticker":               str,     # canonical app ticker, e.g. "TCS"
                "yahoo_symbol":         str,     # provider symbol, e.g. "TCS.NS"
                "company_name":         str,
                "sector":               str | None,
                "currency":             str,     # "INR" | "USD"
                "price":                float,
                "previous_close":       float | None,
                "price_change":         float,
                "price_change_percent": float,
                "volume":               float,
                "average_volume":       float,
                "volatility":           float,   # annualised daily std dev estimate
                "sentiment_score":      float,   # -1.0 to 1.0; 0.0 if not available
                "sentiment_label":      str,     # "Positive" | "Negative" | "Neutral"
                "market_state":         str | None,  # PRE|REGULAR|POST|CLOSED
                "data_source":          str,     # "Yahoo Finance" | "Demo"
                "data_timestamp":       datetime,  # when the underlying data is from
                "fetched_at":           datetime,  # when we fetched it
                "demo_mode":            bool,
            }
        """

    @abstractmethod
    def get_history(self, ticker: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Return daily OHLCV history for the last `days` calendar days.

        Return shape (list of dicts):
            {
                "date":          str,    # "YYYY-MM-DD"
                "timestamp":     str,    # ISO
                "open":          float,
                "high":          float,
                "low":           float,
                "close":         float,
                "volume":        int,
                "is_checkpoint": bool,  # True for the first (oldest) point
            }
        """

    @abstractmethod
    def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for stocks matching `query` (ticker or company name fragment).

        Return shape (list of dicts):
            {
                "ticker":               str,
                "company_name":         str,
                "sector":               str | None,
                "price":                float,
                "price_change_percent": float,
                "currency":             str,
            }
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider can currently serve requests."""

    # ------------------------------------------------------------------
    # Optional helpers — providers may override
    # ------------------------------------------------------------------

    def normalize_ticker(self, ticker: str) -> str:
        """
        Convert the app-internal ticker (e.g. "TCS") to the
        provider-specific symbol (e.g. "TCS.NS").
        Default: no-op.
        """
        return ticker.upper()

    def get_supported_tickers(self) -> List[str]:
        """
        Return the list of tickers this provider supports.
        Used for search and validation.
        """
        return []
