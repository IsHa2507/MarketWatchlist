"""
ChangeDetectionService
Compares current market state against the user's last checkpoint.
"""
from datetime import datetime
from typing import Dict, Optional, Any

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
        Calculate the change for a ticker since user's last checkpoint.
        Returns structured change data.
        """
        stock = self.market.get_stock(ticker)
        if not stock:
            return {}

        checkpoint = self.get_checkpoint(user_id, ticker)
        current_price = stock["price"]
        current_volume = stock["volume"]
        current_volatility = stock["volatility"]
        current_sentiment = stock["sentiment_score"]

        if checkpoint:
            cp_price = checkpoint.price
            cp_volume = checkpoint.volume
            cp_volatility = checkpoint.volatility
            cp_sentiment = checkpoint.sentiment_score

            price_change_pct = (
                (current_price - cp_price) / cp_price * 100
                if cp_price > 0
                else 0.0
            )
            volume_change_pct = (
                (current_volume - cp_volume) / cp_volume * 100
                if cp_volume > 0
                else 0.0
            )
            volatility_change_pct = (
                (current_volatility - cp_volatility) / cp_volatility * 100
                if cp_volatility > 0
                else 0.0
            )
            sentiment_change = self._classify_sentiment_change(cp_sentiment, current_sentiment)
            is_first_visit = False
            since = checkpoint.checked_at
        else:
            # No checkpoint yet — use base price as reference
            price_change_pct = stock["price_change_percent"]
            volume_change_pct = 0.0
            volatility_change_pct = 0.0
            sentiment_change = "No prior data"
            is_first_visit = True
            since = None

        avg_volume = stock["average_volume"]
        volume_multiplier = current_volume / avg_volume if avg_volume > 0 else 1.0

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
            "current_sentiment": current_sentiment,
            "sentiment_label": stock["sentiment_label"],
            "sentiment_change": sentiment_change,
            "is_first_visit": is_first_visit,
            "since": since,
            "stock_data": stock,
        }

    def save_checkpoint(self, user_id: int, ticker: str, stock_data: Dict[str, Any]):
        """Save or update the user checkpoint for a ticker."""
        existing = self.get_checkpoint(user_id, ticker)

        if existing:
            existing.price = stock_data["price"]
            existing.volume = stock_data["volume"]
            existing.volatility = stock_data["volatility"]
            existing.sentiment_score = stock_data["sentiment_score"]
            existing.checked_at = datetime.utcnow()
        else:
            checkpoint = UserCheckpoint(
                user_id=user_id,
                ticker=ticker,
                price=stock_data["price"],
                volume=stock_data["volume"],
                volatility=stock_data["volatility"],
                sentiment_score=stock_data["sentiment_score"],
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
