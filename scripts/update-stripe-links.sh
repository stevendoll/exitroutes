#!/usr/bin/env bash
# Patches STRIPE_LINK_STANDARD and STRIPE_LINK_CONCIERGE into index.html
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT/.env"

INDEX="$ROOT/index.html"

if [ ! -f "$INDEX" ]; then
  echo "Error: index.html not found at $ROOT"
  exit 1
fi

if [ -z "${STRIPE_LINK_STANDARD:-}" ] || [ "$STRIPE_LINK_STANDARD" = "https://buy.stripe.com/" ]; then
  echo "Error: STRIPE_LINK_STANDARD not set in .env"
  exit 1
fi

if [ -z "${STRIPE_LINK_CONCIERGE:-}" ] || [ "$STRIPE_LINK_CONCIERGE" = "https://buy.stripe.com/" ]; then
  echo "Error: STRIPE_LINK_CONCIERGE not set in .env"
  exit 1
fi

sed -i '' \
  "s|https://buy.stripe.com/REPLACE_WITH_STANDARD_LINK|${STRIPE_LINK_STANDARD}|g" \
  "$INDEX"

sed -i '' \
  "s|https://buy.stripe.com/REPLACE_WITH_CONCIERGE_LINK|${STRIPE_LINK_CONCIERGE}|g" \
  "$INDEX"

echo "✓ Stripe links patched into index.html"
echo "  Standard:  ${STRIPE_LINK_STANDARD}"
echo "  Concierge: ${STRIPE_LINK_CONCIERGE}"

# Patch Typeform link into thank-you.html
THANKYOU="$ROOT/thank-you.html"
if [ -f "$THANKYOU" ] && [ -n "${TYPEFORM_LINK:-}" ]; then
  sed -i '' "s|TYPEFORM_PLACEHOLDER|${TYPEFORM_LINK}|g" "$THANKYOU"
  echo "✓ Typeform link patched into thank-you.html"
fi

echo ""
echo "  Commit and push to deploy:"
echo "  git add index.html thank-you.html && git commit -m 'add Stripe and Typeform links' && git push"
