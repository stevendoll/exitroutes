"""
BaseScraper — abstract base class for all review site scrapers.
"""

import logging
import random
import time
from abc import ABC, abstractmethod

import requests

from api.db.dynamo import DynamoClient, DUPLICATE
from api.parsers.review_parser import ReviewParser

SCRAPE_DELAY_SECONDS = 3.0
MAX_RETRIES          = 2

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]


class BaseScraper(ABC):
    source_name: str = ""

    def __init__(self, db: DynamoClient | None = None):
        self.db     = db or DynamoClient()
        self.parser = ReviewParser()
        self.logger = logging.getLogger(f"scraper.{self.source_name}")
        self.session = requests.Session()
        self.session.headers.update(self._random_user_agent())

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Fetch raw review dicts from the source. Must be implemented."""

    @abstractmethod
    def parse_raw(self, raw: dict) -> dict | None:
        """
        Convert source-specific raw dict to the shape expected by ReviewParser.
        Return None to skip this item.
        """

    def run(self) -> dict:
        """
        Full scrape cycle: fetch → parse → score → store.
        Returns stats dict: {leads_found, leads_new, leads_duplicate, leads_skipped}.
        """
        stats = {"leads_found": 0, "leads_new": 0, "leads_duplicate": 0, "leads_skipped": 0}

        try:
            raw_items = self.scrape()
            stats["leads_found"] = len(raw_items)

            for raw in raw_items:
                normalized = self.parse_raw(raw)
                if not normalized:
                    stats["leads_skipped"] += 1
                    continue

                parsed = self.parser.parse(normalized, self.source_name)
                if not parsed:
                    stats["leads_skipped"] += 1
                    continue

                result = self.db.put_contact(parsed)
                if result == DUPLICATE:
                    stats["leads_duplicate"] += 1
                else:
                    stats["leads_new"] += 1

        except Exception as e:
            self.logger.error("Scrape failed: %s", e)
            raise

        self.logger.info(
            "%s: found=%d new=%d dup=%d skipped=%d",
            self.source_name,
            stats["leads_found"],
            stats["leads_new"],
            stats["leads_duplicate"],
            stats["leads_skipped"],
        )
        return stats

    def polite_delay(self, base: float | None = None):
        time.sleep((base or SCRAPE_DELAY_SECONDS) + random.uniform(0.5, 2.0))

    def safe_get(self, url: str, **kwargs) -> requests.Response | None:
        """GET with retry on 429. Returns None on 403 or persistent failure."""
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.get(url, timeout=15, **kwargs)
                if resp.status_code == 200:
                    return resp
                if resp.status_code == 429:
                    wait = 30 * (attempt + 1)
                    self.logger.warning("Rate limited. Waiting %ds...", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code == 403:
                    self.logger.warning("403 Forbidden on %s. Skipping.", url)
                    return None
                self.logger.warning("HTTP %d on %s", resp.status_code, url)
                return None
            except requests.RequestException as e:
                self.logger.error("Request error: %s", e)
                time.sleep(5)
        return None

    @staticmethod
    def _random_user_agent() -> dict:
        return {"User-Agent": random.choice(_USER_AGENTS)}
