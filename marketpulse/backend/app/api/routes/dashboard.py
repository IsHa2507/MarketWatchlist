from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.models.user import User
from app.services.dashboard import DashboardService
from app.api.deps import get_current_user, get_optional_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(
    watchlist_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    svc = DashboardService(db)
    return svc.get_dashboard(current_user.id, watchlist_id)


@router.get("/changes")
def get_changes(
    watchlist_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Returns only the changed stocks (attention + watching)."""
    svc = DashboardService(db)
    result = svc.get_dashboard(current_user.id, watchlist_id)
    return {
        "changes": result["needs_attention"] + result["worth_watching"],
        "last_checked": result["last_checked"],
        "summary": result["summary"],
    }


@router.get("/attention")
def get_attention(
    watchlist_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Returns only stocks needing attention, sorted by score."""
    svc = DashboardService(db)
    result = svc.get_dashboard(current_user.id, watchlist_id)
    return {
        "needs_attention": result["needs_attention"],
        "count": len(result["needs_attention"]),
        "last_checked": result["last_checked"],
    }
