"""
POST /intake — stores a customer intake form submission.

Called from /thank-you after Stripe payment. No auth required.
Stores a CUSTOMER contact in DynamoDB, sends Slack + SES notification.
"""

import json
import logging
import os
import urllib.request
import urllib.error
import boto3

from api.db.dynamo import DynamoClient
from api.db.schema import get_table

logger = logging.getLogger(__name__)

SLACKMAIL_URL     = os.environ.get("SLACKMAIL_URL", "")
SLACKMAIL_API_KEY = os.environ.get("SLACKMAIL_API_KEY", "")
FROM_EMAIL        = os.environ.get("FROM_EMAIL", "steven@exitroutes.app")
ADMIN_EMAIL       = os.environ.get("ADMIN_EMAIL", "steven@dolltribe.com")


def _json_response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def _notify_slack(data: dict):
    if not SLACKMAIL_URL:
        return
    name     = data.get("name", "Unknown")
    email    = data.get("email", "")
    platform = data.get("from_platform", "FieldRoutes")
    dest     = data.get("to_platform", "unknown")
    plan     = data.get("plan", "standard")
    text     = (
        f":inbox_tray: *New intake — {name}* ({plan})\n"
        f"From: {platform} → {dest}\n"
        f"Email: {email}"
    )
    payload = json.dumps({"channel": "money", "text": text}).encode()
    req = urllib.request.Request(
        f"{SLACKMAIL_URL}/slack",
        data=payload,
        headers={
            "Authorization": f"Bearer {SLACKMAIL_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        logger.warning("Slack notify failed: %s", e)


def _send_email(data: dict):
    ses   = boto3.client("ses", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    name  = data.get("name", "there")
    email = data.get("email", "")
    if not email:
        return
    body = (
        f"Hi {name},\n\n"
        "Thanks for your ExitRoutes order. We received your intake details and will "
        "be in touch within 48 hours to start your migration.\n\n"
        "If you have any questions, reply to this email.\n\n"
        "— Steven\n"
        "ExitRoutes | exitroutes.app"
    )
    try:
        ses.send_email(
            Source=FROM_EMAIL,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": "Your ExitRoutes migration — next steps"},
                "Body":    {"Text": {"Data": body}},
            },
        )
    except Exception as e:
        logger.warning("SES send failed: %s", e)


def handle(event: dict) -> dict:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _json_response(400, {"error": "Invalid JSON"})

    name          = (body.get("name") or "").strip()
    email         = (body.get("email") or "").strip()
    from_platform = (body.get("from_platform") or "").strip()
    to_platform   = (body.get("to_platform") or "").strip()
    notes         = (body.get("notes") or "").strip()
    plan          = (body.get("plan") or "standard").strip()

    if not email:
        return _json_response(400, {"error": "email is required"})

    db = DynamoClient()
    contact_id = db.put_contact({
        "contact_type":    "customer",
        "source":          "intake",
        "outreach_status": "new",
        "pain_score":      0,
        "reviewer_name":   name,
        "email":           email,
        "from_platform":   from_platform,
        "to_platform":     to_platform,
        "intake_notes":    notes,
        "plan":            plan,
    })

    _notify_slack({**body, "plan": plan})
    _send_email(body)

    return _json_response(201, {"contact_id": contact_id})
