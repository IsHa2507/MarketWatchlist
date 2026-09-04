from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class UserCheckpoint(Base):
    __tablename__ = "user_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    volume = Column(Float, default=0.0)
    volatility = Column(Float, default=0.0)
    sentiment_score = Column(Float, default=0.0)
    checked_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="checkpoints")
