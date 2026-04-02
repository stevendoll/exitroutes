"""
Capterra scraper — FieldRoutes reviews.

Uses requests + BeautifulSoup4. Paginates via ?page=N.
Only processes reviews with rating ≤ 3 or containing hot/warm keywords.
"""

import re
from bs4 import BeautifulSoup

from api.scrapers.base import BaseScraper
from api.parsers.review_parser import HOT_KEYWORDS, WARM_KEYWORDS

CAPTERRA_URL = (
    "https://www.capterra.com/p/85601/FieldRoutes/"
    "reviews/?sort=recent&page={page}"
)


class CapterraScraper(BaseScraper):
    source_name = "capterra"

    def scrape(self) -> list[dict]:
        results = []
        page    = 1
        while True:
            url  = CAPTERRA_URL.format(page=page)
            resp = self.safe_get(url)
            if not resp:
                break

            soup    = BeautifulSoup(resp.text, "lxml")
            reviews = soup.select("[data-testid='review-card'], .review-card, article.review")
            if not reviews:
                # Try generic heuristic
                reviews = soup.find_all("div", class_=re.compile(r"review", re.I))

            if not reviews:
                self.logger.info("No reviews found on page %d — stopping.", page)
                break

            for card in reviews:
                raw = self._extract_card(card, url)
                if raw:
                    results.append(raw)

            self.polite_delay()
            page += 1

            if page > 20:  # safety cap
                break

        return results

    def _extract_card(self, card, page_url: str) -> dict | None:
        try:
            # Rating — count filled stars or parse aria-label
            rating = self._extract_rating(card)

            # Text sections
            cons_el  = card.find(string=re.compile(r"Cons?", re.I))
            cons_text = ""
            if cons_el and cons_el.parent:
                sibling = cons_el.parent.find_next_sibling()
                cons_text = sibling.get_text(" ", strip=True) if sibling else ""

            pros_el   = card.find(string=re.compile(r"Pros?", re.I))
            pros_text = ""
            if pros_el and pros_el.parent:
                sibling = pros_el.parent.find_next_sibling()
                pros_text = sibling.get_text(" ", strip=True) if sibling else ""

            full_text = f"{pros_text} {cons_text}".strip()

            # Filter: keep only low-rating or keyword-containing reviews
            all_keywords = HOT_KEYWORDS + WARM_KEYWORDS
            text_lower   = full_text.lower()
            has_keyword  = any(k in text_lower for k in all_keywords)
            if rating and rating > 3 and not has_keyword:
                return None

            # Reviewer info
            reviewer_name = self._text(card, [
                "[data-testid='reviewer-name']", ".reviewer-name", ".author",
            ])
            reviewer_role = self._text(card, [
                "[data-testid='reviewer-role']", ".reviewer-role", ".job-title",
            ])
            company_size = self._text(card, [
                "[data-testid='company-size']", ".company-size",
            ])

            # Switching reason
            switching_el = card.find(string=re.compile(r"switching", re.I))
            switching_reason = ""
            if switching_el and switching_el.parent:
                sibling = switching_el.parent.find_next_sibling()
                switching_reason = sibling.get_text(" ", strip=True) if sibling else ""

            # Source ID from any anchor or data attribute
            source_id = card.get("data-review-id") or card.get("id") or ""

            return {
                "reviewer_name":    reviewer_name,
                "reviewer_role":    reviewer_role,
                "company_size":     company_size,
                "rating":           rating,
                "cons_text":        cons_text,
                "pros_text":        pros_text,
                "full_review_text": full_text,
                "switching_reason": switching_reason,
                "source_url":       page_url,
                "source_id":        str(source_id),
            }
        except Exception as e:
            self.logger.debug("Card extraction error: %s", e)
            return None

    def _extract_rating(self, card) -> int | None:
        # Try aria-label: "4 out of 5"
        star_el = card.find(attrs={"aria-label": re.compile(r"\d+ out of \d+")})
        if star_el:
            m = re.search(r"(\d+) out of", star_el.get("aria-label", ""))
            if m:
                return int(m.group(1))
        # Count filled star icons
        filled = card.select("svg.star-filled, .star-full, .rating-filled, [class*='star'][class*='fill']")
        if filled:
            return len(filled)
        return None

    def _text(self, card, selectors: list[str]) -> str:
        for sel in selectors:
            el = card.select_one(sel)
            if el:
                return el.get_text(" ", strip=True)
        return ""

    def parse_raw(self, raw: dict) -> dict | None:
        return raw  # already in the right shape from _extract_card
