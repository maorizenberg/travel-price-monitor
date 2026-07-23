"""Playwright-based web scraper for travel package pages."""

import logging
import time
from typing import Optional

from playwright.sync_api import sync_playwright, Browser, Page

from travel_monitor.models import ScrapeResult, TripData
from travel_monitor.parser import TripParser

logger = logging.getLogger(__name__)


class TravelScraper:
    """Scrapes travel package pages using Playwright for JavaScript rendering."""

    def __init__(self, headless: bool = True, timeout_ms: int = 30000):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._playwright = None
        self._browser: Optional[Browser] = None
        self.parser = TripParser()

    def start(self) -> None:
        """Start the browser instance."""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        logger.info("Browser started")

    def stop(self) -> None:
        """Stop the browser instance."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        logger.info("Browser stopped")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

    def fetch_html(self, url: str, wait_selector: Optional[str] = None) -> str:
        """Fetch fully rendered HTML from a URL.
        
        Args:
            url: The URL to scrape
            wait_selector: Optional CSS selector to wait for before extracting
            
        Returns:
            Fully rendered HTML content
        """
        if not self._browser:
            raise RuntimeError("Browser not started. Call start() or use context manager.")

        page: Page = self._browser.new_page()
        
        try:
            logger.info(f"Navigating to {url}")
            page.goto(url, timeout=self.timeout_ms, wait_until="networkidle")
            
            if wait_selector:
                logger.info(f"Waiting for selector: {wait_selector}")
                page.wait_for_selector(wait_selector, timeout=self.timeout_ms)
            
            html = page.content()
            logger.info(f"Fetched {len(html)} bytes from {url}")
            return html
            
        finally:
            page.close()

    def extract(self, url: str, wait_selector: Optional[str] = None) -> ScrapeResult:
        """Extract trip data from a travel package URL.
        
        Args:
            url: The URL to scrape
            wait_selector: Optional CSS selector to wait for
            
        Returns:
            ScrapeResult with extracted trip data or error
        """
        start_time = time.time()
        
        try:
            html = self.fetch_html(url, wait_selector)
            scrape_duration_ms = (time.time() - start_time) * 1000
            
            trip_data = self.parser.parse(html, url=url)
            
            return ScrapeResult(
                success=True,
                trip_data=trip_data,
                html_size=len(html),
                scrape_duration_ms=scrape_duration_ms,
            )
            
        except Exception as e:
            scrape_duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Scrape failed for {url}: {e}")
            return ScrapeResult(
                success=False,
                error=str(e),
                scrape_duration_ms=scrape_duration_ms,
            )