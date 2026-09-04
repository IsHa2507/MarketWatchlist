from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text

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
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


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
