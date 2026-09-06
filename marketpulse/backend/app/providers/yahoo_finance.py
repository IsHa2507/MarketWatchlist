"""
YahooFinanceProvider — fetches real market data via yfinance.

This provider handles:
  - Indian NSE stocks  (TCS → TCS.NS, RELIANCE → RELIANCE.NS, etc.)
  - US stocks          (AAPL, NVDA, TSLA, MSFT, etc.)

Symbol resolution lives entirely in symbol_map.py — no .NS logic here.

Sentiment is NOT fetched here. Providers return sentiment_score=None
(explicitly unavailable) and the MarketDataService layer calls
SentimentService to fill it in separately with proper provenance tracking.

Important limitations (documented in README):
  - Yahoo Finance data may be delayed 15-20 minutes for US; 10 min for NSE.
  - yfinance is an unofficial library. It may break if Yahoo changes its API.
  - Do NOT call this on every frontend request. Use the cache in MarketDataService.
  - Never claim this provides exchange-grade real-time data.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.providers.base import BaseMarketProvider, compute_freshness
from app.providers.symbol_map import (
    SYMBOL_REGISTRY,
    get_all_tickers,
    get_company_meta,
    get_fallback_avg_volume,
    resolve_yahoo_symbol,
)

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None  # type: ignore[assignment]


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float safely, returning default on failure."""
    try:
        if value is None:
            return default
        f = float(value)
        # yfinance sometimes returns NaN
        if f != f:  # NaN check
            return default
        return f
    except (TypeError, ValueError):
        return default


def _calculate_volatility(history_df: Any) -> float:
    """
    Calculate annualised daily volatility from a yfinance history DataFrame.
    Returns a reasonable fallback if history is insufficient.
    """
    try:
        if history_df is None or len(history_df) < 2:
            return 0.015
        closes = history_df["Close"].dropna()
        if len(closes) < 2:
            return 0.015
        returns = closes.pct_change().dropna()
        if len(returns) < 1:
            return 0.015
        daily_std = float(returns.std())
        annualised = daily_std * (252 ** 0.5)
        # Clamp to reasonable range: 0.5% – 200%
        return round(max(0.005, min(2.0, annualised)), 6)
    except Exception:
        return 0.015


