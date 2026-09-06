"""
ChangeDetectionService
Compares current market state against the user's last checkpoint.
Phase 2: also fetches historical closes for RSI-14 calculation,
and threads sentiment_unavailable flag through to the scorer.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.models.checkpoint import UserCheckpoint
from app.services.market_data import MarketDataService


class ChangeDetectionService:
    def __init__(self, db: Session):
        self.db = db
        self.market = MarketDataService(db)

    def get_checkpoint(self, user_id: int, ticker: str) -> Optional[UserCheckpoint]:
        return (
            self.db.query(UserCheckpoint)
            .filter(
                UserCheckpoint.user_id == user_id,
                UserCheckpoint.ticker == ticker,
            )
            .order_by(UserCheckpoint.checked_at.desc())
            .first()
        )

    def detect_changes(self, user_id: int, ticker: str) -> Dict[str, Any]:
        """
        Calculate changes for a ticker since user's last checkpoint.
        Includes historical closes for RSI-14 and sentiment provenance.
        """
        stock = self.market.get_stock(ticker)
        if not stock:
            return {}

        checkpoint = self.get_checkpoint(user_id, ticker)
        current_price = stock["price"]
        current_volume = stock["volume"]
        current_volatility = stock["volatility"]

        # sentiment_score may be None (unavailable)
        current_sentiment = stock.get("sentiment_score")
        sentiment_unavailable = stock.get("sentiment_unavailable", current_sentiment is None)

        if checkpoint:
            cp_price = checkpoint.price
            cp_volume = checkpoint.volume
            cp_volatility = checkpoint.volatility
            cp_sentiment = checkpoint.sentiment_score

            price_change_pct = (
                (current_price - cp_price) / cp_price * 100
                if cp_price > 0 else 0.0
            )
            volume_change_pct = (
                (current_volume - cp_volume) / cp_volume * 100
                if cp_volume > 0 else 0.0
            )
            volatility_change_pct = (
                (current_volatility - cp_volatility) / cp_volatility * 100
                if cp_volatility > 0 else 0.0
            )
            # Only classify sentiment change if both sides have real scores
            if sentiment_unavailable or cp_sentiment is None:
                sentiment_change = "Unavailable"
            else:
                sentiment_change = self._classify_sentiment_change(
                    cp_sentiment, current_sentiment
                )
            is_first_visit = False
            since = checkpoint.checked_at
        else:
            price_change_pct = stock["price_change_percent"]
            volume_change_pct = 0.0
            volatility_change_pct = 0.0
            sentiment_change = "No prior data"
            is_first_visit = True
            since = None

        avg_volume = stock["average_volume"]
        volume_multiplier = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Fetch historical closes for RSI-14 + SMA-20 (non-blocking; falls back gracefully)
        closes = self._get_closes(ticker)

        return {
            "ticker": ticker,
            "company_name": stock["company_name"],
            "current_price": current_price,
            "checkpoint_price": checkpoint.price if checkpoint else stock.get("base_price", current_price),
            "price_change_pct": round(price_change_pct, 2),
            "volume_multiplier": round(volume_multiplier, 2),
            "volume_change_pct": round(volume_change_pct, 2),
            "current_volatility": current_volatility,
            "volatility_change_pct": round(volatility_change_pct, 2),
            "current_sentiment": current_sentiment,           # None if unavailable
            "sentiment_label": stock.get("sentiment_label", "Unavailable"),
            "sentiment_change": sentiment_change,
            "sentiment_unavailable": sentiment_unavailable,
            "sentiment_source": stock.get("sentiment_source", "Unavailable"),
            "sentiment_timestamp": stock.get("sentiment_timestamp"),
            "sentiment_article_count": stock.get("sentiment_article_count", 0),
            "sentiment_confidence": stock.get("sentiment_confidence", 0.0),
            "is_first_visit": is_first_visit,
            "since": since,
            "stock_data": stock,
            # For RSI-14 + SMA-20
            "closes": closes,
        }

    def _get_closes(self, ticker: str) -> List[float]:
        """
        Fetch last 25 daily closing prices for RSI-14 + SMA-20.
        Returns [] on any failure — caller handles gracefully.
        Need 25 to have 20 for SMA and 15 for RSI with some buffer.
        """
        try:
            history = self.market.get_history(ticker, days=25)
            if not history:
                return []
            return [float(h["close"]) for h in history if h.get("close")]
        except Exception:
            return []

    def save_checkpoint(self, user_id: int, ticker: str, stock_data: Dict[str, Any]):
        """Save or update the user checkpoint for a ticker."""
        existing = self.get_checkpoint(user_id, ticker)
        # Store 0.0 in DB when sentiment is unavailable to maintain schema compatibility
        sentiment_db = stock_data.get("sentiment_score") or 0.0

        if existing:
            existing.price = stock_data["price"]
            existing.volume = stock_data["volume"]
            existing.volatility = stock_data["volatility"]
            existing.sentiment_score = sentiment_db
            existing.checked_at = datetime.utcnow()
        else:
            checkpoint = UserCheckpoint(
                user_id=user_id,
                ticker=ticker,
                price=stock_data["price"],
                volume=stock_data["volume"],
                volatility=stock_data["volatility"],
                sentiment_score=sentiment_db,
                checked_at=datetime.utcnow(),
            )
            self.db.add(checkpoint)

        self.db.commit()

    def _classify_sentiment_change(self, old: float, new: float) -> str:
        def label(score: float) -> str:
            if score > 0.3:
                return "Positive"
            elif score < -0.3:
                return "Negative"
            else:
                return "Neutral"

        old_label = label(old)
        new_label = label(new)
        if old_label == new_label:
            return new_label
        return f"{old_label} → {new_label}"
