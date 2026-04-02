#!/usr/bin/env bash
# Configure CloudFront custom error pages for SPA routing.
# Routes 403/404 → /index.html with 200 status so React Router handles all paths.
# Run once after bootstrap-aws.sh.
#
# Usage: source .env && bash scripts/setup-cloudfront-spa.sh

set -euo pipefail

: "${CLOUDFRONT_DISTRIBUTION_ID:?Set CLOUDFRONT_DISTRIBUTION_ID in .env}"

echo "==> Fetching current CloudFront distribution config..."
CONFIG=$(aws cloudfront get-distribution-config \
  --id "$CLOUDFRONT_DISTRIBUTION_ID" \
  --region us-east-1)

ETAG=$(echo "$CONFIG" | jq -r '.ETag')
DIST_CONFIG=$(echo "$CONFIG" | jq '.DistributionConfig')

echo "==> Adding SPA custom error pages (403 and 404 → /index.html)..."
UPDATED=$(echo "$DIST_CONFIG" | jq '
  .CustomErrorResponses = {
    "Quantity": 2,
    "Items": [
      {
        "ErrorCode": 403,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 0
      },
      {
        "ErrorCode": 404,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 0
      }
    ]
  }
')

aws cloudfront update-distribution \
  --id "$CLOUDFRONT_DISTRIBUTION_ID" \
  --distribution-config "$UPDATED" \
  --if-match "$ETAG" \
  --region us-east-1 \
  --output table --query 'Distribution.{ID:Id,Status:Status}'

echo "✓ CloudFront updated. Deploy propagation takes ~5 minutes."
echo "  /thank-you, /migrate, and all React Router paths will now work."
