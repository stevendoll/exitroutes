"""
Contacts API handlers — admin only (requires session cookie).

GET  /contacts              — list with filters
GET  /contacts/{id}         — single contact
PATCH /contacts/{id}        — update outreach fields
POST /contacts/{id}/enrich  — enrich from web (googlesearch)
GET  /contacts/export/csv   — download all leads as CSV
"""

import csv
import io
import json
import logging

from api.auth import get_authenticated_contact
from api.db.dynamo import DynamoClient

logger = logging.getLogger(__name__)


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
    """Returns 403 response if not authenticated, else None."""
    contact = get_authenticated_contact(event)
    if not contact or contact.get("contact_type") != "admin":
        return _json(403, {"error": "Forbidden"})
    return None


def handle_list(event: dict) -> dict:
    """GET /contacts — list contacts with optional filters."""
    err = _require_admin(event)
    if err:
        return err

    params       = event.get("queryStringParameters") or {}
    contact_type = params.get("type")
    source       = params.get("source")
    status       = params.get("status")
    limit        = min(int(params.get("limit", 50)), 200)

    db    = DynamoClient()
    items, lek = db.list_contacts(
        contact_type=contact_type,
        source=source,
        status=status,
        limit=limit,
    )

    response = {"items": items, "count": len(items)}
    if lek:
        response["cursor"] = json.dumps(lek, default=str)
    return _json(200, response)


def handle_get(event: dict) -> dict:
    """GET /contacts/{id}"""
    err = _require_admin(event)
    if err:
        return err

    contact_id = (event.get("pathParameters") or {}).get("id")
    if not contact_id:
        return _json(400, {"error": "id is required"})

    db   = DynamoClient()
    item = db.get_contact(contact_id)
    if not item:
        return _json(404, {"error": "Contact not found"})
    return _json(200, item)


def handle_patch(event: dict) -> dict:
    """PATCH /contacts/{id} — update outreach fields."""
    err = _require_admin(event)
    if err:
        return err

    contact_id = (event.get("pathParameters") or {}).get("id")
    if not contact_id:
        return _json(400, {"error": "id is required"})

    try:
        updates = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _json(400, {"error": "Invalid JSON"})

    db     = DynamoClient()
    result = db.update_contact(contact_id, updates)
    if not result:
        return _json(404, {"error": "Contact not found"})
    return _json(200, result)


def handle_enrich(event: dict) -> dict:
    """POST /contacts/{id}/enrich — look up website/phone via Google."""
    err = _require_admin(event)
    if err:
        return err

    contact_id = (event.get("pathParameters") or {}).get("id")
    db         = DynamoClient()
    contact    = db.get_contact(contact_id)
    if not contact:
        return _json(404, {"error": "Contact not found"})

    business_name = contact.get("business_name")
    if not business_name:
        return _json(400, {"error": "Contact has no business_name to enrich"})

    try:
        from api.enricher import enrich_lead
        enriched = enrich_lead(business_name)
    except Exception as e:
        logger.error("Enrichment failed: %s", e)
        return _json(500, {"error": "Enrichment failed"})

    result = db.update_contact(contact_id, enriched)
    return _json(200, result)


def handle_export_csv(event: dict) -> dict:
    """GET /contacts/export/csv — download all leads as CSV."""
    err = _require_admin(event)
    if err:
        return err

    db    = DynamoClient()
    items = db.scan_contacts_for_export(contact_type="lead")

    if not items:
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type":              "text/csv",
                "Content-Disposition":       'attachment; filename="exitroutes_leads.csv"',
                "Access-Control-Allow-Origin": "https://exitroutes.app",
            },
            "body": "",
        }

    fieldnames = [
        "contact_id", "business_name", "reviewer_name", "reviewer_role",
        "company_size", "email", "phone", "website", "city", "state",
        "source", "source_url", "rating", "pain_score",
        "is_data_hostage", "is_switching", "is_support_issue", "is_pricing_issue",
        "raw_complaint", "outreach_status", "outreach_notes", "follow_up_date",
        "scraped_at", "created_at",
    ]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(items)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type":              "text/csv",
            "Content-Disposition":       'attachment; filename="exitroutes_leads.csv"',
            "Access-Control-Allow-Origin": "https://exitroutes.app",
            "Access-Control-Allow-Credentials": "true",
        },
        "body": buf.getvalue(),
    }
