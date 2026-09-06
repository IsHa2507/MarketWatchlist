"""
Market data providers for MarketPulse.

Provider hierarchy:
    MarketDataService
        ├── YahooFinanceProvider   (MARKET_DATA_PROVIDER=yahoo)
        └── DemoProvider           (MARKET_DATA_PROVIDER=demo  — always works offline)

Usage:
    from app.providers import get_provider
    provider = get_provider()
    quote = provider.get_quote("TCS")
"""
from app.providers.base import BaseMarketProvider, FreshnessStatus
from app.providers.demo import DemoProvider
from app.providers.yahoo_finance import YahooFinanceProvider


def get_provider(provider_name: str = "demo") -> BaseMarketProvider:
    """
    Factory: return the right provider based on the config string.
    Falls back to DemoProvider if an unknown name is given.
    """
    name = provider_name.lower().strip()
    if name == "yahoo":
        return YahooFinanceProvider()
    return DemoProvider()


__all__ = [
    "BaseMarketProvider",
    "FreshnessStatus",
    "DemoProvider",
    "YahooFinanceProvider",
    "get_provider",
]
