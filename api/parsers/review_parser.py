"""
ReviewParser — converts raw scraper output to a contacts-table dict.

Pain score weights and keyword lists are tuned for FieldRoutes reviews.
"""

import hashlib
import re
from datetime import datetime, timezone

# ── Keyword lists ──────────────────────────────────────────────────────────

HOT_KEYWORDS = [
    "fieldroutes",
    "data hostage",
    "holding our data",
    "impossible to leave",
    "can't switch",
    "data export",
    "incomplete backup",
    "$500",
    "500 dollars",
    "gorilladesk",
    "jobber",
    "housecall",
    "switching to",
    "switching from",
]

WARM_KEYWORDS = [
    "cancel",
    "leaving",
    "switch",
    "no support",
    "no one answers",
    "support is terrible",
    "can't get help",
    "no response",
    "never calls back",
    "price",
    "expensive",
    "cost",
    "pricing",
    "price increase",
    "overpriced",
]

# ── Pain score weights ────────────────────────────────────────────────────

PAIN_WEIGHTS = {
    "rating_1_star":       5,
    "rating_2_star":       3,
    "rating_3_star":       1,
    "mentions_data_hostage": 4,
    "mentions_switching":  2,
    "mentions_support":    1,
    "mentions_pricing":    1,
    "reviewer_is_owner":   1,
}

MIN_PAIN_SCORE = 3


class ReviewParser:

    def calculate_pain_score(self, data: dict) -> int:
        score  = 0
        rating = data.get("rating") or 5

        if rating == 1:
            score += PAIN_WEIGHTS["rating_1_star"]
        elif rating == 2:
            score += PAIN_WEIGHTS["rating_2_star"]
        elif rating == 3:
            score += PAIN_WEIGHTS["rating_3_star"]

        text = " ".join(filter(None, [
            data.get("cons_text", ""),
            data.get("full_review_text", ""),
            data.get("switching_reason", ""),
        ])).lower()

        if any(k in text for k in [
            "data hostage", "holding our data", "impossible to leave",
            "can't switch", "data export", "incomplete backup", "$500",
            "500 dollars",
        ]):
            score += PAIN_WEIGHTS["mentions_data_hostage"]

        if any(k in text for k in [
            "switching to", "switching from", "cancel", "leaving", "switching",
            "gorilladesk", "jobber", "housecall",
        ]):
            score += PAIN_WEIGHTS["mentions_switching"]

        if any(k in text for k in [
            "no support", "no one answers", "support is terrible",
            "can't get help", "no response", "never calls back",
        ]):
            score += PAIN_WEIGHTS["mentions_support"]

        if any(k in text for k in [
            "price", "expensive", "cost", "pricing", "price increase",
            "overpriced", "too much",
        ]):
            score += PAIN_WEIGHTS["mentions_pricing"]

        role = (data.get("reviewer_role") or "").lower()
        if any(r in role for r in ["owner", "operator", "ceo", "president", "founder"]):
            score += PAIN_WEIGHTS["reviewer_is_owner"]

        return min(score, 10)

    def detect_signals(self, data: dict) -> dict:
        text = " ".join(filter(None, [
            data.get("cons_text", ""),
            data.get("full_review_text", ""),
        ])).lower()

        return {
            "is_data_hostage": any(k in text for k in [
                "data hostage", "holding our data", "impossible to leave",
                "data export", "incomplete backup", "$500", "500 dollars",
            ]),
            "is_switching": any(k in text for k in [
                "switching to", "switching from", "cancel", "leaving",
                "switch to", "switch from", "gorilladesk", "jobber", "housecall",
            ]),
            "is_support_issue": any(k in text for k in [
                "no support", "no one answers", "support is terrible",
                "can't get help", "no response", "never calls back",
            ]),
            "is_pricing_issue": any(k in text for k in [
                "price", "expensive", "cost", "pricing", "price increase",
                "overpriced", "too much",
            ]),
        }

    def extract_key_sentences(self, text: str, max_sentences: int = 3) -> str:
        """Return the top N most complaint-relevant sentences."""
        if not text:
            return ""
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        all_keywords = HOT_KEYWORDS + WARM_KEYWORDS

        def sentence_score(s: str) -> int:
            s_lower = s.lower()
            return sum(1 for kw in all_keywords if kw in s_lower)

        ranked = sorted(sentences, key=sentence_score, reverse=True)
        top    = [s for s in ranked[:max_sentences] if sentence_score(s) > 0]
        return " ".join(top) if top else (sentences[0] if sentences else "")

    def generate_fingerprint(
        self, source: str, reviewer_name: str, business_name: str | None = None
    ) -> str:
        parts = [source, (reviewer_name or "").lower().strip()]
        if business_name:
            parts.append(business_name.lower().strip())
        return hashlib.md5("|".join(parts).encode()).hexdigest()

    def parse(self, raw: dict, source: str) -> dict | None:
        """
        Convert raw scraper output → contacts-table dict.
        Returns None if pain_score < MIN_PAIN_SCORE.
        """
        pain_score = self.calculate_pain_score(raw)
        if pain_score < MIN_PAIN_SCORE:
            return None

        signals  = self.detect_signals(raw)
        raw_text = raw.get("cons_text") or raw.get("full_review_text") or ""
        fp       = self.generate_fingerprint(
            source,
            raw.get("reviewer_name", ""),
            raw.get("business_name"),
        )

        return {
            "contact_type":      "lead",
            "source":            source,
            "outreach_status":   "new",
            "source_url":        raw.get("source_url"),
            "source_id":         raw.get("source_id"),
            "scraped_at":        datetime.now(timezone.utc).isoformat(),
            "business_name":     raw.get("business_name"),
            "reviewer_name":     raw.get("reviewer_name"),
            "reviewer_role":     raw.get("reviewer_role"),
            "company_size":      raw.get("company_size"),
            "rating":            raw.get("rating"),
            "pain_score":        pain_score,
            "raw_complaint":     self.extract_key_sentences(raw_text),
            "full_review_text":  raw_text,
            "fingerprint":       fp,
            **signals,
        }
