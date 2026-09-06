"""
Symbol mapping — single source of truth for ticker ↔ Yahoo Finance symbol.

The application uses short canonical tickers internally (e.g. "TCS", "AAPL").
Yahoo Finance requires suffixed symbols for non-US exchanges (e.g. "TCS.NS").

All .NS logic lives here. Nothing else in the codebase should know about suffixes.

Public API
----------
    resolve_yahoo_symbol("TCS")      → "TCS.NS"
    resolve_yahoo_symbol("AAPL")     → "AAPL"
    canonical_ticker("TCS.NS")       → "TCS"
    get_all_tickers()                → ["TCS", "RELIANCE", ...]
    get_company_meta("TCS")          → {"name": "Tata...", "sector": ..., "currency": ...}
    is_supported("TCS")              → True
    is_supported("FAKEXXX")          → False
"""
from typing import Dict, List, Optional, Any


# ---------------------------------------------------------------------------
# Master registry
# Each entry:
#   canonical_ticker → {
#       yahoo_symbol:  str     (symbol to pass to yfinance)
#       name:          str     (display name)
#       sector:        str
#       currency:      str     ("INR" | "USD")
#       avg_volume:    int     (fallback when provider doesn't return avg vol)
#   }
# ---------------------------------------------------------------------------

SYMBOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ── Indian (NSE) ────────────────────────────────────────────────────────
    "TCS": {
        "yahoo_symbol": "TCS.NS",
        "name": "Tata Consultancy Services",
        "sector": "Information Technology",
        "currency": "INR",
        "avg_volume": 1_200_000,
    },
    "RELIANCE": {
        "yahoo_symbol": "RELIANCE.NS",
        "name": "Reliance Industries",
        "sector": "Conglomerates",
        "currency": "INR",
        "avg_volume": 8_500_000,
    },
    "INFY": {
        "yahoo_symbol": "INFY.NS",
        "name": "Infosys Limited",
        "sector": "Information Technology",
        "currency": "INR",
        "avg_volume": 5_200_000,
    },
    "HDFCBANK": {
        "yahoo_symbol": "HDFCBANK.NS",
        "name": "HDFC Bank",
        "sector": "Banking",
        "currency": "INR",
        "avg_volume": 7_800_000,
    },
    "ICICIBANK": {
        "yahoo_symbol": "ICICIBANK.NS",
        "name": "ICICI Bank",
        "sector": "Banking",
        "currency": "INR",
        "avg_volume": 9_200_000,
    },
    "WIPRO": {
        "yahoo_symbol": "WIPRO.NS",
        "name": "Wipro Limited",
        "sector": "Information Technology",
        "currency": "INR",
        "avg_volume": 4_100_000,
    },
    "AXISBANK": {
        "yahoo_symbol": "AXISBANK.NS",
        "name": "Axis Bank",
        "sector": "Banking",
        "currency": "INR",
        "avg_volume": 6_300_000,
    },
    # ── US ──────────────────────────────────────────────────────────────────
    "AAPL": {
        "yahoo_symbol": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "currency": "USD",
        "avg_volume": 55_000_000,
    },
    "NVDA": {
        "yahoo_symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "sector": "Semiconductors",
        "currency": "USD",
        "avg_volume": 42_000_000,
    },
    "TSLA": {
        "yahoo_symbol": "TSLA",
        "name": "Tesla Inc.",
        "sector": "Automotive / EV",
        "currency": "USD",
        "avg_volume": 98_000_000,
    },
    "MSFT": {
        "yahoo_symbol": "MSFT",
        "name": "Microsoft Corporation",
        "sector": "Technology",
        "currency": "USD",
        "avg_volume": 22_000_000,
    },
    "AMZN": {
        "yahoo_symbol": "AMZN",
        "name": "Amazon.com Inc.",
        "sector": "E-Commerce / Cloud",
        "currency": "USD",
        "avg_volume": 38_000_000,
    },
    "GOOGL": {
        "yahoo_symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "sector": "Technology",
        "currency": "USD",
        "avg_volume": 25_000_000,
    },
    "META": {
        "yahoo_symbol": "META",
        "name": "Meta Platforms Inc.",
        "sector": "Social Media / Technology",
        "currency": "USD",
        "avg_volume": 20_000_000,
    },
}

# Reverse map: yahoo_symbol → canonical ticker
_REVERSE_MAP: Dict[str, str] = {
    v["yahoo_symbol"]: k for k, v in SYMBOL_REGISTRY.items()
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_yahoo_symbol(ticker: str) -> Optional[str]:
    """
    Convert canonical ticker → Yahoo Finance symbol.

    "TCS"    → "TCS.NS"
    "AAPL"   → "AAPL"
    "FAKE"   → None
    """
    entry = SYMBOL_REGISTRY.get(ticker.upper())
    return entry["yahoo_symbol"] if entry else None


def canonical_ticker(yahoo_symbol: str) -> Optional[str]:
    """
    Convert Yahoo symbol → canonical ticker.

    "TCS.NS"  → "TCS"
    "AAPL"    → "AAPL"
    """
    return _REVERSE_MAP.get(yahoo_symbol.upper())


def get_all_tickers() -> List[str]:
    """Return all supported canonical tickers."""
    return list(SYMBOL_REGISTRY.keys())


def get_company_meta(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Return static metadata for a ticker.
    Returns None for unknown tickers.
    """
    return SYMBOL_REGISTRY.get(ticker.upper())


def is_supported(ticker: str) -> bool:
    """Return True if ticker is in the registry."""
    return ticker.upper() in SYMBOL_REGISTRY


def get_fallback_avg_volume(ticker: str) -> int:
    """Return the registry fallback average volume (used when provider doesn't supply it)."""
    meta = SYMBOL_REGISTRY.get(ticker.upper(), {})
    return meta.get("avg_volume", 1_000_000)
