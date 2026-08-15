"""Eshet.com specific scraper for discovering trips."""

import json
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class EshetDiscovery:
    """Discover trip URLs from eshet.com category pages."""

    def discover_trips(self, html: str) -> list[dict]:
        """Extract all trip links from a category page.
        
        Args:
            html: HTML content of the category page
            
        Returns:
            List of dicts with trip URL and basic info
        """
        soup = BeautifulSoup(html, "lxml")
        trips = []
        seen_urls = set()
        
        # Find all links to trip pages
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            
            # Match trip URLs
            if "/organized/trip/" in href and "itinerary=" in href:
                # Normalize URL
                if href.startswith("/"):
                    href = f"https://www.eshet.com{href}"
                
                # Skip duplicates
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                
                # Extract basic info from link text
                text = link.get_text(strip=True)
                
                trips.append({
                    "url": href,
                    "text": text[:200] if text else "",
                })
        
        logger.info(f"Discovered {len(trips)} trip URLs")
        return trips

    def discover_from_category(self, category_url: str) -> list[str]:
        """Get just the URLs from a category page.
        
        Args:
            category_url: URL of the category page
            
        Returns:
            List of trip URLs
        """
        from travel_monitor.scraper import TravelScraper
        
        with TravelScraper(headless=True, timeout_ms=90000) as scraper:
            html = scraper.fetch_html(category_url, wait_until="domcontentloaded")
        
        trips = self.discover_trips(html)
        return [t["url"] for t in trips]