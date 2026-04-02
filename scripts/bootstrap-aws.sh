#!/usr/bin/env bash
# Creates: S3 bucket, ACM cert (DNS-validated via Cloudflare), CloudFront distribution, IAM OIDC + deploy role
# Writes:  AWS_ROLE_ARN, S3_BUCKET, CLOUDFRONT_DISTRIBUTION_ID, ACM_CERTIFICATE_ARN, CLOUDFRONT_DOMAIN → .env
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$ROOT/.env"

BUCKET="exitroutes-app-ui"
ROLE_NAME="exitroutes-github-deploy"
OIDC_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

patch_env() {
  local key="$1" val="$2"
  sed -i '' "s|^${key}=.*|${key}=${val}|" "$ROOT/.env"
  echo "    .env ← ${key}"
}

# ── S3 ────────────────────────────────────────────────────────────────
echo "==> S3 bucket: $BUCKET"
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  aws s3api create-bucket --bucket "$BUCKET" --region "$AWS_REGION"
  echo "    created"
else
  echo "    already exists"
fi
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
echo "    ✓ public access blocked"

# ── ACM cert ──────────────────────────────────────────────────────────
echo "==> ACM certificate (${CF_DOMAIN})"
CERT_ARN=$(aws acm list-certificates \
  --region us-east-1 \
  --query "CertificateSummaryList[?DomainName=='${CF_DOMAIN}'].CertificateArn | [0]" \
  --output text)

if [ "$CERT_ARN" = "None" ] || [ -z "$CERT_ARN" ]; then
  CERT_ARN=$(aws acm request-certificate \
    --domain-name "$CF_DOMAIN" \
    --subject-alternative-names "www.${CF_DOMAIN}" \
    --validation-method DNS \
    --region us-east-1 \
    --query 'CertificateArn' --output text)
  echo "    requested: $CERT_ARN"
  echo "    waiting for validation records to populate..."
  sleep 10
else
  echo "    existing: $CERT_ARN"
fi

# Add DNS validation CNAME to Cloudflare
VALIDATION=$(aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord')

VAL_NAME=$(echo "$VALIDATION" | jq -r '.Name' | sed 's/\.$//')
VAL_VALUE=$(echo "$VALIDATION" | jq -r '.Value' | sed 's/\.$//')

EXISTING=$(curl -s \
  "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records?type=CNAME&name=${VAL_NAME}" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" | jq -r '.result | length')

if [ "$EXISTING" = "0" ]; then
  echo "    adding Cloudflare validation CNAME..."
  curl -s -X POST \
    "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records" \
    -H "Authorization: Bearer ${CF_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"type\":\"CNAME\",\"name\":\"${VAL_NAME}\",\"content\":\"${VAL_VALUE}\",\"ttl\":300,\"proxied\":false}" \
    | jq -r 'if .success then "    ✓ DNS record added" else "    ✗ \(.errors[0].message)" end'
else
  echo "    validation CNAME already in Cloudflare"
fi

echo "    waiting for certificate to validate (up to 5 min)..."
aws acm wait certificate-validated \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1
echo "    ✓ certificate validated"

# ── CloudFront OAC ────────────────────────────────────────────────────
echo "==> CloudFront Origin Access Control"
OAC_ID=$(aws cloudfront list-origin-access-controls \
  --query "OriginAccessControlList.Items[?Name=='exitroutes-oac'].Id | [0]" \
  --output text)

if [ "$OAC_ID" = "None" ] || [ -z "$OAC_ID" ]; then
  OAC_ID=$(aws cloudfront create-origin-access-control \
    --origin-access-control-config \
    "Name=exitroutes-oac,Description=OAC for exitroutes-app-ui,SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=s3" \
    --query 'OriginAccessControl.Id' --output text)
  echo "    created: $OAC_ID"
else
  echo "    existing: $OAC_ID"
fi

# ── CloudFront distribution ───────────────────────────────────────────
echo "==> CloudFront distribution"
DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Comment=='exitroutes.app'].Id | [0]" \
  --output text)

if [ "$DIST_ID" = "None" ] || [ -z "$DIST_ID" ]; then
  DIST_CONFIG=$(mktemp /tmp/cf-dist-XXXXX.json)
  cat > "$DIST_CONFIG" <<JSON
{
  "CallerReference": "exitroutes-$(date +%s)",
  "Comment": "exitroutes.app",
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 1,
    "Items": [{
      "Id": "s3-exitroutes",
      "DomainName": "${BUCKET}.s3.${AWS_REGION}.amazonaws.com",
      "S3OriginConfig": {"OriginAccessIdentity": ""},
      "OriginAccessControlId": "${OAC_ID}"
    }]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "s3-exitroutes",
    "ViewerProtocolPolicy": "redirect-to-https",
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}
    },
    "Compress": true
  },
  "Aliases": {
    "Quantity": 2,
    "Items": ["${CF_DOMAIN}", "www.${CF_DOMAIN}"]
  },
  "ViewerCertificate": {
    "ACMCertificateArn": "${CERT_ARN}",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  },
  "CustomErrorResponses": {
    "Quantity": 1,
    "Items": [{
      "ErrorCode": 403,
      "ResponsePagePath": "/index.html",
      "ResponseCode": "200",
      "ErrorCachingMinTTL": 0
    }]
  },
  "Enabled": true,
  "HttpVersion": "http2",
  "PriceClass": "PriceClass_100"
}
JSON
  DIST_RESULT=$(aws cloudfront create-distribution --distribution-config "file://${DIST_CONFIG}")
  rm -f "$DIST_CONFIG"
  DIST_ID=$(echo "$DIST_RESULT" | jq -r '.Distribution.Id')
  DIST_DOMAIN=$(echo "$DIST_RESULT" | jq -r '.Distribution.DomainName')
  echo "    created: $DIST_ID"
