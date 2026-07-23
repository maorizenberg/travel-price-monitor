"""Travel Price Monitor - Main entry point."""

import logging
import sys
from typing import Optional

from travel_monitor.models import ScrapeResult, TripData
from travel_monitor.scraper import TravelScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def scrape_trip(url: str, wait_selector: Optional[str] = None) -> ScrapeResult:
    """Scrape a travel package URL and return structured data.
    
    Args:
        url: The travel package URL to scrape
        wait_selector: Optional CSS selector to wait for
        
    Returns:
        ScrapeResult with trip data or error
    """
    with TravelScraper(headless=True) as scraper:
        return scraper.extract(url, wait_selector=wait_selector)


def main():
    """CLI entry point for testing."""
    if len(sys.argv) < 2:
        print("Usage: python -m travel_monitor <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    result = scrape_trip(url)
    
    if result.success:
        print(result.trip_data.model_dump_json(indent=2))
    else:
        print(f"Error: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()