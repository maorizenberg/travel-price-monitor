from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PriceAlert(BaseModel):
    origin: str
    destination: str
    max_price: float
    alert_type: str = "flight"


class PriceRecord(BaseModel):
    origin: str
    destination: str
    price: float
    source: str
    timestamp: datetime
    travel_date: Optional[datetime] = None