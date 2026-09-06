"""
DemoProvider — fully offline, deterministic market data.

This is the original market_data.py demo logic extracted into its own class.
It is always available as a fallback when:
  - MARKET_DATA_PROVIDER=demo
  - Yahoo Finance is unreachable
  - A ticker fetch fails in live mode

All prices are seeded/scenario-based — never real market prices.
The UI will show a "Demo Mode" badge when this provider is active.
"""
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.providers.base import BaseMarketProvider, compute_freshness
from app.providers.symbol_map import SYMBOL_REGISTRY, get_all_tickers, get_company_meta


# ---------------------------------------------------------------------------
# Demo scenarios — deterministic, never changes between runs
# ---------------------------------------------------------------------------

_DEMO_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "TCS": {
        "price_change_pct": -3.8,
        "volume_multiplier": 2.1,
        "sentiment_score": -0.42,
        "sentiment_label": "Negative",
        "volatility": 0.038,
    },
    "NVDA": {
        "price_change_pct": 6.2,
        "volume_multiplier": 2.8,
        "sentiment_score": 0.71,
        "sentiment_label": "Positive",
        "volatility": 0.065,
    },
    "RELIANCE": {
        "price_change_pct": 2.4,
        "volume_multiplier": 1.8,
        "sentiment_score": 0.35,
        "sentiment_label": "Positive",
        "volatility": 0.024,
    },
    "ICICIBANK": {
        "price_change_pct": 1.8,
        "volume_multiplier": 1.4,
        "sentiment_score": 0.18,
        "sentiment_label": "Neutral",
        "volatility": 0.018,
    },
    "HDFCBANK": {
        "price_change_pct": 0.4,
        "volume_multiplier": 0.9,
        "sentiment_score": 0.05,
        "sentiment_label": "Neutral",
        "volatility": 0.008,
    },
    "INFY": {
        "price_change_pct": 0.3,
        "volume_multiplier": 1.0,
        "sentiment_score": 0.02,
        "sentiment_label": "Neutral",
        "volatility": 0.007,
    },
    "AAPL": {
        "price_change_pct": -0.8,
        "volume_multiplier": 1.1,
        "sentiment_score": -0.08,
        "sentiment_label": "Neutral",
        "volatility": 0.010,
    },
    "TSLA": {
        "price_change_pct": -1.2,
        "volume_multiplier": 1.3,
        "sentiment_score": -0.12,
        "sentiment_label": "Neutral",
        "volatility": 0.018,
    },
    "MSFT": {
        "price_change_pct": 0.6,
        "volume_multiplier": 0.95,
        "sentiment_score": 0.10,
        "sentiment_label": "Neutral",
        "volatility": 0.009,
    },
    "AMZN": {
        "price_change_pct": 1.1,
        "volume_multiplier": 1.2,
        "sentiment_score": 0.15,
        "sentiment_label": "Neutral",
        "volatility": 0.013,
    },
    "GOOGL": {
        "price_change_pct": 0.9,
        "volume_multiplier": 1.05,
        "sentiment_score": 0.12,
        "sentiment_label": "Neutral",
        "volatility": 0.011,
    },
    "META": {
        "price_change_pct": 1.5,
        "volume_multiplier": 1.3,
        "sentiment_score": 0.22,
        "sentiment_label": "Positive",
        "volatility": 0.016,
    },
    "WIPRO": {
        "price_change_pct": 0.2,
        "volume_multiplier": 0.85,
        "sentiment_score": 0.01,
        "sentiment_label": "Neutral",
        "volatility": 0.006,
    },
    "AXISBANK": {
        "price_change_pct": 1.0,
        "volume_multiplier": 1.15,
        "sentiment_score": 0.08,
        "sentiment_label": "Neutral",
        "volatility": 0.012,
    },
}

# Base prices used only in demo mode — never shown as "real" prices
_DEMO_BASE_PRICES: Dict[str, float] = {
    "TCS": 3842.0,
    "RELIANCE": 2945.0,
    "INFY": 1482.0,
    "HDFCBANK": 1623.0,
    "ICICIBANK": 1142.0,
    "WIPRO": 481.0,
    "AXISBANK": 1205.0,
    "AAPL": 189.30,
    "NVDA": 875.40,
    "TSLA": 177.80,
    "MSFT": 415.20,
    "AMZN": 182.50,
    "GOOGL": 175.60,
    "META": 505.80,
}

_DEFAULT_SCENARIO: Dict[str, Any] = {
    "price_change_pct": 0.0,
    "volume_multiplier": 1.0,
    "sentiment_score": 0.0,
    "sentiment_label": "Neutral",
    "volatility": 0.015,
}


