#!/usr/bin/env python3
"""
Seed the admin contact (steven@dolltribe.com) into exitroutes-contacts.
Safe to run multiple times — uses GSI query to check before inserting.

Usage:
    source .env
    python scripts/seed-admin.py
"""

import os
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
from api.db.dynamo import DynamoClient
from api.db.schema import create_table_if_not_exists

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "steven@dolltribe.com")
TABLE_NAME  = os.environ.get("DYNAMO_TABLE_NAME", "exitroutes-contacts")
REGION      = os.environ.get("AWS_REGION", "us-east-1")


def main():
    print(f"==> Seeding admin contact: {ADMIN_EMAIL}")
    print(f"    Table: {TABLE_NAME} ({REGION})")

    resource = boto3.resource("dynamodb", region_name=REGION)
    create_table_if_not_exists(resource, TABLE_NAME)

    db = DynamoClient(table=resource.Table(TABLE_NAME))

    # Check if already exists
    existing = db.find_admin_by_email(ADMIN_EMAIL)
    if existing:
        print(f"    Already exists: contact_id={existing['contact_id']}")
        return

    contact_id = db.put_contact({
        "contact_type":    "admin",
        "source":          "admin",
        "outreach_status": "new",
        "pain_score":      0,
        "scraped_at":      "",
        "email":           ADMIN_EMAIL,
        "reviewer_name":   "Steven",
    })

    print(f"    Created: contact_id={contact_id}")
    print()
    print("✓ Done.")
    print()
    print("Next: request a magic link:")
    print(f'  curl -X POST https://api.exitroutes.app/auth/magic-link \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -d \'{{"email": "{ADMIN_EMAIL}"}}\'')


if __name__ == "__main__":
    main()