class YahooFinanceProvider(BaseMarketProvider):
    """
    Real market data from Yahoo Finance via yfinance.

    Caching is handled by MarketDataService — this provider always
    fetches fresh data when called. Do not call it directly in hot paths.
    """

    def is_available(self) -> bool:
        """Check if yfinance is importable and network is reachable."""
        return yf is not None

    def get_supported_tickers(self) -> List[str]:
        return get_all_tickers()

    def normalize_ticker(self, ticker: str) -> str:
        """Return the Yahoo symbol for a canonical ticker."""
        yahoo = resolve_yahoo_symbol(ticker.upper())
        return yahoo if yahoo else ticker.upper()

    # ------------------------------------------------------------------
    # Core quote fetch
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time quote from Yahoo Finance.

        Returns None if:
          - ticker is not in the symbol registry
          - yfinance raises an exception
          - the returned data contains no usable price
        """
        ticker = ticker.upper()
        meta = get_company_meta(ticker)
        if not meta:
            logger.warning("YahooFinanceProvider: unknown ticker '%s'", ticker)
            return None

        yahoo_symbol = meta["yahoo_symbol"]

        if yf is None:
            logger.error("yfinance is not installed. Run: pip install yfinance")
            return None

        try:
            stock = yf.Ticker(yahoo_symbol)

            # Fetch 5-day history for price + volatility calculation
            hist = stock.history(period="5d")

            # info dict — may be slow; contains most fields we need
            info = stock.info or {}

            fetch_time = datetime.utcnow()

            # ── Price ──────────────────────────────────────────────────
            # Prefer currentPrice; fall back to regularMarketPrice, then last close
            price = _safe_float(
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or (hist["Close"].iloc[-1] if len(hist) > 0 else None),
                default=0.0,
            )

            if price <= 0:
                logger.warning(
                    "YahooFinanceProvider: no valid price for '%s' (yahoo: %s)",
                    ticker, yahoo_symbol,
                )
                return None

            previous_close = _safe_float(
                info.get("previousClose")
                or info.get("regularMarketPreviousClose")
                or (hist["Close"].iloc[-2] if len(hist) > 1 else None),
                default=price,
            )

            price_change = round(price - previous_close, 4)
            price_change_pct = (
                round((price_change / previous_close) * 100, 4)
                if previous_close > 0 else 0.0
            )

            # ── Volume ─────────────────────────────────────────────────
            volume = _safe_float(
                info.get("volume") or info.get("regularMarketVolume"),
                default=0.0,
            )
            avg_volume = _safe_float(
                info.get("averageVolume") or info.get("averageDailyVolume10Day"),
                default=float(get_fallback_avg_volume(ticker)),
            )
            if avg_volume <= 0:
                avg_volume = float(get_fallback_avg_volume(ticker))

            # ── Volatility ─────────────────────────────────────────────
            volatility = _calculate_volatility(hist)

            # ── Market state ──────────────────────────────────────────
            market_state = info.get("marketState")  # PRE | REGULAR | POST | CLOSED

            # ── Data timestamp ────────────────────────────────────────
            # Use the last bar's timestamp from history if available
            if len(hist) > 0 and hasattr(hist.index, "__len__"):
                try:
                    data_ts = hist.index[-1].to_pydatetime().replace(tzinfo=None)
                except Exception:
                    data_ts = fetch_time
            else:
                data_ts = fetch_time

            # ── Freshness ─────────────────────────────────────────────
            freshness = compute_freshness(
                fetched_at=fetch_time,
                ttl_seconds=300,
                market_state=market_state,
            )

            # ── Company metadata override ─────────────────────────────
            # Prefer registry values; fall back to info dict
            company_name = (
                meta["name"]
                or info.get("longName")
                or info.get("shortName")
                or ticker
            )
            sector = meta.get("sector") or info.get("sector")
            currency = meta["currency"]

            return {
                "ticker": ticker,
                "yahoo_symbol": yahoo_symbol,
                "company_name": company_name,
                "sector": sector,
                "currency": currency,
                "price": round(price, 4),
                "previous_close": round(previous_close, 4),
                "price_change": round(price_change, 4),
                "price_change_percent": round(price_change_pct, 4),
                "volume": volume,
                "average_volume": avg_volume,
                "volatility": volatility,
                # Sentiment is NOT set here — it is populated separately by
                # SentimentService (via MarketDataService) with real news data.
                # Using None explicitly to distinguish "not yet computed"
                # from 0.0 which would mean "neutral".
                "sentiment_score": None,
                "sentiment_label": "Unavailable",
                "sentiment_unavailable": True,
                "market_state": market_state,
                "data_source": "Yahoo Finance",
                "data_timestamp": data_ts,
                "fetched_at": fetch_time,
                "freshness": freshness,
                # Backward-compat fields expected by existing services
                "last_updated": fetch_time,
                "data_confidence": "MEDIUM",  # delayed data — not exchange-grade
                "demo_mode": False,
            }

        except Exception as exc:
            logger.error(
                "YahooFinanceProvider.get_quote failed for '%s' (yahoo: %s): %s",
                ticker, yahoo_symbol, exc,
            )
            return None

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, ticker: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch real daily OHLCV history from Yahoo Finance.
        Returns [] if fetch fails (caller handles the fallback).
        """
        ticker = ticker.upper()
        meta = get_company_meta(ticker)
        if not meta:
            return []

        yahoo_symbol = meta["yahoo_symbol"]

        if yf is None:
            return []

        try:
            stock = yf.Ticker(yahoo_symbol)
            # Add a small buffer to ensure we get `days` trading days
            period_days = min(days + 10, 365)
            hist = stock.history(period=f"{period_days}d")

            if hist is None or len(hist) == 0:
                logger.warning(
                    "YahooFinanceProvider.get_history: empty history for '%s'", ticker
                )
                return []

            # Trim to requested number of rows
            hist = hist.tail(days)

            result = []
            for i, (idx, row) in enumerate(hist.iterrows()):
                try:
                    date_str = idx.strftime("%Y-%m-%d")
                    ts = idx.to_pydatetime().replace(tzinfo=None)
                    result.append({
                        "date": date_str,
                        "timestamp": ts.isoformat(),
                        "open": round(_safe_float(row.get("Open")), 4),
                        "high": round(_safe_float(row.get("High")), 4),
                        "low": round(_safe_float(row.get("Low")), 4),
                        "close": round(_safe_float(row.get("Close")), 4),
                        "volume": int(_safe_float(row.get("Volume"))),
                        "is_checkpoint": i == 0,
                    })
                except Exception:
                    continue

            return result

        except Exception as exc:
            logger.error(
                "YahooFinanceProvider.get_history failed for '%s': %s", ticker, exc
            )
            return []

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        """
        Search against the local symbol registry first (fast, offline).
        Does NOT call Yahoo Finance for search — avoids rate limiting.
        """
        query_upper = query.upper().strip()
        results = []

        for ticker in get_all_tickers():
            meta = get_company_meta(ticker)
            if not meta:
                continue
            if query_upper in ticker or query_upper in meta["name"].upper():
                # Return static metadata; price fetched separately when needed
                results.append({
                    "ticker": ticker,
                    "company_name": meta["name"],
                    "sector": meta["sector"],
                    "price": 0.0,            # caller fetches price via get_quote
                    "price_change_percent": 0.0,
                    "currency": meta["currency"],
                })

        return results
