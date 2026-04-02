#!/usr/bin/env bash
# Creates DNS records: exitroutes.app → CloudFront (gray cloud — TLS terminates at CloudFront)
# Requires CLOUDFRONT_DOMAIN to be set (populated by bootstrap-aws.sh)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT/.env"

if [ -z "${CLOUDFRONT_DOMAIN:-}" ]; then
  echo "Error: CLOUDFRONT_DOMAIN is not set. Run bootstrap-aws.sh first."
  exit 1
fi

CF_API="https://api.cloudflare.com/client/v4"

upsert_dns() {
  local type="$1" name="$2" content="$3" proxied="$4"

  EXISTING_ID=$(curl -s \
    "${CF_API}/zones/${CF_ZONE_ID}/dns_records?type=${type}&name=${name}" \
    -H "Authorization: Bearer ${CF_API_TOKEN}" \
    | jq -r '.result[0].id // empty')

  PAYLOAD="{\"type\":\"${type}\",\"name\":\"${name}\",\"content\":\"${content}\",\"ttl\":1,\"proxied\":${proxied}}"

  if [ -n "$EXISTING_ID" ]; then
    curl -s -X PUT \
      "${CF_API}/zones/${CF_ZONE_ID}/dns_records/${EXISTING_ID}" \
      -H "Authorization: Bearer ${CF_API_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" \
      | jq -r 'if .success then "    updated: \(.result.name) → \(.result.content)" else "    ✗ \(.errors[0].message)" end'
  else
    curl -s -X POST \
      "${CF_API}/zones/${CF_ZONE_ID}/dns_records" \
      -H "Authorization: Bearer ${CF_API_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD" \
      | jq -r 'if .success then "    created: \(.result.name) → \(.result.content)" else "    ✗ \(.errors[0].message)" end'
  fi
}

echo "==> DNS records for ${CF_DOMAIN}"
echo "    CloudFront: ${CLOUDFRONT_DOMAIN}"
echo ""

# Root domain — CNAME to CloudFront, proxy OFF (CloudFront handles TLS)
upsert_dns "CNAME" "${CF_DOMAIN}"       "${CLOUDFRONT_DOMAIN}" "false"
upsert_dns "CNAME" "www.${CF_DOMAIN}"   "${CF_DOMAIN}"          "false"

echo ""
echo "✓ Cloudflare DNS bootstrap complete."
echo "  DNS propagation: ~1 min"
echo "  CloudFront deployment: 10-20 min"
echo "  Next: bash scripts/bootstrap-github.sh"
