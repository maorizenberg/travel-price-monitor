"""Pydantic models for trip data."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TripData(BaseModel):
    """Structured trip information extracted from a travel package page."""

    url: str = Field(..., description="Source URL of the travel package")
    trip_name: str = Field(..., description="Name or title of the trip")
    
    current_price: Decimal = Field(..., description="Current listed price")
    currency: str = Field(..., description="Currency code (e.g., EUR, USD)")
    price_per_person: Optional[Decimal] = Field(None, description="Price per person if different from total")
    total_price: Optional[Decimal] = Field(None, description="Total price for all travelers")
    
    departure_date: Optional[date] = Field(None, description="Departure date")
    return_date: Optional[date] = Field(None, description="Return date")
    duration_nights: Optional[int] = Field(None, description="Trip duration in nights")
    duration_days: Optional[int] = Field(None, description="Trip duration in days")
    
    hotel_name: Optional[str] = Field(None, description="Hotel name")
    hotel_stars: Optional[int] = Field(None, description="Hotel star rating")
    
    airline: Optional[str] = Field(None, description="Airline name")
    flight_direct: Optional[bool] = Field(None, description="Whether flight is direct")
    
    origin: Optional[str] = Field(None, description="Departure city/airport")
    destination: Optional[str] = Field(None, description="Destination city/airport")
    
    availability: Optional[str] = Field(None, description="Availability status")
    available_spots: Optional[int] = Field(None, description="Number of available spots")
    
    board_type: Optional[str] = Field(None, description="Board type (e.g., All Inclusive, Half Board)")
    room_type: Optional[str] = Field(None, description="Room type")
    
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When the data was scraped")
    
    raw_html: Optional[str] = Field(None, description="Raw HTML for debugging")

    class Config:
        json_encoders = {
            Decimal: str,
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None,
        }


class ScrapeResult(BaseModel):
    """Result of a scrape operation."""
    
    success: bool
    trip_data: Optional[TripData] = None
    error: Optional[str] = None
    html_size: int = 0
    scrape_duration_ms: float = 0