else
  DIST_DOMAIN=$(aws cloudfront get-distribution \
    --id "$DIST_ID" \
    --query 'Distribution.DomainName' --output text)
  echo "    existing: $DIST_ID"
fi
echo "    domain: $DIST_DOMAIN"

# ── S3 bucket policy ──────────────────────────────────────────────────
echo "==> S3 bucket policy (allow CloudFront OAC)"
BUCKET_POLICY=$(mktemp /tmp/s3-policy-XXXXX.json)
cat > "$BUCKET_POLICY" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowCloudFrontOAC",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${BUCKET}/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::${AWS_ACCOUNT_ID}:distribution/${DIST_ID}"
      }
    }
  }]
}
JSON
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "file://${BUCKET_POLICY}"
rm -f "$BUCKET_POLICY"
echo "    ✓"

# ── IAM OIDC provider ─────────────────────────────────────────────────
echo "==> IAM OIDC provider"
if ! aws iam get-open-id-connect-provider \
     --open-id-connect-provider-arn "$OIDC_ARN" 2>/dev/null; then
  aws iam create-openid-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1"
  echo "    created"
else
  echo "    already exists"
fi

# ── IAM deploy role ───────────────────────────────────────────────────
echo "==> IAM role: $ROLE_NAME"
TRUST=$(mktemp /tmp/trust-XXXXX.json)
cat > "$TRUST" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "${OIDC_ARN}"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:${GITHUB_USERNAME}/${GITHUB_REPO}:*"
      },
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      }
    }
  }]
}
JSON

ROLE_ARN=$(aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document "file://${TRUST}" \
  --query 'Role.Arn' --output text 2>/dev/null || \
  aws iam get-role --role-name "$ROLE_NAME" \
  --query 'Role.Arn' --output text)
rm -f "$TRUST"

POLICY=$(mktemp /tmp/policy-XXXXX.json)
cat > "$POLICY" <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::${BUCKET}",
        "arn:aws:s3:::${BUCKET}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "cloudfront:CreateInvalidation",
      "Resource": "arn:aws:cloudfront::${AWS_ACCOUNT_ID}:distribution/${DIST_ID}"
    }
  ]
}
JSON
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "exitroutes-deploy" \
  --policy-document "file://${POLICY}"
rm -f "$POLICY"
echo "    ✓ $ROLE_ARN"

# ── Patch .env ────────────────────────────────────────────────────────
echo ""
echo "==> Patching .env"
patch_env "AWS_ROLE_ARN"               "$ROLE_ARN"
patch_env "S3_BUCKET"                  "$BUCKET"
patch_env "CLOUDFRONT_DISTRIBUTION_ID" "$DIST_ID"
patch_env "ACM_CERTIFICATE_ARN"        "$CERT_ARN"
patch_env "CLOUDFRONT_DOMAIN"          "$DIST_DOMAIN"

echo ""
echo "✓ AWS bootstrap complete."
echo "  Next: bash scripts/bootstrap-cloudflare.sh"