class DemoProvider(BaseMarketProvider):
    """
    Offline demo provider — works without any API key or internet access.
    Returns deterministic, scenario-based data seeded per ticker.
    The UI displays a 'Demo Mode' label when this provider is active.
    """

    def is_available(self) -> bool:
        return True

    def get_supported_tickers(self) -> List[str]:
        return get_all_tickers()

    def normalize_ticker(self, ticker: str) -> str:
        return ticker.upper()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        ticker = ticker.upper()
        meta = get_company_meta(ticker)
        if not meta:
            return None

        scenario = _DEMO_SCENARIOS.get(ticker, _DEFAULT_SCENARIO)
        base_price = _DEMO_BASE_PRICES.get(ticker, 100.0)
        price_change_pct = scenario["price_change_pct"]
        current_price = round(base_price * (1 + price_change_pct / 100), 2)
        price_change = round(current_price - base_price, 2)
        avg_vol = meta["avg_volume"]
        volume = avg_vol * scenario["volume_multiplier"]

        now = datetime.utcnow()
        freshness = compute_freshness(
            fetched_at=now,
            ttl_seconds=300,
            market_state="REGULAR",
        )

        return {
            "ticker": ticker,
            "yahoo_symbol": meta["yahoo_symbol"],
            "company_name": meta["name"],
            "sector": meta["sector"],
            "currency": meta["currency"],
            "price": current_price,
            "previous_close": base_price,
            "price_change": price_change,
            "price_change_percent": price_change_pct,
            "volume": volume,
            "average_volume": avg_vol,
            "volatility": scenario["volatility"],
            "sentiment_score": scenario["sentiment_score"],
            "sentiment_label": scenario["sentiment_label"],
            "market_state": "REGULAR",
            "data_source": "Demo",
            "data_timestamp": now,
            "fetched_at": now,
            "freshness": freshness,
            # Backward-compat fields
            "last_updated": now,
            "data_confidence": "HIGH",
            "demo_mode": True,
        }

    def get_history(self, ticker: str, days: int = 30) -> List[Dict[str, Any]]:
        ticker = ticker.upper()
        meta = get_company_meta(ticker)
        if not meta:
            return []

        scenario = _DEMO_SCENARIOS.get(ticker, _DEFAULT_SCENARIO)
        base_price = _DEMO_BASE_PRICES.get(ticker, 100.0)
        price_change_pct = scenario["price_change_pct"]
        current_price = base_price * (1 + price_change_pct / 100)
        avg_vol = meta["avg_volume"]
        vol_multi = scenario["volume_multiplier"]

        # Seeded random — deterministic per ticker
        rng = random.Random(hash(ticker) % (2**31))

        # Build history walking backwards from current price
        prices = [current_price]
        daily_drift = price_change_pct / 100 / max(days, 1)
        for _ in range(days - 1):
            noise = rng.gauss(0, 0.008)
            prev = prices[-1] / (1 + daily_drift + noise)
            prices.append(round(prev, 2))

        prices.reverse()

        now = datetime.utcnow()
        history = []
        for i, price in enumerate(prices):
            date = now - timedelta(days=days - i)
            progress = i / max(days - 1, 1)
            vol_factor = 1 + (vol_multi - 1) * progress
            volume = int(avg_vol * vol_factor * (0.8 + rng.random() * 0.4))
            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "timestamp": date.isoformat(),
                "open": round(price * (1 - rng.uniform(0, 0.005)), 2),
                "high": round(price * (1 + rng.uniform(0, 0.01)), 2),
                "low": round(price * (1 - rng.uniform(0, 0.01)), 2),
                "close": price,
                "volume": volume,
                "is_checkpoint": i == 0,
            })
        return history

    def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        query_upper = query.upper().strip()
        results = []
        for ticker in get_all_tickers():
            meta = get_company_meta(ticker)
            if not meta:
                continue
            if query_upper in ticker or query_upper in meta["name"].upper():
                scenario = _DEMO_SCENARIOS.get(ticker, _DEFAULT_SCENARIO)
                base_price = _DEMO_BASE_PRICES.get(ticker, 100.0)
                price_change_pct = scenario["price_change_pct"]
                results.append({
                    "ticker": ticker,
                    "company_name": meta["name"],
                    "sector": meta["sector"],
                    "price": round(base_price * (1 + price_change_pct / 100), 2),
                    "price_change_percent": price_change_pct,
                    "currency": meta["currency"],
                })
        return results
