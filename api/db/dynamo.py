"""
DynamoClient — all database operations for exitroutes-contacts.
"""

import uuid
import secrets
import time
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key

from api.db.schema import (
    contact_pk, contact_sk, session_sk,
    scrape_pk, scrape_sk, get_table,
)

logger = logging.getLogger(__name__)

# Sentinel returned when a fingerprint duplicate is detected
DUPLICATE = "DUPLICATE"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _epoch(dt: datetime) -> int:
    return int(dt.timestamp())


def _clean(item: dict) -> dict:
    """Remove DynamoDB key fields before returning to callers."""
    return {k: v for k, v in item.items() if k not in ("PK", "SK")}


class DynamoClient:
    def __init__(self, table=None):
        self._table = table or get_table()

    # ── Contacts ──────────────────────────────────────────────────────────

    def put_contact(self, data: dict) -> str | None:
        """
        Insert a new contact. Returns contact_id on success, DUPLICATE if
        fingerprint already exists (for scraped leads), None on error.

        data must include: contact_type, source, outreach_status, pain_score
        Fingerprint dedup is only applied when data['fingerprint'] is set.
        """
        # Dedup check for scraped leads
        if data.get("fingerprint"):
            existing = self.get_contact_by_fingerprint(data["fingerprint"])
            if existing:
                logger.info("Duplicate fingerprint: %s", data["fingerprint"])
                return DUPLICATE

        contact_id = data.get("contact_id") or str(uuid.uuid4())
        now = _now()

        item = {
            "PK":            contact_pk(contact_id),
            "SK":            contact_sk(),
            "contact_id":    contact_id,
            "created_at":    now,
            "updated_at":    now,
            **data,
        }

        # DynamoDB requires Decimal for numbers used as sort keys
        if "pain_score" in item:
            item["pain_score"] = Decimal(str(item["pain_score"]))

        # Ensure required GSI fields are present
        item.setdefault("source",          "unknown")
        item.setdefault("outreach_status", "new")
        item.setdefault("contact_type",    "lead")
        item.setdefault("pain_score",      Decimal("0"))
        item.setdefault("scraped_at",      now)

        # DynamoDB rejects empty strings as GSI key attributes — omit them
        # when absent so items without those fields are excluded from GSI4.
        for gsi_key in ("fingerprint", "scraped_at"):
            if not item.get(gsi_key):
                item.pop(gsi_key, None)

        self._table.put_item(Item=item)
        return contact_id

    def get_contact(self, contact_id: str) -> dict | None:
        resp = self._table.get_item(Key={
            "PK": contact_pk(contact_id),
            "SK": contact_sk(),
        })
        item = resp.get("Item")
        return _clean(item) if item else None

    def get_contact_by_fingerprint(self, fingerprint: str) -> dict | None:
        resp = self._table.query(
            IndexName="GSI4-fingerprint-dedup",
            KeyConditionExpression=Key("fingerprint").eq(fingerprint),
            Limit=1,
        )
        items = resp.get("Items", [])
        return _clean(items[0]) if items else None

    def update_contact(self, contact_id: str, updates: dict) -> dict | None:
        """
        Partial update. Allowed keys: outreach_status, outreach_notes,
        follow_up_date, website, phone, city, state, email.
        """
        allowed = {
            "outreach_status", "outreach_notes", "follow_up_date",
            "website", "phone", "city", "state", "email",
        }
        safe = {k: v for k, v in updates.items() if k in allowed}
        if not safe:
            return self.get_contact(contact_id)

        safe["updated_at"] = _now()

        expr_parts, names, values = [], {}, {}
        for i, (k, v) in enumerate(safe.items()):
            placeholder = f"#f{i}"
            value_key   = f":v{i}"
            names[placeholder] = k
            values[value_key]  = v
            expr_parts.append(f"{placeholder} = {value_key}")

        resp = self._table.update_item(
            Key={"PK": contact_pk(contact_id), "SK": contact_sk()},
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        item = resp.get("Attributes")
        return _clean(item) if item else None

    def list_contacts(
        self,
        contact_type: str | None = None,
        source: str | None = None,
        status: str | None = None,
        limit: int = 50,
        cursor: str | None = None,   # base64-encoded LastEvaluatedKey (handled by caller)
    ) -> tuple[list[dict], dict | None]:
        """
        Query contacts via GSI. Returns (items, last_evaluated_key).
        Priority: status (GSI2) > source (GSI1) > type (GSI3).
        Falls back to GSI3 with contact_type='lead' if nothing specified.
        """
        kwargs = {
            "ScanIndexForward": False,   # descending pain_score (highest first)
            "Limit": limit,
        }
        if cursor:
            kwargs["ExclusiveStartKey"] = cursor  # caller decodes

        if status:
            kwargs["IndexName"] = "GSI2-status-pain"
            kwargs["KeyConditionExpression"] = Key("outreach_status").eq(status)
        elif source:
            kwargs["IndexName"] = "GSI1-source-pain"
            kwargs["KeyConditionExpression"] = Key("source").eq(source)
        else:
            kwargs["IndexName"] = "GSI3-type-pain"
            kwargs["KeyConditionExpression"] = Key("contact_type").eq(contact_type or "lead")

        resp = self._table.query(**kwargs)
        items = [_clean(i) for i in resp.get("Items", [])]
        lek   = resp.get("LastEvaluatedKey")
        return items, lek

    def scan_contacts_for_export(self, contact_type: str = "lead") -> list[dict]:
        """Full table scan filtered by contact_type. Use for CSV export only."""
        items = []
        lek   = None
        while True:
            kwargs = {
                "IndexName": "GSI3-type-pain",
                "KeyConditionExpression": Key("contact_type").eq(contact_type),
                "ScanIndexForward": False,
            }
            if lek:
                kwargs["ExclusiveStartKey"] = lek
            resp = self._table.query(**kwargs)
            items.extend(_clean(i) for i in resp.get("Items", []))
            lek = resp.get("LastEvaluatedKey")
            if not lek:
                break
        return items

    # ── Sessions (magic link + auth) ──────────────────────────────────────

    def create_magic_link_token(self, contact_id: str, ttl_minutes: int = 15) -> str:
        token  = secrets.token_urlsafe(32)
        expiry = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        self._table.put_item(Item={
            "PK":         contact_pk(contact_id),
            "SK":         session_sk(token),
            "token":      token,
            "token_type": "magic_link",
            "contact_id": contact_id,
            "expires_at": expiry.isoformat(),
            "ttl":        _epoch(expiry),
        })
        return token

    def create_session_token(self, contact_id: str, ttl_days: int = 7) -> str:
        token  = secrets.token_urlsafe(32)
        expiry = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        self._table.put_item(Item={
            "PK":         contact_pk(contact_id),
            "SK":         session_sk(token),
            "token":      token,
            "token_type": "session",
            "contact_id": contact_id,
            "expires_at": expiry.isoformat(),
            "ttl":        _epoch(expiry),
        })
        return token

    def get_token(self, contact_id: str, token: str) -> dict | None:
        resp = self._table.get_item(Key={
            "PK": contact_pk(contact_id),
            "SK": session_sk(token),
        })
        item = resp.get("Item")
        if not item:
            return None
        # Check expiry (DynamoDB TTL deletion is eventually consistent)
        if item.get("ttl", 0) < int(time.time()):
            return None
        return item

    def delete_token(self, contact_id: str, token: str):
        self._table.delete_item(Key={
            "PK": contact_pk(contact_id),
            "SK": session_sk(token),
        })

    def find_admin_by_email(self, email: str) -> dict | None:
        """Scan GSI3 for admin contact with matching email."""
        from boto3.dynamodb.conditions import Attr
        logger.info("find_admin_by_email: querying GSI3 for email=%s", email)
        resp = self._table.query(
            IndexName="GSI3-type-pain",
            KeyConditionExpression=Key("contact_type").eq("admin"),
            FilterExpression=Attr("email").eq(email),
        )
        items = resp.get("Items", [])
        logger.info("find_admin_by_email: found %d items", len(items))
        return _clean(items[0]) if items else None

    # ── Scrape runs ────────────────────────────────────────────────────────

    def put_scrape_run(self, run_id: str, sources: list[str]) -> str:
        now = _now()
        self._table.put_item(Item={
            "PK":        scrape_pk(run_id),
            "SK":        scrape_sk(),
            "run_id":    run_id,
            "sources":   sources,
            "status":    "running",
            "started_at": now,
            "updated_at": now,
            "stats":     {},
        })
        return run_id

    def complete_scrape_run(self, run_id: str, stats: dict, status: str = "completed"):
        now = _now()
        self._table.update_item(
            Key={"PK": scrape_pk(run_id), "SK": scrape_sk()},
            UpdateExpression="SET #st = :st, stats = :stats, completed_at = :ca, updated_at = :ua",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":st":    status,
                ":stats": stats,
                ":ca":    now,
                ":ua":    now,
            },
        )

    def get_scrape_run(self, run_id: str) -> dict | None:
        resp = self._table.get_item(Key={
            "PK": scrape_pk(run_id),
            "SK": scrape_sk(),
        })
        item = resp.get("Item")
        return _clean(item) if item else None

    def list_scrape_runs(self, limit: int = 20) -> list[dict]:
        """Scan for SCRAPE# items. Acceptable since scrape runs are rare."""
        resp = self._table.scan(
            FilterExpression=Key("PK").begins_with("SCRAPE#"),
            Limit=200,
        )
        items = sorted(
            resp.get("Items", []),
            key=lambda x: x.get("started_at", ""),
            reverse=True,
        )
        return [_clean(i) for i in items[:limit]]

    # ── Stats ──────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Aggregate counts by querying each GSI. Efficient for small tables."""
        stats = {
            "by_type":   {},
            "by_source": {},
            "by_status": {},
        }

        for contact_type in ("lead", "customer", "admin"):
            resp = self._table.query(
                IndexName="GSI3-type-pain",
                KeyConditionExpression=Key("contact_type").eq(contact_type),
                Select="COUNT",
            )
            stats["by_type"][contact_type] = resp.get("Count", 0)

        for source in ("capterra", "g2", "softwareadvice", "getapp", "reddit", "intake"):
            resp = self._table.query(
                IndexName="GSI1-source-pain",
                KeyConditionExpression=Key("source").eq(source),
                Select="COUNT",
            )
            count = resp.get("Count", 0)
            if count:
                stats["by_source"][source] = count

        for status in ("new", "contacted", "converted", "skip"):
            resp = self._table.query(
                IndexName="GSI2-status-pain",
                KeyConditionExpression=Key("outreach_status").eq(status),
                Select="COUNT",
            )
            count = resp.get("Count", 0)
            if count:
                stats["by_status"][status] = count

        return stats
