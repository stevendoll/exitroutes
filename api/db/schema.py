"""
DynamoDB key builders and table creation helper for exitroutes-contacts.

Table: exitroutes-contacts
  PK: CONTACT#{contact_id}   SK: METADATA       — contact record
  PK: CONTACT#{contact_id}   SK: SESSION#{token} — magic link / session tokens
  PK: SCRAPE#{run_id}        SK: METADATA       — scrape run record

GSIs:
  GSI1: source (PK) + pain_score (SK)       — browse leads by review source
  GSI2: outreach_status (PK) + pain_score   — browse by outreach status
  GSI3: contact_type (PK) + pain_score      — browse by type (lead/customer/admin)
  GSI4: fingerprint (PK) + scraped_at       — dedup check on ingest
"""

import boto3
import os


def contact_pk(contact_id: str) -> str:
    return f"CONTACT#{contact_id}"


def contact_sk() -> str:
    return "METADATA"


def session_sk(token: str) -> str:
    return f"SESSION#{token}"


def scrape_pk(run_id: str) -> str:
    return f"SCRAPE#{run_id}"


def scrape_sk() -> str:
    return "METADATA"


def create_table_if_not_exists(resource, table_name: str):
    """Create the contacts table with all GSIs. Safe to call multiple times."""
    existing = [t.name for t in resource.tables.all()]
    if table_name in existing:
        return resource.Table(table_name)

    table = resource.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK",             "AttributeType": "S"},
            {"AttributeName": "SK",             "AttributeType": "S"},
            {"AttributeName": "source",         "AttributeType": "S"},
            {"AttributeName": "outreach_status","AttributeType": "S"},
            {"AttributeName": "contact_type",   "AttributeType": "S"},
            {"AttributeName": "fingerprint",    "AttributeType": "S"},
            {"AttributeName": "pain_score",     "AttributeType": "N"},
            {"AttributeName": "scraped_at",     "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1-source-pain",
                "KeySchema": [
                    {"AttributeName": "source",     "KeyType": "HASH"},
                    {"AttributeName": "pain_score", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI2-status-pain",
                "KeySchema": [
                    {"AttributeName": "outreach_status", "KeyType": "HASH"},
                    {"AttributeName": "pain_score",      "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI3-type-pain",
                "KeySchema": [
                    {"AttributeName": "contact_type", "KeyType": "HASH"},
                    {"AttributeName": "pain_score",   "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "GSI4-fingerprint-dedup",
                "KeySchema": [
                    {"AttributeName": "fingerprint", "KeyType": "HASH"},
                    {"AttributeName": "scraped_at",  "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    return table


def get_table():
    """Return the DynamoDB Table resource using env config."""
    region = os.environ.get("AWS_REGION", "us-east-1")
    table_name = os.environ.get("DYNAMO_TABLE_NAME", "exitroutes-contacts")
    endpoint_url = os.environ.get("DYNAMO_ENDPOINT_URL")  # for local dev

    kwargs = {"region_name": region}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url

    resource = boto3.resource("dynamodb", **kwargs)
    return resource.Table(table_name)
