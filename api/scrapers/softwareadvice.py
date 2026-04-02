"""
SoftwareAdvice scraper — same Gartner parent as Capterra, similar HTML.
Extra field: "tenure" (years used). Long tenure + low rating = +1 pain.
"""

import re
from bs4 import BeautifulSoup

from api.scrapers.base import BaseScraper
from api.parsers.review_parser import HOT_KEYWORDS, WARM_KEYWORDS

SA_URL = "https://www.softwareadvice.com/pest-control/fieldroutes-profile/reviews/?page={page}"


class SoftwareAdviceScraper(BaseScraper):
    source_name = "softwareadvice"

    def scrape(self) -> list[dict]:
        results = []
        page    = 1

        while page <= 15:
            url  = SA_URL.format(page=page)
            resp = self.safe_get(url)
            if not resp:
                break

            soup    = BeautifulSoup(resp.text, "lxml")
            cards   = soup.select(".review-card, [class*='ReviewCard'], article.review")
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

            cons_el  = card.find(string=re.compile(r"Cons?", re.I))
            cons = ""
            if cons_el and cons_el.parent:
                sib = cons_el.parent.find_next_sibling()
                cons = sib.get_text(" ", strip=True) if sib else ""

            pros_el = card.find(string=re.compile(r"Pros?", re.I))
            pros = ""
            if pros_el and pros_el.parent:
                sib = pros_el.parent.find_next_sibling()
                pros = sib.get_text(" ", strip=True) if sib else ""

            # Tenure: "Used the software for: 2 years"
            tenure_el = card.find(string=re.compile(r"used.+for", re.I))
            tenure_years = 0
            if tenure_el:
                m = re.search(r"(\d+)\s*year", tenure_el, re.I)
                if m:
                    tenure_years = int(m.group(1))

            return {
                "reviewer_name":    self._text(card, [".reviewer-name", ".author-name"]),
                "reviewer_role":    self._text(card, [".reviewer-title", ".job-title"]),
                "company_size":     self._text(card, [".company-size"]),
                "rating":           rating,
                "cons_text":        cons,
                "pros_text":        pros,
                "full_review_text": f"{pros} {cons}".strip(),
                "tenure_years":     tenure_years,
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
        # Boost pain score for long-tenure low-rating reviewers
        if raw.get("tenure_years", 0) > 1 and raw.get("rating") and raw["rating"] <= 3:
            raw["_tenure_bonus"] = True  # ReviewParser will see this in text via magic below
            # Inject tenure signal into cons_text so pain scorer picks it up
            raw["cons_text"] = raw.get("cons_text", "") + " long time customer. "
        return raw
