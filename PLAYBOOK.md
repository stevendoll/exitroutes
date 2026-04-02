# exitroutes.app — Development Playbook

Practices and conventions adapted from [t12n](https://github.com/stevendoll/t12n) and [probate-scraper](https://github.com/stevendoll/probate-scraper).

---

## Stack

| Layer | Tool |
|-------|------|
| Landing page | Static HTML (S3 + CloudFront) |
| App | Python / Streamlit |
| Backend (future) | AWS Lambda (Python) |
| Database (future) | DynamoDB |
| DNS / CDN | Cloudflare → CloudFront |
| CI/CD | GitHub Actions |
| Auth (AWS) | OIDC — no long-lived credentials |
| Payments | Stripe Payment Links |
| Intake | Typeform (or Lambda-backed HTML form) |

---

## Repository layout

```
exitroutes/
├── index.html                  # Landing page
├── thank-you.html              # Post-payment redirect
├── app/
│   ├── main.py                 # Streamlit UI
│   ├── parser.py               # FieldRoutes CSV parser
│   ├── cleaner.py              # Data normalization & validation
│   ├── mapper.py               # Field mapping engine
│   ├── packager.py             # ZIP output generator
│   └── config/
│       ├── gorilladesk.json
│       ├── jobber.json
│       └── housecallpro.json
├── sample_data/                # Realistic test CSVs
├── scripts/
│   ├── bootstrap-aws.sh        # Creates S3, CloudFront, ACM, IAM OIDC
│   ├── bootstrap-cloudflare.sh # Creates DNS records
│   └── update-stripe-links.sh  # Patches Stripe links into index.html
├── .github/
│   └── workflows/
│       └── deploy-ui.yml       # S3 sync + CloudFront invalidation on push to main
├── requirements.txt
├── .env                        # Local secrets — never committed
├── .gitignore
└── PLAYBOOK.md
```

---

## Local development

```bash
cp .env .env.local   # fill in values once
source .env

# Run Streamlit app
cd app && pip install -r ../requirements.txt
streamlit run main.py
```

---

## Infrastructure bootstrap (one-time)

Run once to create all AWS and Cloudflare resources. Requires AWS CLI and `jq`.

```bash
source .env
bash scripts/bootstrap-aws.sh        # outputs ARNs — paste into .env
bash scripts/bootstrap-cloudflare.sh  # creates DNS records
```

Then seed GitHub secrets:

```bash
source .env
gh secret set AWS_ROLE_ARN              --body "$AWS_ROLE_ARN"
gh secret set S3_BUCKET                 --body "$S3_BUCKET"
gh secret set CLOUDFRONT_DISTRIBUTION_ID --body "$CLOUDFRONT_DISTRIBUTION_ID"
```

---

## CI/CD

`deploy-ui.yml` triggers on pushes to `main` that touch `index.html` or `thank-you.html`.

Steps:
1. Configure AWS credentials via OIDC (`aws-actions/configure-aws-credentials`)
2. Sync HTML files to S3
3. Invalidate CloudFront cache (`/*`)

No long-lived AWS credentials are stored — GitHub Actions assumes the OIDC role at deploy time.

---

## AWS IAM — OIDC pattern

The `bootstrap-aws.sh` script creates:

- **OIDC provider**: `token.actions.githubusercontent.com`
- **Role**: `exitroutes-github-deploy`
  - Trust policy: only this repo's `main` branch can assume it
  - Permissions: `s3:PutObject`, `s3:DeleteObject`, `cloudfront:CreateInvalidation`

This is the same pattern used in t12n. Never store `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` as GitHub secrets.

---

## Cloudflare DNS

| Record | Type | Value | Proxy |
|--------|------|-------|-------|
| `exitroutes.app` | CNAME | `<cloudfront>.cloudfront.net` | Off (gray cloud) |
| `www.exitroutes.app` | CNAME | `exitroutes.app` | Off |

Proxy must be **off** (DNS only) when using CloudFront with a custom SSL cert — Cloudflare and CloudFront can't both terminate TLS.

---

## Stripe setup (manual — 5 min)

1. Go to Stripe dashboard → **Payment Links** → Create link
2. **Standard**: `SwitchKit Standard Migration` — $199 one-time
   - Success URL: `https://exitroutes.app/thank-you?plan=standard`
3. **Concierge**: `SwitchKit Concierge Migration` — $349 one-time
   - Success URL: `https://exitroutes.app/thank-you?plan=concierge`
4. Paste the URLs into `.env` as `STRIPE_LINK_STANDARD` and `STRIPE_LINK_CONCIERGE`
5. Run: `bash scripts/update-stripe-links.sh` — patches `index.html` and commits

Future: Stripe webhook `checkout.session.completed` → Lambda → SES confirmation email.

---

## Intake form

**Option A — Typeform (MVP)**
- Create form at typeform.com per the 8-question spec
- Paste link into `.env` as `TYPEFORM_LINK`
- Set `INTAKE_FORM=typeform`
- After payment, Stripe success URL redirects to thank-you page which links to Typeform

**Option B — Custom Lambda form (no Typeform dependency)**
- Lambda function stores submission to DynamoDB + sends SES notification
- Form lives in `thank-you.html`
- Set `INTAKE_FORM=lambda`

---

## Secrets — where they live

| Secret | Dev | CI/CD |
|--------|-----|-------|
| AWS creds | OIDC (no secret needed) | OIDC |
| Stripe links | `.env` | Baked into HTML at build time |
| Cloudflare token | `.env` | Not needed post-bootstrap |
| Stripe webhook secret | `.env` | GitHub Secret → Lambda env var |

---

## Deploying the Streamlit app

MVP: [Streamlit Cloud](https://streamlit.io/cloud) — connect GitHub repo, point to `app/main.py`, free for one public app.

Future: containerize and run on AWS Lambda or ECS.

---

## Git workflow

### Branches

- `main` — protected; never commit directly
- `feature/<slug>` — all work happens here; open a PR to merge
- Linear history preferred (rebase before merge)

### Commit messages

Follow conventional commits with a required `Prompted-by:` trailer:

```
feat: add Stripe webhook handler

Sends SES confirmation and Slack #money notification on purchase.

Prompted-by: claude-sonnet-4-6
Prompt-summary: build the stripe integration for me
```

Types: `feat` | `fix` | `test` | `docs` | `refactor` | `chore`

A commit template is configured in `.gitmessage` — it loads automatically when you run `git commit`.

### PRs

Use the PR template at `.github/pull_request_template.md`. Always paste the prompt that generated the work. This enables prompt → code quality analysis over time.

Session notes go in `docs/sessions/YYYY-MM-DD-slug.md`.

---

## Testing

Framework: **pytest**. Tests live in `tests/`, source in `app/` and `api/`.

```bash
# Install dev deps
pip install pytest pytest-cov pandas stripe boto3

# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov=api --cov-report=term-missing
```

### Test files

| File | What it covers |
|------|---------------|
| `tests/test_parser.py` | CSV detection, encoding, BOM handling |
| `tests/test_cleaner.py` | Phone normalization, email validation, deduplication, address fallback |
| `tests/test_mapper.py` | Column mapping for all three destinations |
| `tests/test_packager.py` | ZIP output, report text, open invoices extraction |
| `tests/test_webhook.py` | Signature verification, plan detection, SES, Slack |

CI runs `pytest tests/ -v` on every PR. `main` is blocked until tests pass.

---

## CI / Branch protection

`ci.yml` triggers on PRs to `main`. Required status check: **`tests`**.

Branch protection rules on `main`:
- Required status checks: `tests` (strict — branch must be up to date)
- No force pushes
- No deletions

To add or update branch protection:
```bash
gh api --method PUT repos/stevendoll/exitroutes/branches/main/protection \
  --input - <<JSON
{
  "required_status_checks": {"strict": true, "contexts": ["tests"]},
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON
```

---

## Naming

- **Product**: SwitchKit
- **Domain**: exitroutes.app
- **GitHub repo**: `stevendoll/exitroutes`
- **AWS resources**: prefixed `exitroutes-`
- **S3 bucket**: `exitroutes-app-ui`
- **CloudFront**: `exitroutes-app`
- **IAM role**: `exitroutes-github-deploy`
