"""
GetApp scraper — same Gartner parent as Capterra/SoftwareAdvice.
Extra field: value_rating (1-5 sub-rating for value for money).
"""

import re
from bs4 import BeautifulSoup

from api.scrapers.base import BaseScraper
from api.parsers.review_parser import HOT_KEYWORDS, WARM_KEYWORDS

GETAPP_URL = "https://www.getapp.com/field-service-management-software/a/fieldroutes/reviews/?page={page}"


class GetAppScraper(BaseScraper):
    source_name = "getapp"

    def scrape(self) -> list[dict]:
        results = []
        page    = 1

        while page <= 15:
            url  = GETAPP_URL.format(page=page)
            resp = self.safe_get(url)
            if not resp:
                break

            soup  = BeautifulSoup(resp.text, "lxml")
            cards = soup.select(".review-card, [class*='ReviewCard'], article.review")
            if not cards:
                break

            all_keywords = HOT_KEYWORDS + WARM_KEYWORDS
            for card in cards:
                raw = self._extract_card(card, url)
                if raw:
                    full = raw.get("full_review_text", "").lower()
                    rating = raw.get("rating")
                    if rating and rating > 3 and not any(k in full for k in all_keywords):
                        continue
                    results.append(raw)

            self.polite_delay()
            page += 1

        return results

    def _extract_card(self, card, page_url: str) -> dict | None:
        try:
            rating = self._extract_rating(card)

            cons_el = card.find(string=re.compile(r"Cons?", re.I))
            cons = ""
            if cons_el and cons_el.parent:
                sib = cons_el.parent.find_next_sibling()
                cons = sib.get_text(" ", strip=True) if sib else ""

            pros_el = card.find(string=re.compile(r"Pros?", re.I))
            pros = ""
            if pros_el and pros_el.parent:
                sib = pros_el.parent.find_next_sibling()
                pros = sib.get_text(" ", strip=True) if sib else ""

            # Value for money sub-rating
            value_el = card.find(string=re.compile(r"value.+money", re.I))
            value_rating = None
            if value_el:
                parent = value_el.parent
                stars  = parent.find_next_sibling()
                if stars:
                    m = re.search(r"(\d+)", stars.get_text())
                    if m:
                        value_rating = int(m.group(1))

            return {
                "reviewer_name":    self._text(card, [".reviewer-name", ".author"]),
                "reviewer_role":    self._text(card, [".reviewer-title", ".job-title"]),
                "company_size":     self._text(card, [".company-size"]),
                "rating":           rating,
                "value_rating":     value_rating,
                "cons_text":        cons,
                "pros_text":        pros,
                "full_review_text": f"{pros} {cons}".strip(),
                "source_url":       page_url,
                "source_id":        card.get("data-review-id", ""),
            }
        except Exception as e:
            self.logger.debug("Card extraction error: %s", e)
            return None

    def _extract_rating(self, card) -> int | None:
        el = card.find(attrs={"aria-label": re.compile(r"\d+ out of \d+")})
        if el:
            m = re.search(r"(\d+) out of", el.get("aria-label", ""))
            if m:
                return int(m.group(1))
        return None

    def _text(self, card, selectors: list[str]) -> str:
        for sel in selectors:
            el = card.select_one(sel)
            if el:
                return el.get_text(" ", strip=True)
        return ""

    def parse_raw(self, raw: dict) -> dict | None:
        # Boost pricing signal if low value_rating + pricing complaints
        if raw.get("value_rating") and raw["value_rating"] <= 2:
            pricing_words = ["price", "expensive", "cost", "pricing"]
            if any(w in (raw.get("cons_text") or "").lower() for w in pricing_words):
                raw["cons_text"] = raw.get("cons_text", "") + " too expensive. "
        return raw
