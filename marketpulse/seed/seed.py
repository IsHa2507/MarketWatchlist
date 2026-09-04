"""
MarketPulse Seed Script
Populates the database with demo data for the hackathon demo.
Run from project root: python seed/seed.py
Or from backend/: python ../seed/seed.py
"""
import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.db.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistStock
from app.models.market import StockSnapshot, MarketEvent
from app.models.checkpoint import UserCheckpoint
from app.core.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

print("🌱 Seeding MarketPulse demo data...")

# ── Demo user ─────────────────────────────────────────────────────────────────
existing = db.query(User).filter(User.email == "demo@marketpulse.app").first()
if not existing:
    demo_user = User(
        email="demo@marketpulse.app",
        password_hash=hash_password("demo123"),
        full_name="Demo User",
        last_seen_at=datetime.utcnow() - timedelta(days=3),
    )
    db.add(demo_user)
    db.flush()
    print(f"  ✓ Demo user created: demo@marketpulse.app / demo123")
else:
    demo_user = existing
    print(f"  · Demo user already exists")

# ── Watchlist ─────────────────────────────────────────────────────────────────
wl = db.query(Watchlist).filter(Watchlist.user_id == demo_user.id).first()
if not wl:
    wl = Watchlist(user_id=demo_user.id, name="Demo Portfolio")
    db.add(wl)
    db.flush()
    print(f"  ✓ Watchlist created: Demo Portfolio")

    tickers = ["TCS", "NVDA", "RELIANCE", "INFY", "HDFCBANK", "AAPL", "TSLA", "MSFT", "AMZN", "ICICIBANK"]
    for t in tickers:
        ws = WatchlistStock(watchlist_id=wl.id, ticker=t)
        db.add(ws)
    print(f"  ✓ Added {len(tickers)} stocks")

# ── Stock snapshots ───────────────────────────────────────────────────────────
SNAPSHOTS = {
    "TCS":       {"price": 3989.20, "price_change_percent": 0.2,  "volume": 1_250_000, "avg_volume": 1_200_000, "volatility": 0.015, "sentiment_score": 0.05},
    "NVDA":      {"price": 823.10,  "price_change_percent": -0.8, "volume": 15_000_000,"avg_volume": 42_000_000,"volatility": 0.025, "sentiment_score": 0.10},
    "RELIANCE":  {"price": 2874.50, "price_change_percent": 0.5,  "volume": 4_700_000, "avg_volume": 8_500_000, "volatility": 0.012, "sentiment_score": 0.08},
    "INFY":      {"price": 1478.40, "price_change_percent": 0.1,  "volume": 5_100_000, "avg_volume": 5_200_000, "volatility": 0.007, "sentiment_score": 0.01},
    "HDFCBANK":  {"price": 1616.90, "price_change_percent": 0.2,  "volume": 7_000_000, "avg_volume": 7_800_000, "volatility": 0.008, "sentiment_score": 0.03},
    "AAPL":      {"price": 190.80,  "price_change_percent": 0.8,  "volume": 48_000_000,"avg_volume": 55_000_000,"volatility": 0.010, "sentiment_score": 0.09},
    "TSLA":      {"price": 179.60,  "price_change_percent": -0.3, "volume": 88_000_000,"avg_volume": 98_000_000,"volatility": 0.018, "sentiment_score": -0.05},
    "MSFT":      {"price": 413.50,  "price_change_percent": 0.3,  "volume": 21_000_000,"avg_volume": 22_000_000,"volatility": 0.009, "sentiment_score": 0.08},
    "AMZN":      {"price": 181.20,  "price_change_percent": 0.5,  "volume": 35_000_000,"avg_volume": 38_000_000,"volatility": 0.012, "sentiment_score": 0.07},
    "ICICIBANK": {"price": 1120.10, "price_change_percent": 0.3,  "volume": 8_000_000, "avg_volume": 9_200_000, "volatility": 0.010, "sentiment_score": 0.05},
}

# Seed checkpoints to simulate "3 days ago" state
CHECKPOINT_PRICES = {
    "TCS":       3989.20 / (1 - 0.038),  # -3.8% from checkpoint
    "NVDA":      823.10  / (1 + 0.062),  # +6.2% from checkpoint
    "RELIANCE":  2874.50 / (1 + 0.024),  # +2.4% from checkpoint
    "INFY":      1478.40 / (1 + 0.003),  # +0.3% from checkpoint
    "HDFCBANK":  1616.90 / (1 + 0.004),  # +0.4% from checkpoint
    "AAPL":      190.80  / (1 - 0.008),  # -0.8% from checkpoint
    "TSLA":      179.60  / (1 - 0.012),  # -1.2% from checkpoint
    "MSFT":      413.50  / (1 + 0.006),  # +0.6% from checkpoint
    "AMZN":      181.20  / (1 + 0.011),  # +1.1% from checkpoint
    "ICICIBANK": 1120.10 / (1 + 0.018),  # +1.8% from checkpoint
}

