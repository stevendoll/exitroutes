#!/usr/bin/env bash
# Creates GitHub repo, sets branch protection, seeds secrets from .env
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT/.env"

REPO="${GITHUB_USERNAME}/${GITHUB_REPO}"

# ── Repo ──────────────────────────────────────────────────────────────
echo "==> GitHub repo: ${REPO}"
if gh repo view "$REPO" &>/dev/null; then
  echo "    already exists"
else
  gh repo create "$REPO" \
    --private \
    --description "SwitchKit — FieldRoutes data migration for pest control operators" \
    --source "$ROOT" \
    --remote origin \
    --push
  echo "    created and pushed"
fi

# Ensure remote is set
git -C "$ROOT" remote add origin "https://github.com/${REPO}.git" 2>/dev/null \
  || git -C "$ROOT" remote set-url origin "https://github.com/${REPO}.git"

# ── Secrets ───────────────────────────────────────────────────────────
echo "==> GitHub secrets"
gh secret set AWS_ROLE_ARN                --body "$AWS_ROLE_ARN"                --repo "$REPO"
gh secret set S3_BUCKET                   --body "$S3_BUCKET"                   --repo "$REPO"
gh secret set CLOUDFRONT_DISTRIBUTION_ID  --body "$CLOUDFRONT_DISTRIBUTION_ID"  --repo "$REPO"
echo "    ✓ AWS_ROLE_ARN"
echo "    ✓ S3_BUCKET"
echo "    ✓ CLOUDFRONT_DISTRIBUTION_ID"

# ── Branch protection ─────────────────────────────────────────────────
echo "==> Branch protection: main"
gh api \
  --method PUT \
  "repos/${REPO}/branches/main/protection" \
  -f required_status_checks='{"strict":true,"contexts":["deploy"]}' \
  -f enforce_admins=false \
  -F required_pull_request_reviews=null \
  -F restrictions=null \
  2>/dev/null && echo "    ✓" || echo "    skipped (push main first, then re-run)"

echo ""
echo "✓ GitHub bootstrap complete."
echo "  Repo: https://github.com/${REPO}"
