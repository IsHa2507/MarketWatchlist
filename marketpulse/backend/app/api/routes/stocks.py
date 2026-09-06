from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.user import User
from app.models.market import MarketEvent
from app.services.market_data import MarketDataService
from app.api.deps import get_current_user

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/search")
def search_stocks(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = MarketDataService(db)
    results = svc.search_stocks(q)
    return {"results": results, "total": len(results)}


@router.get("/{ticker}")
def get_stock(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = MarketDataService(db)
    stock = svc.get_stock(ticker.upper())
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock '{ticker}' not found")
    return stock


@router.get("/{ticker}/history")
def get_stock_history(
    ticker: str,
    days: int = Query(default=30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = MarketDataService(db)
    history = svc.get_history(ticker.upper(), days)
    if not history:
        raise HTTPException(status_code=404, detail=f"No history found for '{ticker}'")
    return {
        "ticker": ticker.upper(),
        "days": days,
        "data_points": history,
        "data_confidence": "MEDIUM",
        "note": "Market data may be delayed depending on source.",
    }


@router.get("/{ticker}/events")
def get_stock_events(
    ticker: str,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    events = (
        db.query(MarketEvent)
        .filter(MarketEvent.ticker == ticker.upper())
        .order_by(MarketEvent.timestamp.desc())
        .limit(limit)
        .all()
    )

    # Return seeded demo events if no events in DB
    if not events:
        events = _get_demo_events(ticker.upper())
        return {"ticker": ticker.upper(), "events": events, "demo": True}

    return {
        "ticker": ticker.upper(),
        "events": [
            {
                "id": e.id,
                "ticker": e.ticker,
                "event_type": e.event_type,
                "title": e.title,
                "description": e.description,
                "sentiment": e.sentiment,
                "impact_score": e.impact_score,
                "source": e.source,
                "timestamp": e.timestamp,
            }
            for e in events
        ],
        "demo": False,
    }


def _get_demo_events(ticker: str) -> list:
    """Deterministic demo events per ticker."""
    from datetime import datetime, timedelta

    events_map = {
        "TCS": [
            {
                "id": 1, "ticker": "TCS", "event_type": "earnings",
                "title": "Q4 Results Miss Estimates",
                "description": "TCS reported Q4 revenue below analyst estimates, citing slower demand from key banking clients in North America.",
                "sentiment": "negative", "impact_score": 78.0,
                "source": "Company Filing", "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            },
            {
                "id": 2, "ticker": "TCS", "event_type": "analyst",
                "title": "Analyst Downgrades Outlook",
                "description": "A major brokerage revised its outlook, citing macroeconomic headwinds in IT spending.",
                "sentiment": "negative", "impact_score": 62.0,
                "source": "Analyst Report", "timestamp": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
            },
        ],
        "NVDA": [
            {
                "id": 3, "ticker": "NVDA", "event_type": "earnings",
                "title": "Record Data Center Revenue",
                "description": "NVIDIA reported record data center revenue driven by strong AI chip demand. Revenue exceeded consensus estimates by 18%.",
                "sentiment": "positive", "impact_score": 89.0,
                "source": "Earnings Release", "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            },
            {
                "id": 4, "ticker": "NVDA", "event_type": "news",
                "title": "New AI Partnership Announced",
                "description": "NVIDIA announced a strategic partnership to deploy AI infrastructure at scale.",
                "sentiment": "positive", "impact_score": 71.0,
                "source": "Press Release", "timestamp": (datetime.utcnow() - timedelta(hours=4)).isoformat(),
            },
        ],
        "RELIANCE": [
            {
                "id": 5, "ticker": "RELIANCE", "event_type": "news",
                "title": "Jio Platforms Subscriber Growth",
                "description": "Reliance Jio added 8.2 million subscribers in the quarter, beating growth forecasts.",
                "sentiment": "positive", "impact_score": 65.0,
                "source": "Company Update", "timestamp": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
            },
        ],
    }

    defaults = [
        {
            "id": 99, "ticker": ticker, "event_type": "news",
            "title": "No significant news events",
            "description": "No major events have been recorded for this stock in the current period.",
            "sentiment": "neutral", "impact_score": 5.0,
            "source": "MarketPulse", "timestamp": datetime.utcnow().isoformat(),
        }
    ]

    return events_map.get(ticker, defaults)
