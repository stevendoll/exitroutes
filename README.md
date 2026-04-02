# ExitRoutes

FieldRoutes data migration service for pest control operators.
**exitroutes.app** — $199 flat fee, 48-hour turnaround.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vite + React + TypeScript (S3 + CloudFront) |
| API | AWS Lambda (Python 3.12) + API Gateway HTTP API |
| Email | AWS SES |
| Payments | Stripe Payment Links |
| Notifications | Slack via Slackmail |
| DNS | Cloudflare → CloudFront (DNS-only, proxy off) |
| Auth (AWS) | GitHub Actions OIDC — no long-lived credentials |
| CI/CD | GitHub Actions |

---

## Site routes

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/thank-you?plan=standard\|concierge` | Post-payment confirmation + intake form |
| `/migrate` | CSV migration tool (client-side, no upload) |

---

## API endpoints

Base URL: `https://l7lgyijvs7.execute-api.us-east-1.amazonaws.com`
Subdomain: `api.exitroutes.app` (CNAME → above)

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| `POST` | `/webhook` | `api/webhook.py` | Stripe `checkout.session.completed` → SES confirmation email + Slack `#money` notification |
| `POST` | `/intake` | _not yet built_ | Intake form submission from `/thank-you` |

### `POST /webhook`

Called by Stripe on successful payment. Verifies HMAC signature (`STRIPE_WEBHOOK_SECRET`), detects plan by amount (≥$300 = concierge), sends:
- SES email to customer with next-steps instructions
- Slack `#money` notification via Slackmail

**Auth:** `Stripe-Signature` header (HMAC-SHA256)
**Events handled:** `checkout.session.completed`

### `POST /intake` _(todo)_

Receives the 5-field form on the thank-you page (name, email, from-platform, to-platform, notes). Currently falls back to `mailto:` in the UI if `VITE_API_URL` is unset.

---

## Local development

```bash
# Frontend
cd ui && npm install
npm run dev          # http://localhost:5173

# Python tests
pip install pytest pytest-cov pandas stripe boto3
pytest tests/ -v
```

---

## Deployment

All deploys go through GitHub Actions on push to `main`.

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `deploy-ui.yml` | `ui/**` changed | `npm run build` → sync `ui/dist/` to S3 → CloudFront invalidation |
| `deploy-api.yml` | `api/**` changed | Package Lambda → `update-function-code` + `update-function-configuration` |
| `ci.yml` | PR to `main` | `pytest tests/ -v` — required to merge |

### Manual deploy

```bash
source .env
make deploy       # builds ui, syncs to S3, invalidates CloudFront
```

---

## Bootstrap (one-time)

```bash
cp .env.example .env   # fill in values
source .env

make bootstrap-aws        # S3, CloudFront, ACM cert, IAM OIDC role
make bootstrap-cloudflare # DNS records
make bootstrap-github     # GitHub repo, secrets, branch protection
make bootstrap-lambda     # Lambda, API Gateway, Cloudflare api.exitroutes.app
make setup-spa            # CloudFront custom error pages for SPA routing
make stripe               # Stripe products, payment links, webhook endpoint
make secrets              # Seed all GitHub Actions secrets from .env
```

---

## Secrets

| Secret | Where |
|--------|-------|
| `AWS_ROLE_ARN` | GitHub → assumed via OIDC at deploy time |
| `S3_BUCKET` | GitHub |
| `CLOUDFRONT_DISTRIBUTION_ID` | GitHub |
| `API_URL` | GitHub → baked into Vite build as `VITE_API_URL` |
| `STRIPE_WEBHOOK_SECRET` | GitHub → Lambda env var |
| `SLACKMAIL_URL` / `SLACKMAIL_API_KEY` | GitHub → Lambda env var |

Local secrets live in `.env` (gitignored). See `.env.example`.

---

## Repository layout

```
exitroutes/
├── ui/                         # Vite React app
│   └── src/
│       ├── pages/
│       │   ├── Landing.tsx     # /
│       │   ├── ThankYou.tsx    # /thank-you
│       │   └── Migrate.tsx     # /migrate
│       ├── lib/
│       │   ├── parser.ts       # CSV detection + parsing
│       │   ├── cleaner.ts      # Phone normalization, dedup, address fallback
│       │   ├── mapper.ts       # Field mapping (GorillaDesk / Jobber / HCP)
│       │   └── packager.ts     # ZIP output
│       └── config/             # Destination field mapping configs
├── api/
│   └── webhook.py              # Lambda handler — POST /webhook
├── app/                        # Python processing modules (reference / tests)
│   ├── parser.py
│   ├── cleaner.py
│   ├── mapper.py
│   └── packager.py
├── tests/                      # pytest suite (60 tests)
├── scripts/
│   ├── bootstrap-aws.sh
│   ├── bootstrap-cloudflare.sh
│   ├── bootstrap-github.sh
│   ├── bootstrap-lambda.sh
│   ├── setup-cloudfront-spa.sh
│   ├── create_stripe_products.py
│   └── update-stripe-links.sh
├── .github/workflows/
│   ├── ci.yml
│   ├── deploy-ui.yml
│   └── deploy-api.yml
├── Makefile
└── PLAYBOOK.md                 # Architecture decisions, conventions, runbooks
```

---

## Testing

```bash
pytest tests/ -v                                    # all 60 tests
pytest tests/ --cov=app --cov=api --cov-report=term-missing
```

| File | Coverage |
|------|----------|
| `test_parser.py` | CSV detection, encoding, BOM, empty rows |
| `test_cleaner.py` | Phone normalization, email validation, dedup, address fallback |
| `test_mapper.py` | Column mapping for all three destinations |
| `test_packager.py` | ZIP output, report text, open invoices |
| `test_webhook.py` | Signature verification, plan detection, SES, Slack |
