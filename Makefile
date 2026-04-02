.PHONY: bootstrap bootstrap-aws bootstrap-cloudflare bootstrap-github deploy update-stripe

# Run full bootstrap in order (AWS → Cloudflare → GitHub)
bootstrap: bootstrap-aws bootstrap-cloudflare bootstrap-github

bootstrap-aws:
	bash scripts/bootstrap-aws.sh

bootstrap-cloudflare:
	bash scripts/bootstrap-cloudflare.sh

bootstrap-github:
	bash scripts/bootstrap-github.sh

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

# Patch Stripe payment links into index.html, then push
update-stripe:
	bash scripts/update-stripe-links.sh
