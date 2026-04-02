"""
Fuzzy duplicate finder — secondary dedup after fingerprint check.
Use sparingly: runs a full GSI scan.
"""

import logging
from difflib import SequenceMatcher
from api.db.dynamo import DynamoClient

logger = logging.getLogger(__name__)


def find_fuzzy_duplicates(db: DynamoClient | None = None, threshold: float = 0.85) -> list[dict]:
    """
    Scan all leads and return potential duplicate pairs.
    Format: [{contact_id_1, contact_id_2, similarity, business_name_1, business_name_2}]
    """
    if db is None:
        db = DynamoClient()

    # Fetch all leads (paginated)
    leads, lek = db.list_contacts(contact_type="lead", limit=200)
    while lek:
        more, lek = db.list_contacts(contact_type="lead", limit=200, cursor=lek)
        leads.extend(more)

    # Group by source, compare business_name within each group
    from itertools import combinations
    by_source: dict[str, list[dict]] = {}
    for lead in leads:
        src = lead.get("source", "unknown")
        by_source.setdefault(src, []).append(lead)

    pairs = []
    for source, group in by_source.items():
        for a, b in combinations(group, 2):
            name_a = (a.get("business_name") or "").lower().strip()
            name_b = (b.get("business_name") or "").lower().strip()
            if not name_a or not name_b:
                continue
            ratio = SequenceMatcher(None, name_a, name_b).ratio()
            if ratio >= threshold:
                pairs.append({
                    "contact_id_1":    a["contact_id"],
                    "contact_id_2":    b["contact_id"],
                    "similarity":      round(ratio, 3),
                    "business_name_1": a.get("business_name"),
                    "business_name_2": b.get("business_name"),
                    "source":          source,
                })

    logger.info("Fuzzy dedup: %d leads, %d potential pairs", len(leads), len(pairs))
    return pairs
