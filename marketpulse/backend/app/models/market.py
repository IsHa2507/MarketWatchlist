from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean

from app.db.database import Base


class StockSnapshot(Base):
    __tablename__ = "stock_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    price_change_percent = Column(Float, default=0.0)
    volume = Column(Float, default=0.0)
    average_volume = Column(Float, default=0.0)
    volatility = Column(Float, default=0.0)
    sentiment_score = Column(Float, default=0.0)  # -1.0 to 1.0
    # Original timestamp kept for backward compat — equals fetched_at for new rows
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # ── Freshness / provenance fields (added in v2) ───────────────────────
    data_source = Column(String, nullable=True, default="Demo")
    data_timestamp = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    freshness_status = Column(String, nullable=True, default="FRESH")
    is_stale = Column(Boolean, nullable=True, default=False)

    # ── Sentiment provenance fields (added in v3 / Phase 2) ──────────────
    # "VADER" | "Keyword" | "Unavailable" | "Demo"
    sentiment_source = Column(String, nullable=True, default="Unavailable")
    # When the sentiment was computed (may differ from fetched_at)
    sentiment_timestamp = Column(DateTime, nullable=True)
    # How many articles contributed to this score
    sentiment_article_count = Column(Integer, nullable=True, default=0)


class MarketEvent(Base):
    __tablename__ = "market_events"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)  # earnings, news, analyst, macro
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    sentiment = Column(String, default="neutral")  # positive, negative, neutral
    impact_score = Column(Float, default=0.0)  # 0-100
    source = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class SentimentCache(Base):
    """
    Caches computed sentiment results per ticker to avoid re-fetching
    news on every dashboard request.

    TTL is controlled by NEWS_CACHE_TTL_SECONDS (default 3600 = 1 hour).
    """
    __tablename__ = "sentiment_cache"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False, index=True)

    # Computed sentiment score (-1.0 to 1.0); None if unavailable
    score = Column(Float, nullable=True)
    # "Positive" | "Negative" | "Neutral" | "Unavailable"
    label = Column(String, nullable=False, default="Unavailable")
    # 0.0 – 1.0 confidence in the score
    confidence = Column(Float, nullable=False, default=0.0)
    # Number of articles used
    article_count = Column(Integer, nullable=False, default=0)
    # "VADER" | "Keyword" | "Unavailable"
    source = Column(String, nullable=False, default="Unavailable")
    # JSON array of {"title": str, "url": str, "published": str} dicts
    headlines_json = Column(Text, nullable=True)
    # Whether news was available at all
    unavailable = Column(Boolean, nullable=False, default=True)

    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)
