"""
DashboardService
Orchestrates: watchlist → market data → checkpoints → changes → scoring → ranking

Critical invariant
------------------
Checkpoints are READ before the dashboard is built, then UPDATED after.
Never update a checkpoint before the comparison is complete.

Partial failure policy
----------------------
If one ticker fails (bad data, provider error, etc.), the rest of the
dashboard is still returned. Failed tickers appear in `errors` list.
The dashboard NEVER returns a 500 because one stock had a problem.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist, WatchlistStock
from app.services.market_data import MarketDataService
from app.services.change_detection import ChangeDetectionService
from app.services.attention_scoring import AttentionScoringService
from app.services.explanation import ExplanationService

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.market = MarketDataService(db)
        self.change_detector = ChangeDetectionService(db)
        self.scorer = AttentionScoringService()
        self.explainer = ExplanationService()

    def get_dashboard(
        self, user_id: int, watchlist_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build the full dashboard response.

        CRITICAL ORDER:
          1. Read previous checkpoints
          2. Fetch current market data
          3. Calculate changes
          4. Score + explain
          5. Update checkpoints

        Partial failure: if a ticker fails at any step, it is moved to
        the `errors` list. All other tickers still appear normally.
        """
        # ── Resolve watchlist ───────────────────────────────────────────
        watchlist = self._resolve_watchlist(user_id, watchlist_id)
        if not watchlist:
            return self._empty_dashboard()

        tickers = [s.ticker for s in watchlist.stocks]
        if not tickers:
            return self._empty_dashboard()

        # ── Step 1–4: Read checkpoints, fetch data, compare, score ──────
        all_results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        oldest_checkpoint: Optional[datetime] = None

        for ticker in tickers:
            try:
                result, cp_time = self._process_ticker(user_id, ticker)
                if result is None:
                    # Provider returned no data — treat as soft error
                    errors.append({
                        "ticker": ticker,
                        "error": "No market data available",
                        "error_type": "NO_DATA",
                    })
                    continue

                all_results.append(result)

                if cp_time and (
                    oldest_checkpoint is None or cp_time < oldest_checkpoint
                ):
                    oldest_checkpoint = cp_time

            except Exception as exc:
                logger.error(
                    "Dashboard: failed to process ticker '%s' for user %d: %s",
                    ticker, user_id, exc, exc_info=True,
                )
                errors.append({
                    "ticker": ticker,
                    "error": str(exc),
                    "error_type": "PROCESSING_ERROR",
                })
                # Continue — do NOT re-raise; other tickers must still work

        # ── Step 4: Sort by attention score descending ──────────────────
        all_results.sort(key=lambda x: x["attention_score"], reverse=True)

        # ── Categorise ─────────────────────────────────────────────────
        needs_attention = [
            r for r in all_results
            if r["classification"] in ("CRITICAL", "IMPORTANT")
        ]
        worth_watching = [
            r for r in all_results
            if r["classification"] == "WORTH_WATCHING"
        ]
        normal = [
            r for r in all_results
            if r["classification"] == "NORMAL"
        ]

        # ── Step 5: NOW update checkpoints (after comparison) ──────────
        for ticker in tickers:
            # Only update checkpoint for tickers that succeeded
            succeeded = any(r["ticker"] == ticker for r in all_results)
            if not succeeded:
                continue
            try:
                stock_data = self.market.get_stock(ticker)
                if stock_data:
                    self.change_detector.save_checkpoint(user_id, ticker, stock_data)
            except Exception as exc:
                logger.warning(
                    "Dashboard: checkpoint update failed for '%s': %s", ticker, exc
                )
                # Non-fatal — checkpoint will be updated next visit

        # ── Build response ──────────────────────────────────────────────
        days_away: Optional[int] = None
        if oldest_checkpoint:
            delta = datetime.utcnow() - oldest_checkpoint
            days_away = delta.days

        return {
            "needs_attention": needs_attention,
            "worth_watching": worth_watching,
            "normal": normal,
            "errors": errors,
            "partial_results": len(errors) > 0,
            "summary": {
                "total": len(all_results),
                "needs_attention_count": len(needs_attention),
                "worth_watching_count": len(worth_watching),
                "normal_count": len(normal),
                "error_count": len(errors),
                "days_away": days_away,
                "watchlist_name": watchlist.name,
                "watchlist_id": watchlist.id,
            },
            "last_checked": oldest_checkpoint,
            "is_first_visit": all(r.get("is_first_visit") for r in all_results)
            if all_results else True,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_ticker(
        self, user_id: int, ticker: str
    ) -> tuple[Optional[Dict[str, Any]], Optional[datetime]]:
        """
        Run the full pipeline for a single ticker.

        Returns (result_dict, checkpoint_datetime) or (None, None) if
        no market data is available.

        Raises on unexpected errors so the caller can catch and isolate.
        """
        change_data = self.change_detector.detect_changes(user_id, ticker)
        if not change_data:
            return None, None

        # Score
        score_data = self.scorer.calculate(change_data)

        # Explain
        explanation = self.explainer.generate(change_data, score_data)

        # Extract checkpoint time for "since you last checked" banner
        cp_time: Optional[datetime] = change_data.get("since")

        # Pull freshness from the stock data dict if present
        stock_data = change_data.get("stock_data", {})
        freshness = stock_data.get("freshness")

        result = {
            "ticker": ticker,
            "company_name": change_data.get("company_name", ticker),
            "current_price": change_data.get("current_price", 0.0),
            "checkpoint_price": change_data.get("checkpoint_price"),
            "price_change_percent": change_data.get("price_change_pct", 0.0),
            "volume_multiplier": change_data.get("volume_multiplier", 1.0),
            "sentiment_change": change_data.get("sentiment_change", "Unavailable"),
            "sentiment_label": change_data.get("sentiment_label", "Unavailable"),
            "attention_score": score_data["attention_score"],
            "classification": score_data["classification"],
            "components": score_data["components"],
            "effective_weights": score_data.get("effective_weights"),
            "key_reasons": score_data["key_reasons"],
            "explanation": explanation,
            "since": cp_time,
            "is_first_visit": change_data.get("is_first_visit", True),
            "stock_data": stock_data,
            "freshness": freshness,
            "data_source": stock_data.get("data_source", "Demo"),
            "demo_mode": stock_data.get("demo_mode", True),
            # Phase 2: sentiment provenance
            "sentiment_source": change_data.get("sentiment_source", "Unavailable"),
            "sentiment_timestamp": change_data.get("sentiment_timestamp"),
            "sentiment_article_count": change_data.get("sentiment_article_count", 0),
            "sentiment_confidence": change_data.get("sentiment_confidence", 0.0),
            "sentiment_unavailable": change_data.get("sentiment_unavailable", True),
            # Phase 2: technical indicator metadata
            "technical_method": score_data.get("technical_method", "price_volume_fallback"),
            "rsi14": score_data.get("rsi14"),
            "sma20": score_data.get("sma20"),
        }

        return result, cp_time

    def _resolve_watchlist(
        self, user_id: int, watchlist_id: Optional[int]
    ) -> Optional[Watchlist]:
        """Find the target watchlist — specific or first available."""
        if watchlist_id:
            return (
                self.db.query(Watchlist)
                .filter(
                    Watchlist.id == watchlist_id,
                    Watchlist.user_id == user_id,
                )
                .first()
            )
        return (
            self.db.query(Watchlist)
            .filter(Watchlist.user_id == user_id)
            .order_by(Watchlist.created_at.asc())
            .first()
        )

    def _empty_dashboard(self) -> Dict[str, Any]:
        return {
            "needs_attention": [],
            "worth_watching": [],
            "normal": [],
            "errors": [],
            "partial_results": False,
            "summary": {
                "total": 0,
                "needs_attention_count": 0,
                "worth_watching_count": 0,
                "normal_count": 0,
                "error_count": 0,
                "days_away": None,
                "watchlist_name": None,
                "watchlist_id": None,
            },
            "last_checked": None,
            "is_first_visit": True,
        }
