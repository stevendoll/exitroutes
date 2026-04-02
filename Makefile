.PHONY: bootstrap bootstrap-aws bootstrap-cloudflare bootstrap-github bootstrap-lambda \
        bootstrap-dynamo stripe deploy update-stripe secrets seed-admin dev test

# Full bootstrap: AWS → Cloudflare → GitHub → Lambda → Stripe
bootstrap: bootstrap-aws bootstrap-cloudflare bootstrap-github bootstrap-lambda stripe

bootstrap-aws:
	bash scripts/bootstrap-aws.sh

bootstrap-cloudflare:
	bash scripts/bootstrap-cloudflare.sh

bootstrap-github:
	bash scripts/bootstrap-github.sh

bootstrap-lambda:
	bash scripts/bootstrap-lambda.sh

bootstrap-dynamo:
	source .env && bash scripts/bootstrap-dynamo.sh

seed-admin:
	source .env && python scripts/seed-admin.py

# Run Vite dev server
dev:
	cd ui && npm run dev

# Run all tests
test:
	python3.12 -m pytest tests/ -v

# Create Stripe products + payment links (requires STRIPE_SECRET_KEY in .env)
stripe:
	python scripts/create_stripe_products.py

# Patch Stripe links + Typeform link into HTML, then push
update-stripe:
	bash scripts/update-stripe-links.sh

# Seed all GitHub secrets from .env
secrets:
	@source .env && \
	gh secret set AWS_ROLE_ARN                --body "$$AWS_ROLE_ARN" && \
	gh secret set S3_BUCKET                   --body "$$S3_BUCKET" && \
	gh secret set CLOUDFRONT_DISTRIBUTION_ID  --body "$$CLOUDFRONT_DISTRIBUTION_ID" && \
	gh secret set STRIPE_WEBHOOK_SECRET       --body "$$STRIPE_WEBHOOK_SECRET" && \
	gh secret set DYNAMO_TABLE_NAME           --body "$$DYNAMO_TABLE_NAME" && \
	gh secret set MAGIC_LINK_BASE_URL         --body "$$MAGIC_LINK_BASE_URL" && \
	gh secret set ADMIN_EMAIL                 --body "$$ADMIN_EMAIL" && \
	gh secret set SLACKMAIL_URL               --body "$$SLACKMAIL_URL" && \
	gh secret set SLACKMAIL_API_KEY           --body "$$SLACKMAIL_API_KEY" && \
	echo "✓ All secrets set"

# Manual deploy (bypasses GitHub Actions — for emergencies)
deploy:
	@source .env && \
	aws s3 sync . s3://$$S3_BUCKET \
		--exclude "*" \
		--exclude ".venv/*" \
		--exclude "ui/node_modules/*" \
		--include "index.html" \
		--include "thank-you.html" \
		--include "admin/*.html" \
		--delete \
		--cache-control "public, max-age=300" && \
	aws cloudfront create-invalidation \
		--distribution-id $$CLOUDFRONT_DISTRIBUTION_ID \
		--paths "/*"
