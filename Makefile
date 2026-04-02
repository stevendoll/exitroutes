.PHONY: bootstrap bootstrap-aws bootstrap-cloudflare bootstrap-github bootstrap-lambda \
        stripe deploy update-stripe secrets setup-spa dev

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

# Configure CloudFront for SPA routing (run once after bootstrap-aws)
setup-spa:
	bash scripts/setup-cloudfront-spa.sh

# Create Stripe products + payment links (requires STRIPE_SECRET_KEY in .env)
stripe:
	python scripts/create_stripe_products.py

# Patch Stripe links into HTML, then push
update-stripe:
	bash scripts/update-stripe-links.sh

# Seed all GitHub secrets from .env
secrets:
	@source .env && \
	gh secret set AWS_ROLE_ARN                --body "$$AWS_ROLE_ARN" && \
	gh secret set S3_BUCKET                   --body "$$S3_BUCKET" && \
	gh secret set CLOUDFRONT_DISTRIBUTION_ID  --body "$$CLOUDFRONT_DISTRIBUTION_ID" && \
	gh secret set API_URL                     --body "$$API_URL" && \
	gh secret set STRIPE_WEBHOOK_SECRET       --body "$$STRIPE_WEBHOOK_SECRET" && \
	gh secret set SLACKMAIL_URL               --body "$$SLACKMAIL_URL" && \
	gh secret set SLACKMAIL_API_KEY           --body "$$SLACKMAIL_API_KEY" && \
	echo "✓ All secrets set"

# Local Vite dev server
dev:
	cd ui && npm run dev

# Manual deploy (bypasses GitHub Actions — for emergencies)
deploy:
	@source .env && \
	cd ui && npm run build && cd .. && \
	aws s3 sync ui/dist/ s3://$$S3_BUCKET \
		--delete \
		--cache-control "public, max-age=300" && \
	aws cloudfront create-invalidation \
		--distribution-id $$CLOUDFRONT_DISTRIBUTION_ID \
		--paths "/*"
