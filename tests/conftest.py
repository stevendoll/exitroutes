import sys
import os
import pytest
import boto3
from pathlib import Path
from moto import mock_aws

# Add app/ to path so test files can import parser, cleaner, mapper, packager
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

# Add api/ to path so "import webhook" works in test_webhook.py
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

# Add repo root to path so "api.db.schema" etc. resolve correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set required env vars for modules that read them at import time
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
os.environ.setdefault("SLACKMAIL_URL", "https://example.com")
os.environ.setdefault("SLACKMAIL_API_KEY", "test-api-key")
os.environ.setdefault("FROM_EMAIL", "test@example.com")
os.environ.setdefault("TYPEFORM_LINK", "https://typeform.com/test")
os.environ.setdefault("DYNAMO_TABLE_NAME", "exitroutes-contacts-test")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
# Fake AWS credentials for moto
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")


@pytest.fixture
def dynamo_table():
    """Mocked DynamoDB table scoped per test."""
    with mock_aws():
        resource   = boto3.resource("dynamodb", region_name="us-east-1")
        table_name = os.environ["DYNAMO_TABLE_NAME"]
        from api.db.schema import create_table_if_not_exists
        create_table_if_not_exists(resource, table_name)
        yield resource.Table(table_name)


@pytest.fixture
def db(dynamo_table):
    """DynamoClient wired to the mocked table."""
    from api.db.dynamo import DynamoClient
    return DynamoClient(table=dynamo_table)


def make_lead(**overrides) -> dict:
    """Factory for test lead data."""
    base = {
        "contact_type":    "lead",
        "source":          "capterra",
        "source_url":      "https://capterra.com/test",
        "source_id":       "test-123",
        "business_name":   "Test Pest Co",
        "reviewer_name":   "John O.",
        "reviewer_role":   "Owner",
        "company_size":    "2-10 employees",
        "rating":          1,
        "pain_score":      8,
        "is_switching":    True,
        "is_data_hostage": True,
        "is_support_issue": False,
        "is_pricing_issue": False,
        "raw_complaint":   "They want $500 for an incomplete backup.",
        "full_review_text": "They want $500 for an incomplete backup. Impossible to leave.",
        "fingerprint":     "test-fingerprint-abc123",
        "outreach_status": "new",
        "scraped_at":      "2026-04-01T10:00:00+00:00",
    }
    return {**base, **overrides}