three_days_ago = datetime.utcnow() - timedelta(days=3)

for ticker, snap in SNAPSHOTS.items():
    existing_snap = db.query(StockSnapshot).filter(
        StockSnapshot.ticker == ticker
    ).order_by(StockSnapshot.timestamp.desc()).first()

    if not existing_snap:
        ss = StockSnapshot(
            ticker=ticker,
            price=snap["price"],
            price_change_percent=snap["price_change_percent"],
            volume=snap["volume"],
            average_volume=snap["avg_volume"],
            volatility=snap["volatility"],
            sentiment_score=snap["sentiment_score"],
            timestamp=datetime.utcnow(),
        )
        db.add(ss)

    # Checkpoint 3 days ago
    existing_cp = db.query(UserCheckpoint).filter(
        UserCheckpoint.user_id == demo_user.id,
        UserCheckpoint.ticker == ticker,
    ).first()
    if not existing_cp:
        cp = UserCheckpoint(
            user_id=demo_user.id,
            ticker=ticker,
            price=round(CHECKPOINT_PRICES.get(ticker, snap["price"]), 2),
            volume=snap["avg_volume"],
            volatility=snap["volatility"] * 0.75,
            sentiment_score=0.0,
            checked_at=three_days_ago,
        )
        db.add(cp)

print(f"  ✓ Seeded {len(SNAPSHOTS)} stock snapshots & checkpoints")

# ── Market events ─────────────────────────────────────────────────────────────
EVENTS = [
    MarketEvent(ticker="TCS", event_type="earnings", title="Q4 Results Miss Estimates",
        description="TCS reported Q4 revenue below analyst estimates, citing slower demand from key banking clients in North America. Margins contracted by 40bps.",
        sentiment="negative", impact_score=78.0, source="Company Filing", timestamp=datetime.utcnow() - timedelta(hours=2)),
    MarketEvent(ticker="TCS", event_type="analyst", title="Analyst Downgrades Outlook",
        description="A major brokerage revised its outlook to 'Neutral' from 'Outperform', citing macroeconomic headwinds in IT spending across BFSI verticals.",
        sentiment="negative", impact_score=62.0, source="Analyst Report", timestamp=datetime.utcnow() - timedelta(hours=5)),
    MarketEvent(ticker="NVDA", event_type="earnings", title="Record Data Center Revenue",
        description="NVIDIA reported record data center revenue driven by strong AI chip demand. Revenue exceeded consensus estimates by 18%. Blackwell ramp ahead of schedule.",
        sentiment="positive", impact_score=89.0, source="Earnings Release", timestamp=datetime.utcnow() - timedelta(hours=1)),
    MarketEvent(ticker="NVDA", event_type="news", title="New AI Partnership Announced",
        description="NVIDIA announced a strategic partnership with a major cloud provider to deploy AI infrastructure at scale, adding to a strong demand pipeline.",
        sentiment="positive", impact_score=71.0, source="Press Release", timestamp=datetime.utcnow() - timedelta(hours=4)),
    MarketEvent(ticker="RELIANCE", event_type="news", title="Jio Platforms Subscriber Growth",
        description="Reliance Jio added 8.2 million subscribers in the quarter, beating growth forecasts. 5G rollout is now live in 450+ cities.",
        sentiment="positive", impact_score=65.0, source="Company Update", timestamp=datetime.utcnow() - timedelta(hours=3)),
    MarketEvent(ticker="AAPL", event_type="news", title="iPhone 16 Demand Tracking In-Line",
        description="Supply chain checks indicate iPhone 16 demand is tracking broadly in line with the prior cycle, with modest AI feature uptake in developed markets.",
        sentiment="neutral", impact_score=30.0, source="Supply Chain Report", timestamp=datetime.utcnow() - timedelta(hours=8)),
    MarketEvent(ticker="TSLA", event_type="analyst", title="Deliveries Slightly Below Consensus",
        description="Q2 deliveries came in slightly below consensus estimates. Management reiterated full-year guidance while citing macro uncertainty.",
        sentiment="negative", impact_score=42.0, source="Analyst Note", timestamp=datetime.utcnow() - timedelta(hours=6)),
]

existing_events = db.query(MarketEvent).count()
if existing_events == 0:
    for ev in EVENTS:
        db.add(ev)
    print(f"  ✓ Seeded {len(EVENTS)} market events")
else:
    print(f"  · Market events already exist ({existing_events})")

db.commit()
db.close()

print("\n✅ Seed complete!")
print("   Login: demo@marketpulse.app / demo123")
print("   Checkpoints are set to 3 days ago — dashboard will show meaningful changes.")
