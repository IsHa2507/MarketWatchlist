from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistStock
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistResponse,
    AddStockRequest,
)
from app.api.deps import get_optional_user        # all routes use optional auth
from app.providers.symbol_map import is_supported

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("", response_model=List[WatchlistResponse])
def list_watchlists(
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Watchlist)
        .filter(Watchlist.user_id == current_user.id)
        .order_by(Watchlist.created_at.asc())
        .all()
    )


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def create_watchlist(
    body: WatchlistCreate,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    wl = Watchlist(user_id=current_user.id, name=body.name)
    db.add(wl)
    db.commit()
    db.refresh(wl)
    return wl


@router.get("/{watchlist_id}", response_model=WatchlistResponse)
def get_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    wl = db.query(Watchlist).filter(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == current_user.id,
    ).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return wl


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist(
    watchlist_id: int,
    body: WatchlistUpdate,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    wl = db.query(Watchlist).filter(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == current_user.id,
    ).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    wl.name = body.name
    wl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(wl)
    return wl


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    wl = db.query(Watchlist).filter(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == current_user.id,
    ).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    db.delete(wl)
    db.commit()


@router.post(
    "/{watchlist_id}/stocks",
    response_model=WatchlistResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_stock(
    watchlist_id: int,
    body: AddStockRequest,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    wl = db.query(Watchlist).filter(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == current_user.id,
    ).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    ticker = body.ticker.upper().strip()

    if not is_supported(ticker):
        raise HTTPException(
            status_code=400,
            detail=f"Ticker '{ticker}' is not supported. Use the search endpoint to find valid tickers.",
        )

    existing = db.query(WatchlistStock).filter(
        WatchlistStock.watchlist_id == watchlist_id,
        WatchlistStock.ticker == ticker,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"{ticker} is already in this watchlist")

    stock = WatchlistStock(watchlist_id=watchlist_id, ticker=ticker)
    db.add(stock)
    wl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(wl)
    return wl


@router.delete("/{watchlist_id}/stocks/{ticker}", response_model=WatchlistResponse)
def remove_stock(
    watchlist_id: int,
    ticker: str,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    wl = db.query(Watchlist).filter(
        Watchlist.id == watchlist_id,
        Watchlist.user_id == current_user.id,
    ).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    ticker = ticker.upper()
    stock = db.query(WatchlistStock).filter(
        WatchlistStock.watchlist_id == watchlist_id,
        WatchlistStock.ticker == ticker,
    ).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"{ticker} not found in this watchlist")

    db.delete(stock)
    wl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(wl)
    return wl
