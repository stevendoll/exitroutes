"""
Auth handlers — magic link email login for admin.

POST /auth/magic-link  — send magic link to admin email
GET  /auth/verify      — validate token, issue session cookie
POST /auth/logout      — delete session token
"""

import json
import logging
import os
import time
import urllib.request
import boto3

from api.db.dynamo import DynamoClient

logger = logging.getLogger(__name__)

FROM_EMAIL            = os.environ.get("FROM_EMAIL", "steven@exitroutes.app")
MAGIC_LINK_BASE_URL   = os.environ.get("MAGIC_LINK_BASE_URL", "https://exitroutes.app")
MAGIC_LINK_TTL_MINUTES = int(os.environ.get("MAGIC_LINK_TTL_MINUTES", "15"))
SESSION_TTL_DAYS      = int(os.environ.get("SESSION_TTL_DAYS", "7"))
SESSION_COOKIE        = "er_session"
CONTACT_COOKIE        = "er_contact"


def _json(status: int, body: dict, headers: dict | None = None) -> dict:
    h = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "https://exitroutes.app",
        "Access-Control-Allow-Credentials": "true",
    }
    if headers:
        h.update(headers)
    return {"statusCode": status, "headers": h, "body": json.dumps(body)}


def _cookie(name: str, value: str, max_age: int) -> str:
    return (
        f"{name}={value}; HttpOnly; Secure; SameSite=Strict; "
        f"Path=/; Max-Age={max_age}"
    )


