"""
Lambda router — single entry point for the exitroutes-contacts API.

Dispatches by HTTP method + path to individual handler functions.
The existing webhook.py stays as a separate Lambda.

API Gateway HTTP API route format: "METHOD /path"
Path parameters like /contacts/{id} are matched by prefix.
"""

import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def _404() -> dict:
    return {
        "statusCode": 404,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": "Not found"}),
    }


def _cors_preflight() -> dict:
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin":      "https://exitroutes.app",
            "Access-Control-Allow-Methods":     "GET,POST,PATCH,OPTIONS",
            "Access-Control-Allow-Headers":     "Content-Type,Cookie",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age":           "86400",
        },
        "body": "",
    }


def handler(event: dict, context) -> dict:
    method   = event.get("requestContext", {}).get("http", {}).get("method", "")
    raw_path = event.get("rawPath", "")

    logger.info("%s %s", method, raw_path)

    # CORS preflight
    if method == "OPTIONS":
        return _cors_preflight()

    # ── Auth ──────────────────────────────────────────────────────────────
    if method == "POST" and raw_path == "/auth/magic-link":
        from api.auth import handle_magic_link
        return handle_magic_link(event)

    if method == "GET" and raw_path == "/auth/verify":
        from api.auth import handle_verify
        return handle_verify(event)

    if method == "POST" and raw_path == "/auth/logout":
        from api.auth import handle_logout
        return handle_logout(event)

    # ── Intake ────────────────────────────────────────────────────────────
    if method == "POST" and raw_path == "/intake":
        from api.intake import handle
        return handle(event)

    # ── Contacts ──────────────────────────────────────────────────────────
    if method == "GET" and raw_path == "/contacts/export/csv":
        from api.contacts import handle_export_csv
        return handle_export_csv(event)

    if method == "GET" and raw_path == "/contacts/duplicates":
        from api.scrape import handle_duplicates
        return handle_duplicates(event)

    if method == "GET" and raw_path == "/contacts":
        from api.contacts import handle_list
        return handle_list(event)

    if raw_path.startswith("/contacts/") and not raw_path.endswith("/enrich"):
        contact_id = raw_path.split("/contacts/")[1].split("/")[0]
        event.setdefault("pathParameters", {})["id"] = contact_id

        if method == "GET":
            from api.contacts import handle_get
            return handle_get(event)

        if method == "PATCH":
            from api.contacts import handle_patch
            return handle_patch(event)

    if raw_path.endswith("/enrich") and method == "POST":
        parts      = raw_path.split("/")
        contact_id = parts[-2] if len(parts) >= 2 else ""
        event.setdefault("pathParameters", {})["id"] = contact_id
        from api.contacts import handle_enrich
        return handle_enrich(event)

    # ── Scraping ──────────────────────────────────────────────────────────
    if method == "POST" and raw_path == "/scrape/run":
        from api.scrape import handle_run
        return handle_run(event)

    if method == "GET" and raw_path == "/scrape/runs":
        from api.scrape import handle_list_runs
        return handle_list_runs(event)

    if method == "GET" and raw_path.startswith("/scrape/runs/"):
        run_id = raw_path.split("/scrape/runs/")[1]
        event.setdefault("pathParameters", {})["id"] = run_id
        from api.scrape import handle_get_run
        return handle_get_run(event)

    # ── Stats ─────────────────────────────────────────────────────────────
    if method == "GET" and raw_path == "/stats":
        from api.stats import handle
        return handle(event)

    return _404()
