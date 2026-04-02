"""GET /stats — aggregate counts, admin only."""

import json
from api.auth import get_authenticated_contact
from api.db.dynamo import DynamoClient


def _json(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin":      "https://exitroutes.app",
            "Access-Control-Allow-Credentials": "true",
        },
        "body": json.dumps(body),
    }


def handle(event: dict) -> dict:
    contact = get_authenticated_contact(event)
    if not contact or contact.get("contact_type") != "admin":
        return _json(403, {"error": "Forbidden"})

    db    = DynamoClient()
    stats = db.get_stats()
    return _json(200, stats)
