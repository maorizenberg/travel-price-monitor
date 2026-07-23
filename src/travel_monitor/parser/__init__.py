"""BeautifulSoup-based HTML parser for travel package pages."""

import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from bs4 import BeautifulSoup, Tag

from travel_monitor.models import TripData

logger = logging.getLogger(__name__)

# Common currency symbols and codes
CURRENCY_PATTERNS = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "CHF": "CHF",
    "EUR": "EUR",
    "USD": "USD",
    "GBP": "GBP",
}


class TripParser:
    """Parses travel package HTML into structured TripData."""

    def parse(self, html: str, url: str = "") -> TripData:
        """Parse HTML content into TripData.
        
        Args:
            html: HTML content to parse
            url: Source URL for the trip
            
        Returns:
            TripData with extracted information
        """
        soup = BeautifulSoup(html, "lxml")
        
        trip_name = self._extract_trip_name(soup)
        price, currency = self._extract_price(soup)
        price_per_person = self._extract_price_per_person(soup)
        departure_date, return_date = self._extract_dates(soup)
        duration_nights, duration_days = self._extract_duration(soup)
        hotel_name, hotel_stars = self._extract_hotel(soup)
        airline, flight_direct = self._extract_flight(soup)
        origin, destination = self._extract_route(soup)
        availability, available_spots = self._extract_availability(soup)
        board_type = self._extract_board_type(soup)
        room_type = self._extract_room_type(soup)
        
        return TripData(
            url=url,
            trip_name=trip_name,
            current_price=price,
            currency=currency,
            price_per_person=price_per_person,
            total_price=price,
            departure_date=departure_date,
            return_date=return_date,
            duration_nights=duration_nights,
            duration_days=duration_days,
            hotel_name=hotel_name,
            hotel_stars=hotel_stars,
            airline=airline,
            flight_direct=flight_direct,
            origin=origin,
            destination=destination,
            availability=availability,
            available_spots=available_spots,
            board_type=board_type,
            room_type=room_type,
            raw_html=html[:1000] if len(html) > 1000 else html,
        )

    def _extract_trip_name(self, soup: BeautifulSoup) -> str:
        """Extract trip name from the page."""
        # Try common selectors
        selectors = [
            "h1.trip-title",
            "h1.package-title",
            "h1.product-title",
            "h1",
            ".trip-header h2",
            ".package-header h2",
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        
        # Fallback to title tag
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)[:100]
        
        return "Unknown Trip"

    def _extract_price(self, soup: BeautifulSoup) -> tuple[Decimal, str]:
        """Extract price and currency."""
        price_selectors = [
            ".price-main",
            ".total-price",
            ".package-price",
            "[data-price]",
            ".price",
            ".amount",
        ]
        
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                price, currency = self._parse_price_text(price_text)
                if price > 0:
                    return price, currency
        
        # Try to find price in any element with price-related class
        for element in soup.find_all(attrs={"class": re.compile(r"price|amount|cost", re.I)}):
            price_text = element.get_text(strip=True)
            price, currency = self._parse_price_text(price_text)
            if price > 0:
                return price, currency
        
        return Decimal("0"), "EUR"

    def _parse_price_text(self, text: str) -> tuple[Decimal, str]:
        """Parse price text into Decimal and currency."""
        if not text:
            return Decimal("0"), "EUR"
        
        # Check for currency symbols
        currency = "EUR"
        for symbol, code in CURRENCY_PATTERNS.items():
            if symbol in text:
                currency = code
                text = text.replace(symbol, "")
                break
        
        # Remove non-numeric characters except . and ,
        cleaned = re.sub(r"[^\d.,]", "", text)
        
        # Handle European format (1.234,56) vs US format (1,234.56)
        if "," in cleaned and "." in cleaned:
            if cleaned.rindex(",") > cleaned.rindex("."):
                # European: 1.234,56 -> 1234.56
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                # US: 1,234.56 -> 1234.56
                cleaned = cleaned.replace(",", "")
        elif "." in cleaned:
            # Could be European thousands (2.499) or US decimal (2.49)
            parts = cleaned.split(".")
            if len(parts[-1]) == 3 and len(parts) > 1:
                # European thousands: 2.499 -> 2499
                cleaned = cleaned.replace(".", "")
            # else: US decimal like 2.49 - keep as is
        elif "," in cleaned:
            # Could be European decimal or US thousands
            parts = cleaned.split(",")
            if len(parts[-1]) == 2:
                # European decimal: 1234,56
                cleaned = cleaned.replace(",", ".")
            else:
                # US thousands: 1,234
                cleaned = cleaned.replace(",", "")
        
        try:
            price = Decimal(cleaned) if cleaned else Decimal("0")
            return price, currency
        except InvalidOperation:
            return Decimal("0"), currency

    def _extract_price_per_person(self, soup: BeautifulSoup) -> Optional[Decimal]:
        """Extract price per person if different from total."""
        ppp_selectors = [
            ".price-per-person",
            ".per-person-price",
            "[data-per-person]",
        ]
        
        for selector in ppp_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                price, _ = self._parse_price_text(price_text)
                if price > 0:
                    return price
        
        return None

    def _extract_dates(self, soup: BeautifulSoup) -> tuple[Optional[date], Optional[date]]:
        """Extract departure and return dates."""
        departure = None
        return_date = None
        
        # Try departure date selectors
        departure_selectors = [
            ".departure-date",
            ".travel-date",
            ".date-departure",
            "[data-departure]",
        ]
        
        for selector in departure_selectors:
            element = soup.select_one(selector)
            if element:
                departure = self._parse_date(element.get_text(strip=True))
                if departure:
                    break
        
        # Try return date selectors
        return_selectors = [
            ".return-date",
            ".date-return",
            "[data-return]",
        ]
        
        for selector in return_selectors:
            element = soup.select_one(selector)
            if element:
                return_date = self._parse_date(element.get_text(strip=True))
                if return_date:
                    break
        
        # Try to find date range in single element
        if not departure:
            date_range_selectors = [
                ".date-range",
                ".travel-dates",
                ".trip-dates",
            ]
            for selector in date_range_selectors:
                element = soup.select_one(selector)
                if element:
                    departure, return_date = self._parse_date_range(element.get_text(strip=True))
                    if departure:
                        break
        
        return departure, return_date

    def _parse_date(self, text: str) -> Optional[date]:
        """Parse a date string."""
        if not text:
            return None
        
        formats = [
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d %B %Y",
            "%d %b %Y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        
        return None

    def _parse_date_range(self, text: str) -> tuple[Optional[date], Optional[date]]:
        """Parse a date range string like '01.06.2025 - 08.06.2025'."""
        # Try common separators
        for separator in [" - ", " to ", " - ", " – ", " — "]:
            if separator in text:
                parts = text.split(separator, 1)
                if len(parts) == 2:
                    departure = self._parse_date(parts[0].strip())
                    return_date = self._parse_date(parts[1].strip())
                    return departure, return_date
        
        return None, None

    def _extract_duration(self, soup: BeautifulSoup) -> tuple[Optional[int], Optional[int]]:
        """Extract trip duration in nights and days."""
        nights = None
        days = None
        
        duration_selectors = [
            ".duration",
            ".trip-duration",
            ".nights",
            "[data-duration]",
        ]
        
        for selector in duration_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                nights, days = self._parse_duration(text)
                if nights or days:
                    break
        
        return nights, days

    def _parse_duration(self, text: str) -> tuple[Optional[int], Optional[int]]:
        """Parse duration text like '7 Nights / 8 Days'."""
        nights = None
        days = None
        
        # Match "X Nights" or "X Nächte"
        nights_match = re.search(r"(\d+)\s*(?:Nights?|Nächte)", text, re.I)
        if nights_match:
            nights = int(nights_match.group(1))
        
        # Match "X Days" or "X Tage"
        days_match = re.search(r"(\d+)\s*(?:Days?|Tage)", text, re.I)
        if days_match:
            days = int(days_match.group(1))
        
        # If only one number found, infer the other
        if nights and not days:
            days = nights + 1
        elif days and not nights:
            nights = days - 1
        
        return nights, days

    def _extract_hotel(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[int]]:
        """Extract hotel name and star rating."""
        hotel_name = None
        hotel_stars = None
        
        name_selectors = [
            ".hotel-name",
            ".hotel-title",
            ".property-name",
            "[data-hotel]",
        ]
        
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                hotel_name = element.get_text(strip=True)
                if hotel_name:
                    break
        
        # Try to find hotel stars
        stars_selectors = [
            ".hotel-stars",
            ".star-rating",
            "[data-stars]",
        ]
        
        for selector in stars_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                stars_match = re.search(r"(\d)", text)
                if stars_match:
                    hotel_stars = int(stars_match.group(1))
                    break
        
        # Try to extract stars from class name (e.g., "stars-5")
        if not hotel_stars:
            for element in soup.find_all(attrs={"class": re.compile(r"stars?-\d", re.I)}):
                classes = " ".join(element.get("class", []))
                stars_match = re.search(r"stars?-(\d)", classes)
                if stars_match:
                    hotel_stars = int(stars_match.group(1))
                    break
        
        return hotel_name, hotel_stars

    def _extract_flight(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[bool]]:
        """Extract airline and whether flight is direct."""
        airline = None
        flight_direct = None
        
        airline_selectors = [
            ".airline-name",
            ".airline",
            ".carrier",
            "[data-airline]",
        ]
        
        for selector in airline_selectors:
            element = soup.select_one(selector)
            if element:
                airline = element.get_text(strip=True)
                if airline:
                    break
        
        # Check for direct flight indicator
        direct_selectors = [
            ".direct-flight",
            ".nonstop",
            ".flight-direct",
        ]
        
        for selector in direct_selectors:
            element = soup.select_one(selector)
            if element:
                flight_direct = True
                break
        
        # Check for stops
        if flight_direct is None:
            stops_selectors = [
                ".stops",
                ".flight-stops",
                ".layover",
            ]
            for selector in stops_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if re.search(r"0\s*(?:Stops?|Stopp)", text, re.I):
                        flight_direct = True
                    elif re.search(r"\d+\s*(?:Stops?|Stopp)", text, re.I):
                        flight_direct = False
                    break
        
        return airline, flight_direct

    def _extract_route(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
        """Extract origin and destination."""
        origin = None
        destination = None
        
        route_selectors = [
            ".route",
            ".flight-route",
            ".departure-destination",
        ]
        
        for selector in route_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                # Try to split by common separators
                for sep in [" → ", " -> ", " - ", " to ", " nach "]:
                    if sep in text:
                        parts = text.split(sep, 1)
                        if len(parts) == 2:
                            origin = parts[0].strip()
                            destination = parts[1].strip()
                            break
                if origin:
                    break
        
        # Try separate selectors
        if not origin:
            origin_selectors = [
                ".departure-city",
                ".origin",
                ".from",
                "[data-origin]",
            ]
            for selector in origin_selectors:
                element = soup.select_one(selector)
                if element:
                    origin = element.get_text(strip=True)
                    if origin:
                        break
        
        if not destination:
            dest_selectors = [
                ".destination-city",
                ".destination",
                ".to",
                "[data-destination]",
            ]
            for selector in dest_selectors:
                element = soup.select_one(selector)
                if element:
                    destination = element.get_text(strip=True)
                    if destination:
                        break
        
        return origin, destination

    def _extract_availability(self, soup: BeautifulSoup) -> tuple[Optional[str], Optional[int]]:
        """Extract availability status and number of spots."""
        availability = None
        available_spots = None
        
        avail_selectors = [
            ".availability",
            ".availability-status",
            ".stock",
            "[data-availability]",
        ]
        
        for selector in avail_selectors:
            element = soup.select_one(selector)
            if element:
                availability = element.get_text(strip=True)
                if availability:
                    break
        
        # Try to find available spots
        spots_selectors = [
            ".available-spots",
            ".spots-left",
            ".remaining",
        ]
        
        for selector in spots_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                spots_match = re.search(r"(\d+)", text)
                if spots_match:
                    available_spots = int(spots_match.group(1))
                    break
        
        return availability, available_spots

    def _extract_board_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract board type (e.g., All Inclusive)."""
        board_selectors = [
            ".board-type",
            ".meal-plan",
            ".board",
            "[data-board]",
        ]
        
        for selector in board_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # Search for common board types in text
        board_types = [
            "All Inclusive",
            "All-Inclusive",
            "Half Board",
            "Half-Board",
            "Full Board",
            "Full-Board",
            "Bed & Breakfast",
            "Bed and Breakfast",
            "Self Catering",
            "Room Only",
            "Vollpension",
            "Halbpension",
            "All Inklusive",
        ]
        
        body_text = soup.get_text()
        for board in board_types:
            if board.lower() in body_text.lower():
                return board
        
        return None

    def _extract_room_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract room type."""
        room_selectors = [
            ".room-type",
            ".room",
            ".accommodation",
            "[data-room]",
        ]
        
        for selector in room_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return None