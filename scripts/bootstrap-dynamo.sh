#!/usr/bin/env bash
# Create the exitroutes-contacts DynamoDB table.
# Run once after bootstrapping IAM/Lambda.
# Usage: source .env && bash scripts/bootstrap-dynamo.sh

set -euo pipefail

TABLE_NAME="${DYNAMO_TABLE_NAME:-exitroutes-contacts}"
REGION="${AWS_REGION:-us-east-1}"

echo "==> Creating DynamoDB table: $TABLE_NAME ($REGION)"

# Check if already exists
if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" &>/dev/null; then
  echo "    Table already exists — skipping."
  exit 0
fi

aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --billing-mode PAY_PER_REQUEST \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
    AttributeName=source,AttributeType=S \
    AttributeName=outreach_status,AttributeType=S \
    AttributeName=contact_type,AttributeType=S \
    AttributeName=fingerprint,AttributeType=S \
    AttributeName=pain_score,AttributeType=N \
    AttributeName=scraped_at,AttributeType=S \
  --key-schema \
    AttributeName=PK,KeyType=HASH \
    AttributeName=SK,KeyType=RANGE \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "GSI1-source-pain",
        "KeySchema": [
          {"AttributeName": "source",     "KeyType": "HASH"},
          {"AttributeName": "pain_score", "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      },
      {
        "IndexName": "GSI2-status-pain",
        "KeySchema": [
          {"AttributeName": "outreach_status", "KeyType": "HASH"},
          {"AttributeName": "pain_score",      "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      },
      {
        "IndexName": "GSI3-type-pain",
        "KeySchema": [
          {"AttributeName": "contact_type", "KeyType": "HASH"},
          {"AttributeName": "pain_score",   "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      },
      {
        "IndexName": "GSI4-fingerprint-dedup",
        "KeySchema": [
          {"AttributeName": "fingerprint", "KeyType": "HASH"},
          {"AttributeName": "scraped_at",  "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      }
    ]' \
  --region "$REGION"

echo "    Waiting for table to be active..."
aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$REGION"

# Enable TTL for session tokens
aws dynamodb update-time-to-live \
  --table-name "$TABLE_NAME" \
  --time-to-live-specification "Enabled=true,AttributeName=ttl" \
  --region "$REGION"

echo "✓ Table ready: $TABLE_NAME"
echo ""
echo "Next steps:"
echo "  1. Update Lambda environment variables (DYNAMO_TABLE_NAME, etc.)"
echo "  2. Run: python scripts/seed-admin.py"
echo "  3. Add API Gateway routes (or run: make bootstrap-api-routes)"
