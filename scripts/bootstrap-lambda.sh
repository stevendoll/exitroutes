#!/usr/bin/env bash
# Creates: Lambda execution role, Lambda function, API Gateway HTTP API
# Writes:  LAMBDA_EXECUTION_ROLE_ARN, API_URL, API_GATEWAY_ID → .env
# Run once locally. Day-to-day deploys go through deploy-api.yml.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT/.env"

FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-exitroutes-webhook}"
EXECUTION_ROLE_NAME="exitroutes-lambda-webhook"
REGION="${AWS_REGION:-us-east-1}"

patch_env() {
  local key="$1" val="$2"
  sed -i '' "s|^${key}=.*|${key}=${val}|" "$ROOT/.env"
  echo "    .env ← ${key}"
}

# ── Verify SES sender email ───────────────────────────────────────────
echo "==> SES: verify sender email (${CONTACT_EMAIL})"
STATUS=$(aws ses get-identity-verification-attributes \
  --identities "$CONTACT_EMAIL" \
  --region "$REGION" \
  --query "VerificationAttributes.\"${CONTACT_EMAIL}\".VerificationStatus" \
  --output text 2>/dev/null || echo "NotFound")

if [ "$STATUS" = "Success" ]; then
  echo "    already verified"
else
  aws ses verify-email-identity --email-address "$CONTACT_EMAIL" --region "$REGION"
  echo "    verification email sent to ${CONTACT_EMAIL} — click the link before testing"
fi

# ── Lambda execution role ─────────────────────────────────────────────
echo "==> IAM role: ${EXECUTION_ROLE_NAME}"
EXEC_ROLE_ARN=$(aws iam get-role \
  --role-name "$EXECUTION_ROLE_NAME" \
  --query 'Role.Arn' --output text 2>/dev/null || true)

if [ -z "$EXEC_ROLE_ARN" ]; then
  TRUST=$(mktemp /tmp/trust-XXXXX.json)
  cat > "$TRUST" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
JSON
  EXEC_ROLE_ARN=$(aws iam create-role \
    --role-name "$EXECUTION_ROLE_NAME" \
    --assume-role-policy-document "file://${TRUST}" \
    --query 'Role.Arn' --output text)
  rm -f "$TRUST"

  # Basic Lambda execution
  aws iam attach-role-policy \
    --role-name "$EXECUTION_ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

  # SES send permission
  POLICY=$(mktemp /tmp/policy-XXXXX.json)
  cat > "$POLICY" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["ses:SendEmail", "ses:SendRawEmail"],
    "Resource": "*"
  }]
}
JSON
  aws iam put-role-policy \
    --role-name "$EXECUTION_ROLE_NAME" \
    --policy-name "exitroutes-ses" \
    --policy-document "file://${POLICY}"
  rm -f "$POLICY"

  echo "    created: ${EXEC_ROLE_ARN}"
  echo "    waiting for role propagation..."
  sleep 10
else
  echo "    existing: ${EXEC_ROLE_ARN}"
fi

# ── Package Lambda ────────────────────────────────────────────────────
echo "==> Packaging Lambda"
PACKAGE_DIR=$(mktemp -d /tmp/lambda-pkg-XXXXX)
pip install -r "$ROOT/api/requirements.txt" -t "$PACKAGE_DIR" -q
cp "$ROOT/api/webhook.py" "$PACKAGE_DIR/"
ZIP_FILE=$(mktemp /tmp/lambda-XXXXX.zip)
(cd "$PACKAGE_DIR" && zip -r "$ZIP_FILE" . -q)
rm -rf "$PACKAGE_DIR"
echo "    ✓ $(du -sh "$ZIP_FILE" | cut -f1) zip"

# ── Lambda env vars ───────────────────────────────────────────────────
ENV_VARS="Variables={\
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET},\
FROM_EMAIL=${CONTACT_EMAIL},\
TYPEFORM_LINK=${TYPEFORM_LINK},\
SLACKMAIL_URL=${SLACKMAIL_URL},\
SLACKMAIL_API_KEY=${SLACKMAIL_API_KEY}\
}"

# ── Create or update Lambda function ─────────────────────────────────
echo "==> Lambda function: ${FUNCTION_NAME}"
EXISTING_FUNCTION=$(aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  --query 'Configuration.FunctionArn' --output text 2>/dev/null || true)

if [ -z "$EXISTING_FUNCTION" ]; then
  FUNCTION_ARN=$(aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --runtime python3.12 \
    --role "$EXEC_ROLE_ARN" \
    --handler webhook.handler \
    --zip-file "fileb://${ZIP_FILE}" \
    --timeout 30 \
    --memory-size 256 \
    --environment "$ENV_VARS" \
    --region "$REGION" \
    --query 'FunctionArn' --output text)
  echo "    created: ${FUNCTION_ARN}"
else
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://${ZIP_FILE}" \
    --region "$REGION" > /dev/null
  aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --environment "$ENV_VARS" \
    --region "$REGION" > /dev/null
  FUNCTION_ARN="$EXISTING_FUNCTION"
  echo "    updated: ${FUNCTION_ARN}"
fi
rm -f "$ZIP_FILE"

