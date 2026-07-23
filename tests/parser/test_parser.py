"""Tests for the TripParser."""

import pytest
from decimal import Decimal

from travel_monitor.parser import TripParser


@pytest.fixture
def parser():
    return TripParser()


class TestExtractPrice:
    """Tests for price extraction."""

    def test_parse_price_euro_symbol(self, parser):
        text = "1.234,56 €"
        price, currency = parser._parse_price_text(text)
        assert price == Decimal("1234.56")
        assert currency == "EUR"

    def test_parse_price_dollar_symbol(self, parser):
        text = "$1,234.56"
        price, currency = parser._parse_price_text(text)
        assert price == Decimal("1234.56")
        assert currency == "USD"

    def test_parse_price_pound_symbol(self, parser):
        text = "£999.99"
        price, currency = parser._parse_price_text(text)
        assert price == Decimal("999.99")
        assert currency == "GBP"

    def test_parse_price_plain_number(self, parser):
        text = "599"
        price, currency = parser._parse_price_text(text)
        assert price == Decimal("599")
        assert currency == "EUR"

    def test_parse_price_empty(self, parser):
        text = ""
        price, currency = parser._parse_price_text(text)
        assert price == Decimal("0")
        assert currency == "EUR"

    def test_parse_price_with_thousands(self, parser):
        text = "2.499 €"
        price, currency = parser._parse_price_text(text)
        assert price == Decimal("2499")
        assert currency == "EUR"


class TestExtractDuration:
    """Tests for duration extraction."""

    def test_parse_nights_and_days(self, parser):
        text = "7 Nights / 8 Days"
        nights, days = parser._parse_duration(text)
        assert nights == 7
        assert days == 8

    def test_parse_nights_only(self, parser):
        text = "5 Nights"
        nights, days = parser._parse_duration(text)
        assert nights == 5
        assert days == 6

    def test_parse_days_only(self, parser):
        text = "10 Tage"
        nights, days = parser._parse_duration(text)
        assert nights == 9
        assert days == 10

    def test_parse_german_nights(self, parser):
        text = "14 Nächte"
        nights, days = parser._parse_duration(text)
        assert nights == 14
        assert days == 15

    def test_parse_empty(self, parser):
        text = ""
        nights, days = parser._parse_duration(text)
        assert nights is None
        assert days is None


class TestExtractDates:
    """Tests for date extraction."""

    def test_parse_date_german_format(self, parser):
        text = "15.06.2025"
        result = parser._parse_date(text)
        assert result is not None
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15

    def test_parse_date_iso_format(self, parser):
        text = "2025-07-01"
        result = parser._parse_date(text)
        assert result is not None
        assert result.year == 2025
        assert result.month == 7
        assert result.day == 1

    def test_parse_date_range(self, parser):
        text = "01.06.2025 - 08.06.2025"
        departure, return_date = parser._parse_date_range(text)
        assert departure is not None
        assert return_date is not None
        assert departure.day == 1
        assert return_date.day == 8

    def test_parse_date_invalid(self, parser):
        text = "not a date"
        result = parser._parse_date(text)
        assert result is None


class TestParseFullHtml:
    """Tests for full HTML parsing."""

    def test_parse_minimal_html(self, parser):
        html = """
        <html>
        <head><title>Test Trip to Mallorca</title></head>
        <body>
            <h1>Wonderful Mallorca Vacation</h1>
            <div class="price">899 €</div>
            <div class="duration">7 Nights</div>
        </body>
        </html>
        """
        trip = parser.parse(html, url="https://example.com/trip/1")
        
        assert trip.trip_name == "Wonderful Mallorca Vacation"
        assert trip.current_price == Decimal("899")
        assert trip.currency == "EUR"
        assert trip.duration_nights == 7
        assert trip.duration_days == 8
        assert trip.url == "https://example.com/trip/1"

    def test_parse_with_hotel_and_flight(self, parser):
        html = """
        <html>
        <body>
            <h1>Mallorca All Inclusive</h1>
            <div class="price">1,299.00 €</div>
            <div class="hotel-name">Hotel Playa Bonita</div>
            <div class="hotel-stars">4 Sterne</div>
            <div class="airline">Lufthansa</div>
            <div class="departure-date">01.07.2025</div>
            <div class="return-date">08.07.2025</div>
        </body>
        </html>
        """
        trip = parser.parse(html)
        
        assert trip.current_price == Decimal("1299.00")
        assert trip.hotel_name == "Hotel Playa Bonita"
        assert trip.hotel_stars == 4
        assert trip.airline == "Lufthansa"
        assert trip.departure_date is not None
        assert trip.return_date is not None

    def test_parse_availability(self, parser):
        html = """
        <html>
        <body>
            <h1>Summer Trip</h1>
            <div class="price">599 €</div>
            <div class="availability">Noch 3 Plätze frei</div>
            <div class="available-spots">3 Plätze</div>
        </body>
        </html>
        """
        trip = parser.parse(html)
        
        assert trip.availability == "Noch 3 Plätze frei"
        assert trip.available_spots == 3

    def test_parse_board_type(self, parser):
        html = """
        <html>
        <body>
            <h1>All Inclusive Resort</h1>
            <div class="price">1,499 €</div>
            <div class="board-type">All Inclusive</div>
        </body>
        </html>
        """
        trip = parser.parse(html)
        
        assert trip.board_type == "All Inclusive"

    def test_parse_route(self, parser):
        html = """
        <html>
        <body>
            <h1>Flight to Spain</h1>
            <div class="price">450 €</div>
            <div class="route">Frankfurt → Palma de Mallorca</div>
        </body>
        </html>
        """
        trip = parser.parse(html)
        
        assert trip.origin == "Frankfurt"
        assert trip.destination == "Palma de Mallorca"