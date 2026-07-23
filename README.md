# Travel Price Monitor

A Python application for monitoring and tracking travel package prices.

## Phase 1 - Core Scraper (MVP)

Extracts structured trip information from travel package pages.

### Features

- Playwright-based scraping for JavaScript-rendered pages
- BeautifulSoup parsing for structured data extraction
- Pydantic models for type-safe data handling
- Comprehensive logging
- Unit tests

### Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

### Usage

```python
from travel_monitor import scrape_trip

result = scrape_trip("https://example.com/trip/123")

if result.success:
    print(result.trip_data.model_dump_json(indent=2))
else:
    print(f"Error: {result.error}")
```

Or via CLI:

```bash
python -m travel_monitor https://example.com/trip/123
```

### Extracted Fields

| Field | Description |
|-------|-------------|
| `trip_name` | Name/title of the trip |
| `current_price` | Current listed price |
| `currency` | Currency code (EUR, USD, GBP) |
| `price_per_person` | Price per person if different |
| `total_price` | Total price for all travelers |
| `departure_date` | Departure date |
| `return_date` | Return date |
| `duration_nights` | Trip duration in nights |
| `duration_days` | Trip duration in days |
| `hotel_name` | Hotel name |
| `hotel_stars` | Hotel star rating |
| `airline` | Airline name |
| `flight_direct` | Whether flight is direct |
| `origin` | Departure city/airport |
| `destination` | Destination city/airport |
| `availability` | Availability status |
| `available_spots` | Number of available spots |
| `board_type` | Board type (e.g., All Inclusive) |
| `room_type` | Room type |

### Testing

```bash
pytest tests/
pytest tests/ --cov=travel_monitor
```

### Architecture

```
src/travel_monitor/
├── __init__.py
├── main.py           # Entry point
├── models/
│   ├── __init__.py
│   └── trip.py       # Pydantic models
├── scraper/
│   └── __init__.py   # Playwright scraper
└── parser/
    └── __init__.py   # BeautifulSoup parser
```

**Separation of concerns:**
- `scraper` handles fetching (Playwright)
- `parser` handles extraction (BeautifulSoup)
- `models` defines data structures (Pydantic)

## Roadmap

- [ ] Phase 2: SQLite persistence
- [ ] Phase 3: Change detection
- [ ] Phase 4: Notifications
- [ ] Phase 5: Scheduling
- [ ] Phase 6: Multiple trips
- [ ] Phase 7: AI integration
- [ ] Phase 8: Web interface

## License

MIT