"""
enrich_lead() — look up a pest control business by name.
Returns {website, phone, city, state}. Never raises.
"""

import re
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r'(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')
SKIP_DOMAINS = {
    "capterra.com", "g2.com", "yelp.com", "yellowpages.com",
    "bbb.org", "facebook.com", "linkedin.com", "google.com",
    "getapp.com", "softwareadvice.com",
}


def enrich_lead(business_name: str) -> dict:
    result = {"website": None, "phone": None, "city": None, "state": None}
    if not business_name:
        return result

    try:
        from googlesearch import search
        query   = f"{business_name} pest control"
        urls    = list(search(query, num_results=5, lang="en"))
        website = next(
            (u for u in urls if not any(d in u for d in SKIP_DOMAINS)),
            None,
        )
        if not website:
            return result
        result["website"] = website

        resp = requests.get(website, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; ExitRoutes-Enricher/1.0)"
        })
        if resp.status_code != 200:
            return result

        soup = BeautifulSoup(resp.text, "lxml")

        # Phone: prefer tel: links, fall back to text regex
        tel_link = soup.find("a", href=re.compile(r"^tel:"))
        if tel_link:
            raw_phone = tel_link.get("href", "").replace("tel:", "").strip()
        else:
            text      = soup.get_text()
            match     = PHONE_RE.search(text)
            raw_phone = match.group(0) if match else None

        if raw_phone:
            result["phone"] = _normalize_phone(raw_phone)

        # City/state from structured address or footer text
        address_tag = (
            soup.find("address") or
            soup.find(attrs={"itemprop": "address"}) or
            soup.find(class_=re.compile(r"address|location|footer", re.I))
        )
        if address_tag:
            addr_text        = address_tag.get_text(" ", strip=True)
            city, state      = _parse_city_state(addr_text)
            result["city"]   = city
            result["state"]  = state

    except Exception as e:
        logger.warning("Enrichment failed for '%s': %s", business_name, e)

    return result


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return raw


def _parse_city_state(text: str) -> tuple[str | None, str | None]:
    pattern = re.compile(r'([A-Z][a-zA-Z\s]+),\s*([A-Z]{2})\b')
    match   = pattern.search(text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, None
