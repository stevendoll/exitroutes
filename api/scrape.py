"""
Scrape handlers — admin only.

POST /scrape/run          — trigger scrape for one or more sources
GET  /scrape/runs         — list recent runs
GET  /scrape/runs/{id}    — single run detail
GET  /contacts/duplicates — fuzzy duplicate report (read-only, no auth)
"""

import json
import logging
import uuid

from api.auth import get_authenticated_contact
from api.db.dynamo import DynamoClient

logger = logging.getLogger(__name__)

SCRAPER_MAP = {
    "capterra":       "api.scrapers.capterra:CapterraScraper",
    "g2":             "api.scrapers.g2:G2Scraper",
    "softwareadvice": "api.scrapers.softwareadvice:SoftwareAdviceScraper",
    "getapp":         "api.scrapers.getapp:GetAppScraper",
    "reddit":         "api.scrapers.reddit:RedditScraper",
}


def _json(status: int, body: dict | list) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin":      "https://exitroutes.app",
            "Access-Control-Allow-Credentials": "true",
        },
        "body": json.dumps(body, default=str),
    }


def _require_admin(event: dict) -> dict | None:
    contact = get_authenticated_contact(event)
    if not contact or contact.get("contact_type") != "admin":
        return _json(403, {"error": "Forbidden"})
    return None


def handle_run(event: dict) -> dict:
    """POST /scrape/run — body: {sources: ['capterra', 'reddit', ...]}"""
    err = _require_admin(event)
    if err:
        return err

    try:
        body    = json.loads(event.get("body") or "{}")
        sources = body.get("sources") or list(SCRAPER_MAP.keys())
    except json.JSONDecodeError:
        return _json(400, {"error": "Invalid JSON"})

    unknown = [s for s in sources if s not in SCRAPER_MAP]
    if unknown:
        return _json(400, {"error": f"Unknown sources: {unknown}. Valid: {list(SCRAPER_MAP)}"})

    run_id = str(uuid.uuid4())
    db     = DynamoClient()
    db.put_scrape_run(run_id, sources)

    aggregate = {"leads_found": 0, "leads_new": 0, "leads_duplicate": 0, "leads_skipped": 0}
    per_source = {}

    for source in sources:
        module_path, class_name = SCRAPER_MAP[source].split(":")
        try:
            import importlib
            module  = importlib.import_module(module_path)
            cls     = getattr(module, class_name)
            scraper = cls(db=db)
            stats   = scraper.run()
            per_source[source] = stats
            for k in aggregate:
                aggregate[k] += stats.get(k, 0)
        except Exception as e:
            logger.error("Scraper %s failed: %s", source, e)
            per_source[source] = {"error": str(e)}

    final_stats = {**aggregate, "per_source": per_source}
    db.complete_scrape_run(run_id, final_stats)

    return _json(200, {"run_id": run_id, "stats": final_stats})


def handle_list_runs(event: dict) -> dict:
    """GET /scrape/runs"""
    err = _require_admin(event)
    if err:
        return err

    db   = DynamoClient()
    runs = db.list_scrape_runs()
    return _json(200, {"items": runs, "count": len(runs)})


def handle_get_run(event: dict) -> dict:
    """GET /scrape/runs/{id}"""
    err = _require_admin(event)
    if err:
        return err

    run_id = (event.get("pathParameters") or {}).get("id")
    if not run_id:
        return _json(400, {"error": "id is required"})

    db  = DynamoClient()
    run = db.get_scrape_run(run_id)
    if not run:
        return _json(404, {"error": "Run not found"})
    return _json(200, run)


def handle_duplicates(event: dict) -> dict:
    """GET /contacts/duplicates — fuzzy duplicate report, no auth required."""
    from api.deduplicator import find_fuzzy_duplicates
    pairs = find_fuzzy_duplicates()
    return _json(200, {"pairs": pairs, "count": len(pairs)})
