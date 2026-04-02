.PHONY: bootstrap bootstrap-aws bootstrap-cloudflare bootstrap-github bootstrap-lambda \
        stripe deploy update-stripe secrets

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
	gh secret set TYPEFORM_LINK               --body "$$TYPEFORM_LINK" && \
	gh secret set SLACKMAIL_URL               --body "$$SLACKMAIL_URL" && \
	gh secret set SLACKMAIL_API_KEY           --body "$$SLACKMAIL_API_KEY" && \
	echo "✓ All secrets set"

# Manual deploy (bypasses GitHub Actions — for emergencies)
deploy:
	@source .env && \
	aws s3 sync . s3://$$S3_BUCKET \
		--exclude "*" \
		--include "*.html" \
		--delete \
		--cache-control "public, max-age=300" && \
	aws cloudfront create-invalidation \
		--distribution-id $$CLOUDFRONT_DISTRIBUTION_ID \
		--paths "/*"