def _send_magic_link(email: str, token: str, contact_id: str):
    ses  = boto3.client("ses", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    link = f"{MAGIC_LINK_BASE_URL}/auth/verify?token={token}&cid={contact_id}"
    text = (
        f"Click the link below to log in to ExitRoutes admin.\n\n"
        f"{link}\n\n"
        f"This link expires in {MAGIC_LINK_TTL_MINUTES} minutes.\n\n"
        "If you didn't request this, ignore this email."
    )
    html = f"""<html><body style="font-family:sans-serif;color:#111;max-width:480px;margin:40px auto;padding:0 16px">
<p>Click the button below to log in to ExitRoutes admin.</p>
<p style="margin:32px 0">
  <a href="{link}" style="background:#F5C842;color:#0A0F1C;text-decoration:none;padding:12px 24px;border-radius:4px;font-weight:600;font-size:15px">Log in to ExitRoutes</a>
</p>
<p style="font-size:13px;color:#666">Link expires in {MAGIC_LINK_TTL_MINUTES} minutes. If you didn't request this, ignore this email.</p>
</body></html>"""
    ses.send_email(
        Source=FROM_EMAIL,
        Destination={"ToAddresses": [email]},
        Message={
            "Subject": {"Data": "ExitRoutes — your login link"},
            "Body": {
                "Text": {"Data": text},
                "Html":  {"Data": html},
            },
        },
    )


def handle_magic_link(event: dict) -> dict:
    """POST /auth/magic-link — body: {email}"""
    try:
        body  = json.loads(event.get("body") or "{}")
        email = (body.get("email") or "").strip().lower()
    except json.JSONDecodeError:
        return _json(400, {"error": "Invalid JSON"})

    if not email:
        return _json(400, {"error": "email is required"})

    logger.info("Magic link requested for email: %s", email)
    db      = DynamoClient()
    contact = db.find_admin_by_email(email)

    if not contact:
        logger.info("Admin not found for email: %s", email)
        return _json(200, {"message": "If that email is registered, a link is on its way."})

    contact_id = contact["contact_id"]
    token      = db.create_magic_link_token(contact_id, MAGIC_LINK_TTL_MINUTES)

    try:
        _send_magic_link(email, token, contact_id)
    except Exception as e:
        logger.error("Failed to send magic link: %s", e)
        return _json(500, {"error": "Failed to send login email"})

    return _json(200, {"message": "If that email is registered, a link is on its way."})


def handle_verify(event: dict) -> dict:
    """GET /auth/verify?token=xxx&cid=yyy — validate magic link, issue session cookie."""
    logger.info("verify event keys: %s", list(event.keys()))
    logger.info("verify rawQueryString: %s", event.get("rawQueryString", "<missing>"))
    logger.info("verify queryStringParameters: %s", event.get("queryStringParameters"))
    params     = event.get("queryStringParameters") or {}
    token      = (params.get("token") or "").strip()
    contact_id = (params.get("cid") or "").strip()

    if not token or not contact_id:
        return {
            "statusCode": 302,
            "headers": {"Location": "https://exitroutes.app/admin/login.html?error=invalid"},
            "body": "",
        }

    db   = DynamoClient()
    item = db.get_token(contact_id, token)

    if not item or item.get("token_type") != "magic_link":
        return {
            "statusCode": 302,
            "headers": {"Location": "https://exitroutes.app/admin/login.html?error=expired"},
            "body": "",
        }

    # Consume the magic link token (one-time use)
    db.delete_token(contact_id, token)

    # Issue a session token
    session_token = db.create_session_token(contact_id, SESSION_TTL_DAYS)
    max_age       = SESSION_TTL_DAYS * 86400

    # Redirect to admin dashboard — cookies set on api.exitroutes.app are sent
    # on subsequent credentialed fetch() calls from exitroutes.app (same-site)
    return {
        "statusCode": 302,
        "headers": {"Location": "https://exitroutes.app/admin/index.html"},
        "cookies": [
            _cookie(SESSION_COOKIE, session_token, max_age),
            f"{CONTACT_COOKIE}={contact_id}; Secure; SameSite=Strict; Path=/; Max-Age={max_age}",
        ],
        "body": "",
    }


def handle_logout(event: dict) -> dict:
    """POST /auth/logout — delete session token."""
    contact_id, session_token = _get_session(event)
    if contact_id and session_token:
        db = DynamoClient()
        db.delete_token(contact_id, session_token)

    return _json(
        200,
        {"message": "Logged out"},
        headers={"Set-Cookie": _cookie(SESSION_COOKIE, "", 0)},
    )


def get_authenticated_contact(event: dict) -> dict | None:
    """
    Middleware helper: validate session cookie and return the contact dict,
    or None if unauthenticated. Used by protected handlers.
    """
    contact_id, session_token = _get_session(event)
    if not contact_id or not session_token:
        return None

    db   = DynamoClient()
    item = db.get_token(contact_id, session_token)
    if not item or item.get("token_type") != "session":
        return None

    return db.get_contact(contact_id)


def _get_session(event: dict) -> tuple[str | None, str | None]:
    """Parse er_session and er_contact from cookies.

    API Gateway HTTP API v2 moves cookies out of headers['cookie'] and into
    event['cookies'] (an array of 'name=value' strings). Fall back to the
    raw Cookie header for local testing / v1 format.
    """
    cookies: dict[str, str] = {}

    # API Gateway v2: cookies are in event["cookies"] array
    for part in (event.get("cookies") or []):
        if "=" in part:
            k, _, v = part.partition("=")
            cookies[k.strip()] = v.strip()

    # Fallback: raw Cookie header (local tests, v1 format)
    if not cookies:
        cookie_header = (event.get("headers") or {}).get("cookie", "")
        for part in cookie_header.split(";"):
            part = part.strip()
            if "=" in part:
                k, _, v = part.partition("=")
                cookies[k.strip()] = v.strip()

    session_token = cookies.get(SESSION_COOKIE)
    contact_id    = cookies.get(CONTACT_COOKIE)
    return contact_id, session_token


def _cookie_with_contact(session_token: str, contact_id: str, max_age: int) -> list[str]:
    return [
        _cookie(SESSION_COOKIE, session_token, max_age),
        f"{CONTACT_COOKIE}={contact_id}; Secure; SameSite=Strict; Path=/; Max-Age={max_age}",
    ]
