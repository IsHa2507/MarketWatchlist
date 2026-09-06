"""
NewsService
===========
Fetches news headlines for a stock ticker from free RSS sources.

Design principles
-----------------
- Zero paid API keys required.
- Never crashes the dashboard — always returns [] on any failure.
- Results are cached in the SentimentCache table (TTL: NEWS_CACHE_TTL_SECONDS).
- Network calls are isolated to this service; all other code receives plain dicts.
- Uses feedparser (pure-Python RSS/Atom parser, no C extensions required).

RSS sources used (in priority order)
--------------------------------------
1. Yahoo Finance RSS headline feed  (ticker-specific, most relevant)
2. Google News RSS                  (company-name search, broad coverage)

The service intentionally avoids scraping article bodies — headlines only.
This keeps latency low and avoids ToS issues.

Sample returned headline dict
------------------------------
{
    "title": "TCS Q4 profit rises 9%, misses Street estimates",
    "url": "https://...",
    "published": "2024-04-17T10:30:00",
    "source": "Yahoo Finance RSS",
}
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote as url_quote

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.market import SentimentCache
from app.providers.symbol_map import get_company_meta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RSS feed URL templates
# ---------------------------------------------------------------------------

def _yahoo_rss_url(yahoo_symbol: str) -> str:
    """Yahoo Finance RSS headline feed for a specific symbol."""
    return f"https://finance.yahoo.com/rss/headline?s={yahoo_symbol}"


def _google_news_rss_url(company_name: str, locale: str = "en-US") -> str:
    """Google News RSS search feed for a company name."""
    query = url_quote(f'"{company_name}" stock')
    return f"https://news.google.com/rss/search?q={query}&hl={locale}&gl=US&ceid=US:en"


def _google_news_rss_url_in(company_name: str) -> str:
    """Google News RSS search feed — Indian locale for NSE stocks."""
    query = url_quote(f'"{company_name}"')
    return f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"


# ---------------------------------------------------------------------------
# Headline normalisation
# ---------------------------------------------------------------------------

def _parse_feed_entries(entries: List[Any], source: str, max_articles: int) -> List[Dict[str, str]]:
    """Convert feedparser entries into normalised headline dicts."""
    results = []
    for entry in entries[:max_articles]:
        try:
            title = entry.get("title", "").strip()
            if not title:
                continue
            url = entry.get("link", "")
            published_struct = entry.get("published_parsed")
            if published_struct:
                try:
                    from time import mktime
                    published = datetime.fromtimestamp(mktime(published_struct)).isoformat()
                except Exception:
                    published = ""
            else:
                published = entry.get("published", "")
            results.append({
                "title": title,
                "url": url,
                "published": published,
                "source": source,
            })
        except Exception:
            continue
    return results


class NewsService:
    """
    Fetches and caches news headlines for market tickers.

    Caching strategy
    ----------------
    Headlines are stored as JSON in the SentimentCache table.
    A cached entry younger than NEWS_CACHE_TTL_SECONDS is returned directly
    without making any network request.

    If news is unavailable (all sources fail, empty feeds, network error),
    returns [] and marks the result as unavailable rather than silently
    returning stale or fabricated data.
    """

    def __init__(self, db: Session):
        self.db = db
        self._ttl = getattr(settings, "NEWS_CACHE_TTL_SECONDS", 3600)
        self._max_articles = getattr(settings, "NEWS_MAX_ARTICLES", 10)
        self._enabled = getattr(settings, "NEWS_ENABLED", True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_headlines(self, ticker: str) -> List[Dict[str, str]]:
        """
        Return up to NEWS_MAX_ARTICLES headlines for ticker.
        Returns [] if news is disabled, unavailable, or all fetches fail.
        Never raises.
        """
        if not self._enabled:
            return []

        # 1. Check cache
        cached = self._get_cached_headlines(ticker)
        if cached is not None:
            return cached

        # 2. Fetch live
        headlines = self._fetch_headlines(ticker)

        # 3. Store to cache (even empty — to avoid hammering on failures)
        self._store_cache(ticker, headlines)

        return headlines

    # ------------------------------------------------------------------
    # Internal: fetch from RSS feeds
    # ------------------------------------------------------------------

    def _fetch_headlines(self, ticker: str) -> List[Dict[str, str]]:
        """
        Try each RSS source in order. Return on first non-empty result.
        Return [] if all sources fail or return empty.
        """
        try:
            import feedparser  # noqa: F401 — import here so module works without feedparser
        except ImportError:
            logger.warning("feedparser not installed — news unavailable")
            return []

        meta = get_company_meta(ticker)
        if not meta:
            return []

        yahoo_symbol = meta["yahoo_symbol"]
        company_name = meta["name"]
        currency = meta.get("currency", "USD")

        sources = [
            ("Yahoo Finance RSS", _yahoo_rss_url(yahoo_symbol)),
            # Indian stocks get IN-locale Google News first
            *([("Google News IN", _google_news_rss_url_in(company_name))]
              if currency == "INR" else []),
            ("Google News", _google_news_rss_url(company_name)),
        ]

        for source_name, url in sources:
            try:
                headlines = self._fetch_rss(url, source_name)
                if headlines:
                    logger.info(
                        "NewsService: fetched %d headlines for '%s' from %s",
                        len(headlines), ticker, source_name,
                    )
                    return headlines
            except Exception as exc:
                logger.debug("NewsService: %s failed for '%s': %s", source_name, ticker, exc)
                continue

        logger.info("NewsService: no headlines found for '%s'", ticker)
        return []

    def _fetch_rss(self, url: str, source_name: str) -> List[Dict[str, str]]:
        """
        Fetch and parse a single RSS URL.
        Returns [] on any failure.
        Timeout: 5 seconds.
        """
        import feedparser

        # feedparser handles the HTTP request internally; we wrap in try/except
        try:
            feed = feedparser.parse(url, request_headers={
                "User-Agent": "MarketPulse/2.0 (https://github.com/marketpulse)",
            })
            if feed.get("bozo") and not feed.entries:
                # bozo=True means parsing error AND no entries — skip
                return []
            return _parse_feed_entries(feed.entries, source_name, self._max_articles)
        except Exception as exc:
            logger.debug("NewsService._fetch_rss failed for %s: %s", url, exc)
            return []

    # ------------------------------------------------------------------
    # Cache read/write
    # ------------------------------------------------------------------

    def _get_cached_headlines(self, ticker: str) -> Optional[List[Dict[str, str]]]:
        """
        Return cached headlines if younger than TTL.
        Returns None if no valid cache entry exists.
        """
        cutoff = datetime.utcnow() - timedelta(seconds=self._ttl)
        row = (
            self.db.query(SentimentCache)
            .filter(
                SentimentCache.ticker == ticker,
                SentimentCache.fetched_at >= cutoff,
            )
            .order_by(SentimentCache.fetched_at.desc())
            .first()
        )
        if row is None:
            return None

        if row.headlines_json:
            try:
                return json.loads(row.headlines_json)
            except (json.JSONDecodeError, TypeError):
                return None

        # Row exists but has no headlines — was an empty result cache
        return []

    def _store_cache(self, ticker: str, headlines: List[Dict[str, str]]) -> None:
        """
        Store headlines in SentimentCache.
        Score/label will be filled in later by SentimentService.
        If DB write fails, log and continue — never crash.
        """
        try:
            row = SentimentCache(
                ticker=ticker,
                score=None,
                label="Unavailable",
                confidence=0.0,
                article_count=len(headlines),
                source="Unavailable",
                headlines_json=json.dumps(headlines) if headlines else None,
                unavailable=len(headlines) == 0,
                fetched_at=datetime.utcnow(),
            )
            self.db.add(row)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.warning("NewsService: failed to store cache for '%s': %s", ticker, exc)

    def update_cache_sentiment(
        self,
        ticker: str,
        score: float,
        label: str,
        confidence: float,
        source: str,
    ) -> None:
        """
        Update the most recent SentimentCache row for ticker with computed
        sentiment results. Called by SentimentService after scoring.
        """
        try:
            row = (
                self.db.query(SentimentCache)
                .filter(SentimentCache.ticker == ticker)
                .order_by(SentimentCache.fetched_at.desc())
                .first()
            )
            if row:
                row.score = score
                row.label = label
                row.confidence = confidence
                row.source = source
                row.unavailable = False
                self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.warning(
                "NewsService: failed to update sentiment cache for '%s': %s", ticker, exc
            )
