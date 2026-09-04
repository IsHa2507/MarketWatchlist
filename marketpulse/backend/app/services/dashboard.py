"""
DashboardService
Orchestrates: watchlist → market data → checkpoints → changes → scoring → ranking
"""
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist, WatchlistStock
from app.services.market_data import MarketDataService
from app.services.change_detection import ChangeDetectionService
from app.services.attention_scoring import AttentionScoringService
from app.services.explanation import ExplanationService


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.market = MarketDataService(db)
        self.change_detector = ChangeDetectionService(db)
        self.scorer = AttentionScoringService()
        self.explainer = ExplanationService()

    def get_dashboard(self, user_id: int, watchlist_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Build the full dashboard response.
        CRITICAL: reads checkpoints BEFORE updating them.
        """
        # Find active watchlist
        if watchlist_id:
            watchlist = (
                self.db.query(Watchlist)
                .filter(Watchlist.id == watchlist_id, Watchlist.user_id == user_id)
                .first()
            )
        else:
            watchlist = (
                self.db.query(Watchlist)
                .filter(Watchlist.user_id == user_id)
                .order_by(Watchlist.created_at.asc())
                .first()
            )

        if not watchlist:
            return self._empty_dashboard()

        tickers = [s.ticker for s in watchlist.stocks]
        if not tickers:
            return self._empty_dashboard()

        # Step 1: Read previous checkpoints (before any update)
        all_results = []
        oldest_checkpoint = None

        for ticker in tickers:
            change_data = self.change_detector.detect_changes(user_id, ticker)
            if not change_data:
                continue

            # Step 2: Calculate attention score
            score_data = self.scorer.calculate(change_data)

            # Step 3: Generate explanation
            explanation = self.explainer.generate(change_data, score_data)

            # Determine last-checked timestamp
            if change_data.get("since") and (
                oldest_checkpoint is None or change_data["since"] < oldest_checkpoint
            ):
                oldest_checkpoint = change_data["since"]

            result = {
                "ticker": ticker,
                "company_name": change_data.get("company_name", ticker),
                "current_price": change_data.get("current_price", 0.0),
                "checkpoint_price": change_data.get("checkpoint_price"),
                "price_change_percent": change_data.get("price_change_pct", 0.0),
                "volume_multiplier": change_data.get("volume_multiplier", 1.0),
                "sentiment_change": change_data.get("sentiment_change", "Neutral"),
                "sentiment_label": change_data.get("sentiment_label", "Neutral"),
                "attention_score": score_data["attention_score"],
                "classification": score_data["classification"],
                "components": score_data["components"],
                "key_reasons": score_data["key_reasons"],
                "explanation": explanation,
                "since": change_data.get("since"),
                "is_first_visit": change_data.get("is_first_visit", True),
                "stock_data": change_data.get("stock_data", {}),
            }
            all_results.append(result)

        # Step 4: Sort by attention score descending
        all_results.sort(key=lambda x: x["attention_score"], reverse=True)

        # Step 5: Categorize
        needs_attention = [r for r in all_results if r["classification"] in ("CRITICAL", "IMPORTANT")]
        worth_watching = [r for r in all_results if r["classification"] == "WORTH_WATCHING"]
        normal = [r for r in all_results if r["classification"] == "NORMAL"]

        # Step 6: NOW update checkpoints
        for ticker in tickers:
            stock_data = self.market.get_stock(ticker)
            if stock_data:
                self.change_detector.save_checkpoint(user_id, ticker, stock_data)

        # Calculate days away
        days_away = None
        if oldest_checkpoint:
            delta = datetime.utcnow() - oldest_checkpoint
            days_away = delta.days

        return {
            "needs_attention": needs_attention,
            "worth_watching": worth_watching,
            "normal": normal,
            "summary": {
                "total": len(all_results),
                "needs_attention_count": len(needs_attention),
                "worth_watching_count": len(worth_watching),
                "normal_count": len(normal),
                "days_away": days_away,
                "watchlist_name": watchlist.name,
                "watchlist_id": watchlist.id,
            },
            "last_checked": oldest_checkpoint,
            "is_first_visit": all(r.get("is_first_visit") for r in all_results),
        }

    def _empty_dashboard(self) -> Dict[str, Any]:
        return {
            "needs_attention": [],
            "worth_watching": [],
            "normal": [],
            "summary": {
                "total": 0,
                "needs_attention_count": 0,
                "worth_watching_count": 0,
                "normal_count": 0,
                "days_away": None,
                "watchlist_name": None,
                "watchlist_id": None,
            },
            "last_checked": None,
            "is_first_visit": True,
        }
