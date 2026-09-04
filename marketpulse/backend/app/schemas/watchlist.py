from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class WatchlistCreate(BaseModel):
    name: str


class WatchlistUpdate(BaseModel):
    name: str


class WatchlistStockResponse(BaseModel):
    id: int
    ticker: str
    added_at: datetime

    class Config:
        from_attributes = True


class WatchlistResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    stocks: List[WatchlistStockResponse] = []

    class Config:
        from_attributes = True


class AddStockRequest(BaseModel):
    ticker: str
