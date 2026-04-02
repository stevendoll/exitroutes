"""
G2 scraper — FieldRoutes reviews.

Tries HTML first; falls back to G2's JSON endpoint which often works even
when the HTML page requires JavaScript rendering.
"""

import json
import re
from bs4 import BeautifulSoup

from api.scrapers.base import BaseScraper
from api.parsers.review_parser import HOT_KEYWORDS, WARM_KEYWORDS

G2_JSON_URL = (
    "https://www.g2.com/products/fieldroutes-a-servicetitan-company"
    "/reviews.json?page={page}"
)
G2_HTML_URL = (
    "https://www.g2.com/products/fieldroutes-a-servicetitan-company"
    "/reviews?page={page}&sort=most_recent"
)


class G2Scraper(BaseScraper):
    source_name = "g2"

    def scrape(self) -> list[dict]:
        results = []
        page    = 1

        while page <= 15:
            # Try JSON endpoint first
            raw_items = self._fetch_json(page)
            if raw_items is None:
                # Fall back to HTML
                raw_items = self._fetch_html(page)

            if not raw_items:
                break

            results.extend(raw_items)
            self.polite_delay()
            page += 1

        return results

    def _fetch_json(self, page: int) -> list[dict] | None:
        url  = G2_JSON_URL.format(page=page)
        resp = self.safe_get(url)
        if not resp:
            return None
        try:
            data    = resp.json()
            reviews = data.get("reviews", [])
            if not isinstance(reviews, list):
                return None
            return [self._normalize_json_review(r, url) for r in reviews]
        except (json.JSONDecodeError, AttributeError):
            return None

    def _normalize_json_review(self, r: dict, page_url: str) -> dict:
        return {
            "reviewer_name":    r.get("reviewer_name", ""),
            "reviewer_role":    r.get("title", ""),
            "company_size":     r.get("company_size", ""),
            "rating":           r.get("star_rating"),
            "cons_text":        r.get("love_least", "") or r.get("dislike", ""),
            "pros_text":        r.get("love_most", "") or r.get("like", ""),
            "full_review_text": r.get("comments", ""),
            "source_url":       page_url,
            "source_id":        str(r.get("id", "")),
        }

    def _fetch_html(self, page: int) -> list[dict] | None:
        url  = G2_HTML_URL.format(page=page)
        resp = self.safe_get(url)
        if not resp:
            return None

        soup    = BeautifulSoup(resp.text, "lxml")
        cards   = soup.select(".paper.paper--white.paper--box")
        if not cards:
            cards = soup.select("[itemprop='review']")
        if not cards:
            return []

        results = []
        all_keywords = HOT_KEYWORDS + WARM_KEYWORDS

        for card in cards:
            rating    = self._extract_rating(card)
            like_el   = card.find(attrs={"data-og-title": re.compile(r"like", re.I)})
            dislike_el = card.find(attrs={"data-og-title": re.compile(r"dislike|least", re.I)})
            pros      = like_el.get_text(" ", strip=True)    if like_el    else ""
            cons      = dislike_el.get_text(" ", strip=True) if dislike_el else ""
            full      = f"{pros} {cons}".strip()

            if rating and rating > 3 and not any(k in full.lower() for k in all_keywords):
                continue

            results.append({
                "reviewer_name": self._text(card, [".m-0.l2", ".reviewer-name"]),
                "reviewer_role": self._text(card, [".market-segment-info", ".reviewer-role"]),
                "company_size":  self._text(card, [".company-size"]),
                "rating":        rating,
                "cons_text":     cons,
                "pros_text":     pros,
                "full_review_text": full,
                "source_url":    url,
                "source_id":     card.get("data-review-id", ""),
            })

        return results

    def _extract_rating(self, card) -> int | None:
        el = card.find(attrs={"aria-label": re.compile(r"\d+\.?\d* out of 5")})
        if el:
            m = re.search(r"([\d.]+) out of", el.get("aria-label", ""))
            if m:
                return round(float(m.group(1)))
        return None

    def _text(self, card, selectors: list[str]) -> str:
        for sel in selectors:
            el = card.select_one(sel)
            if el:
                return el.get_text(" ", strip=True)
        return ""

    def parse_raw(self, raw: dict) -> dict | None:
        return raw
