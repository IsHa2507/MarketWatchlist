from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class StockQuote(BaseModel):
    ticker: str
    company_name: str
    price: float
    price_change: float
    price_change_percent: float
    volume: float
    average_volume: float
    volatility: float
    sentiment_score: float
    sentiment_label: str
    last_updated: datetime
    data_confidence: str = "HIGH"


class StockHistory(BaseModel):
    ticker: str
    data_points: List[Dict[str, Any]]


class MarketEventResponse(BaseModel):
    id: int
    ticker: str
    event_type: str
    title: str
    description: Optional[str] = None
    sentiment: str
    impact_score: float
    source: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class StockSearchResult(BaseModel):
    ticker: str
    company_name: str
    price: float
    price_change_percent: float
    sector: Optional[str] = None


class AttentionComponents(BaseModel):
    price: float
    volume: float
    sentiment: float
    volatility: float
    technical: float


class AttentionScore(BaseModel):
    ticker: str
    company_name: str
    attention_score: float
    classification: str  # NORMAL, WORTH_WATCHING, IMPORTANT, CRITICAL
    components: AttentionComponents
    price_change_percent: float
    volume_multiplier: float
    sentiment_change: str
    current_price: float
    checkpoint_price: Optional[float] = None
    explanation: str
    key_reasons: List[str]


class DashboardResponse(BaseModel):
    needs_attention: List[AttentionScore]
    worth_watching: List[AttentionScore]
    normal: List[AttentionScore]
    summary: Dict[str, Any]
    last_checked: Optional[datetime] = None
    is_first_visit: bool = False


class ChangeResponse(BaseModel):
    ticker: str
    company_name: str
    price_change_percent: float
    volume_change_percent: float
    sentiment_change: str
    attention_score: float
    classification: str
    since: Optional[datetime] = None