# ── API Gateway HTTP API ──────────────────────────────────────────────
echo "==> API Gateway HTTP API"
API_ID=$(aws apigatewayv2 get-apis \
  --region "$REGION" \
  --query "Items[?Name=='exitroutes-api'].ApiId | [0]" \
  --output text)

if [ "$API_ID" = "None" ] || [ -z "$API_ID" ]; then
  API_ID=$(aws apigatewayv2 create-api \
    --name "exitroutes-api" \
    --protocol-type HTTP \
    --region "$REGION" \
    --query 'ApiId' --output text)
  echo "    created: ${API_ID}"
else
  echo "    existing: ${API_ID}"
fi

# Integration
INTEGRATION_ID=$(aws apigatewayv2 get-integrations \
  --api-id "$API_ID" \
  --region "$REGION" \
  --query "Items[?IntegrationUri=='${FUNCTION_ARN}'].IntegrationId | [0]" \
  --output text)

if [ "$INTEGRATION_ID" = "None" ] || [ -z "$INTEGRATION_ID" ]; then
  INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id "$API_ID" \
    --integration-type AWS_PROXY \
    --integration-uri "$FUNCTION_ARN" \
    --payload-format-version "2.0" \
    --region "$REGION" \
    --query 'IntegrationId' --output text)
fi

# Route POST /webhook
ROUTE_EXISTS=$(aws apigatewayv2 get-routes \
  --api-id "$API_ID" \
  --region "$REGION" \
  --query "Items[?RouteKey=='POST /webhook'] | length(@)")

if [ "$ROUTE_EXISTS" = "0" ]; then
  aws apigatewayv2 create-route \
    --api-id "$API_ID" \
    --route-key "POST /webhook" \
    --target "integrations/${INTEGRATION_ID}" \
    --region "$REGION" > /dev/null
fi

# Default stage with auto-deploy
STAGE_EXISTS=$(aws apigatewayv2 get-stages \
  --api-id "$API_ID" \
  --region "$REGION" \
  --query "Items[?StageName=='\$default'] | length(@)")

if [ "$STAGE_EXISTS" = "0" ]; then
  aws apigatewayv2 create-stage \
    --api-id "$API_ID" \
    --stage-name '$default' \
    --auto-deploy \
    --region "$REGION" > /dev/null
fi

# Allow API Gateway to invoke Lambda
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "apigateway-invoke" \
  --action "lambda:InvokeFunction" \
  --principal "apigateway.amazonaws.com" \
  --source-arn "arn:aws:execute-api:${REGION}:${AWS_ACCOUNT_ID}:${API_ID}/*/*/webhook" \
  --region "$REGION" 2>/dev/null || true

API_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com"
echo "    endpoint: ${API_URL}/webhook"

# ── Update GitHub deploy role — allow lambda:UpdateFunctionCode ───────
echo "==> Updating GitHub deploy role permissions"
POLICY=$(mktemp /tmp/deploy-policy-XXXXX.json)
cat > "$POLICY" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::${S3_BUCKET}",
        "arn:aws:s3:::${S3_BUCKET}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "cloudfront:CreateInvalidation",
      "Resource": "arn:aws:cloudfront::${AWS_ACCOUNT_ID}:distribution/${CLOUDFRONT_DISTRIBUTION_ID}"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:GetFunction"
      ],
      "Resource": "${FUNCTION_ARN}"
    }
  ]
}
JSON
aws iam put-role-policy \
  --role-name "exitroutes-github-deploy" \
  --policy-name "exitroutes-deploy" \
  --policy-document "file://${POLICY}"
rm -f "$POLICY"
echo "    ✓ lambda:UpdateFunctionCode added"

# ── Cloudflare DNS: api.exitroutes.app ───────────────────────────────
echo "==> Cloudflare DNS: api.${CF_DOMAIN}"
API_HOST="${API_ID}.execute-api.${REGION}.amazonaws.com"
EXISTING=$(curl -s \
  "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records?type=CNAME&name=api.${CF_DOMAIN}" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" | jq -r '.result | length')

if [ "$EXISTING" = "0" ]; then
  curl -s -X POST \
    "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records" \
    -H "Authorization: Bearer ${CF_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"type\":\"CNAME\",\"name\":\"api.${CF_DOMAIN}\",\"content\":\"${API_HOST}\",\"ttl\":1,\"proxied\":false}" \
    | jq -r 'if .success then "    created: api.\(.result.zone_name) → \(.result.content)" else "    ✗ \(.errors[0].message)" end'
else
  echo "    already exists"
fi

# ── Patch .env ────────────────────────────────────────────────────────
echo ""
echo "==> Patching .env"
patch_env "LAMBDA_EXECUTION_ROLE_ARN" "$EXEC_ROLE_ARN"
patch_env "API_URL"                   "$API_URL"
patch_env "API_GATEWAY_ID"            "$API_ID"

echo ""
echo "✓ Lambda bootstrap complete."
echo "  Webhook endpoint: ${API_URL}/webhook"
echo ""
echo "Next steps:"
echo "  1. python scripts/create_stripe_products.py   (creates products + registers webhook)"
echo "  2. gh secret set STRIPE_WEBHOOK_SECRET --body \"\$STRIPE_WEBHOOK_SECRET\""
echo "  3. make update-stripe && git push"
