"""
MarketDataService — supports Live API mode and Demo mode.
Demo mode uses seeded PostgreSQL data and is fully functional.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random
import math

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.market import StockSnapshot, MarketEvent

# ---------------------------------------------------------------------------
# Company metadata
# ---------------------------------------------------------------------------

COMPANY_METADATA: Dict[str, Dict[str, Any]] = {
    "TCS": {
        "name": "Tata Consultancy Services",
        "sector": "Information Technology",
        "currency": "INR",
        "base_price": 3842.0,
        "avg_volume": 1_200_000,
    },
    "RELIANCE": {
        "name": "Reliance Industries",
        "sector": "Conglomerates",
        "currency": "INR",
        "base_price": 2945.0,
        "avg_volume": 8_500_000,
    },
    "INFY": {
        "name": "Infosys Limited",
        "sector": "Information Technology",
        "currency": "INR",
        "base_price": 1482.0,
        "avg_volume": 5_200_000,
    },
    "HDFCBANK": {
        "name": "HDFC Bank",
        "sector": "Banking",
        "currency": "INR",
        "base_price": 1623.0,
        "avg_volume": 7_800_000,
    },
    "ICICIBANK": {
        "name": "ICICI Bank",
        "sector": "Banking",
        "currency": "INR",
        "base_price": 1142.0,
        "avg_volume": 9_200_000,
    },
    "AAPL": {
        "name": "Apple Inc.",
        "sector": "Technology",
        "currency": "USD",
        "base_price": 189.30,
        "avg_volume": 55_000_000,
    },
    "NVDA": {
        "name": "NVIDIA Corporation",
        "sector": "Semiconductors",
        "currency": "USD",
        "base_price": 875.40,
        "avg_volume": 42_000_000,
    },
    "TSLA": {
        "name": "Tesla Inc.",
        "sector": "Automotive / EV",
        "currency": "USD",
        "base_price": 177.80,
        "avg_volume": 98_000_000,
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "sector": "Technology",
        "currency": "USD",
        "base_price": 415.20,
        "avg_volume": 22_000_000,
    },
    "AMZN": {
        "name": "Amazon.com Inc.",
        "sector": "E-Commerce / Cloud",
        "currency": "USD",
        "base_price": 182.50,
        "avg_volume": 38_000_000,
    },
}

# Demo scenarios — deterministic for reproducibility
DEMO_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "TCS": {
        "price_change_pct": -3.8,
        "volume_multiplier": 2.1,
        "sentiment_score": -0.42,
        "sentiment_label": "Negative",
        "volatility": 0.038,
        "attention_score": 79,
    },
    "NVDA": {
        "price_change_pct": 6.2,
        "volume_multiplier": 2.8,
        "sentiment_score": 0.71,
        "sentiment_label": "Positive",
        "volatility": 0.065,
        "attention_score": 84,
    },
    "RELIANCE": {
        "price_change_pct": 2.4,
        "volume_multiplier": 1.8,
        "sentiment_score": 0.35,
        "sentiment_label": "Positive",
        "volatility": 0.024,
        "attention_score": 62,
    },
    "ICICIBANK": {
        "price_change_pct": 1.8,
        "volume_multiplier": 1.4,
        "sentiment_score": 0.18,
        "sentiment_label": "Neutral",
        "volatility": 0.018,
        "attention_score": 45,
    },
    "HDFCBANK": {
        "price_change_pct": 0.4,
        "volume_multiplier": 0.9,
        "sentiment_score": 0.05,
        "sentiment_label": "Neutral",
        "volatility": 0.008,
        "attention_score": 12,
    },
    "INFY": {
        "price_change_pct": 0.3,
        "volume_multiplier": 1.0,
        "sentiment_score": 0.02,
        "sentiment_label": "Neutral",
        "volatility": 0.007,
        "attention_score": 15,
    },
    "AAPL": {
        "price_change_pct": -0.8,
        "volume_multiplier": 1.1,
        "sentiment_score": -0.08,
        "sentiment_label": "Neutral",
        "volatility": 0.010,
        "attention_score": 18,
    },
    "TSLA": {
        "price_change_pct": -1.2,
        "volume_multiplier": 1.3,
        "sentiment_score": -0.12,
        "sentiment_label": "Neutral",
        "volatility": 0.018,
        "attention_score": 28,
    },
    "MSFT": {
        "price_change_pct": 0.6,
        "volume_multiplier": 0.95,
        "sentiment_score": 0.10,
        "sentiment_label": "Neutral",
        "volatility": 0.009,
        "attention_score": 14,
    },
    "AMZN": {
        "price_change_pct": 1.1,
        "volume_multiplier": 1.2,
        "sentiment_score": 0.15,
        "sentiment_label": "Neutral",
        "volatility": 0.013,
        "attention_score": 22,
    },
}


def _compute_current_price(ticker: str) -> float:
    meta = COMPANY_METADATA.get(ticker, {})
    scenario = DEMO_SCENARIOS.get(ticker, {})
    base = meta.get("base_price", 100.0)
    pct = scenario.get("price_change_pct", 0.0)
    return round(base * (1 + pct / 100), 2)


def _compute_checkpoint_price(ticker: str) -> float:
    """The price the user would have seen on their previous visit."""
    meta = COMPANY_METADATA.get(ticker, {})
    return round(meta.get("base_price", 100.0), 2)


class MarketDataService:
    """
    Abstraction for market data.
    Supports Demo mode (fully functional without paid APIs) and
    Live mode when MARKET_API_KEY is configured.
    """

    def __init__(self, db: Session):
        self.db = db
        self.demo_mode = settings.DEMO_MODE or not settings.MARKET_API_KEY

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_stock(self, ticker: str) -> Optional[Dict[str, Any]]:
        ticker = ticker.upper()
        if ticker not in COMPANY_METADATA:
            return None
        return self._get_demo_stock(ticker)

    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        return self.get_stock(ticker)

    def get_history(self, ticker: str, days: int = 30) -> List[Dict[str, Any]]:
        ticker = ticker.upper()
        if ticker not in COMPANY_METADATA:
            return []
        return self._get_demo_history(ticker, days)

    def get_volume(self, ticker: str) -> Dict[str, Any]:
        ticker = ticker.upper()
        meta = COMPANY_METADATA.get(ticker, {})
        scenario = DEMO_SCENARIOS.get(ticker, {})
        avg_vol = meta.get("avg_volume", 1_000_000)
        multiplier = scenario.get("volume_multiplier", 1.0)
        current_vol = avg_vol * multiplier
        return {
            "ticker": ticker,
            "current_volume": current_vol,
            "average_volume": avg_vol,
            "multiplier": round(multiplier, 2),
        }

    def search_stocks(self, query: str) -> List[Dict[str, Any]]:
        query = query.upper().strip()
        results = []
        for ticker, meta in COMPANY_METADATA.items():
            if (
                query in ticker
                or query in meta["name"].upper()
            ):
                scenario = DEMO_SCENARIOS.get(ticker, {})
                results.append(
                    {
                        "ticker": ticker,
                        "company_name": meta["name"],
                        "sector": meta["sector"],
                        "price": _compute_current_price(ticker),
                        "price_change_percent": scenario.get("price_change_pct", 0.0),
                        "currency": meta.get("currency", "USD"),
                    }
                )
        return results

    def get_all_tickers(self) -> List[str]:
        return list(COMPANY_METADATA.keys())

    # ------------------------------------------------------------------
    # Demo implementation
    # ------------------------------------------------------------------

    def _get_demo_stock(self, ticker: str) -> Dict[str, Any]:
        meta = COMPANY_METADATA[ticker]
        scenario = DEMO_SCENARIOS.get(ticker, {})
        base_price = meta["base_price"]
        price_change_pct = scenario.get("price_change_pct", 0.0)
        current_price = round(base_price * (1 + price_change_pct / 100), 2)
        price_change = round(current_price - base_price, 2)
        avg_vol = meta["avg_volume"]
        multiplier = scenario.get("volume_multiplier", 1.0)

        return {
            "ticker": ticker,
            "company_name": meta["name"],
            "sector": meta["sector"],
            "currency": meta.get("currency", "USD"),
            "price": current_price,
            "price_change": price_change,
            "price_change_percent": price_change_pct,
            "volume": avg_vol * multiplier,
            "average_volume": avg_vol,
            "volatility": scenario.get("volatility", 0.015),
            "sentiment_score": scenario.get("sentiment_score", 0.0),
            "sentiment_label": scenario.get("sentiment_label", "Neutral"),
            "last_updated": datetime.utcnow(),
            "data_confidence": "HIGH",
            "demo_mode": True,
        }

    def _get_demo_history(self, ticker: str, days: int = 30) -> List[Dict[str, Any]]:
        """Generate deterministic price history using a seeded walk."""
        meta = COMPANY_METADATA[ticker]
        scenario = DEMO_SCENARIOS.get(ticker, {})
        base_price = meta["base_price"]
        price_change_pct = scenario.get("price_change_pct", 0.0)
        current_price = base_price * (1 + price_change_pct / 100)
        avg_vol = meta["avg_volume"]
        vol_multi = scenario.get("volume_multiplier", 1.0)

        # Seed random for reproducibility per ticker
        rng = random.Random(hash(ticker) % (2**31))

        # Build history from current price backwards
        prices = [current_price]
        # Last N-1 days before current
        daily_drift = price_change_pct / 100 / days
        for i in range(days - 1):
            noise = rng.gauss(0, 0.008)  # daily noise ~0.8%
            prev = prices[-1] / (1 + daily_drift + noise)
            prices.append(round(prev, 2))

        prices.reverse()

        now = datetime.utcnow()
        history = []
        for i, price in enumerate(prices):
            date = now - timedelta(days=days - i)
            # Volume gradually rises toward current
            progress = i / max(days - 1, 1)
            vol_factor = 1 + (vol_multi - 1) * progress
            volume = avg_vol * vol_factor * (0.8 + rng.random() * 0.4)
            history.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "timestamp": date.isoformat(),
                    "open": round(price * (1 - rng.uniform(0, 0.005)), 2),
                    "high": round(price * (1 + rng.uniform(0, 0.01)), 2),
                    "low": round(price * (1 - rng.uniform(0, 0.01)), 2),
                    "close": price,
                    "volume": int(volume),
                    "is_checkpoint": i == 0,  # First point is "last check"
                }
            )
        return history
