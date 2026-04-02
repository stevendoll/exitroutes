#!/usr/bin/env python3
"""
Creates Stripe products, prices, and payment links for SwitchKit.
Optionally registers the webhook endpoint if API_URL is set.
Writes results back to .env.

Usage:
    pip install stripe
    python scripts/create_stripe_products.py
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ENV_FILE = ROOT / ".env"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def patch_env(key: str, value: str):
    content = ENV_FILE.read_text()
    content = re.sub(rf"^{re.escape(key)}=.*", f"{key}={value}", content, flags=re.MULTILINE)
    ENV_FILE.write_text(content)
    print(f"    .env ← {key}")


def main():
    try:
        import stripe
    except ImportError:
        print("Error: stripe not installed. Run: pip install stripe")
        sys.exit(1)

    env = load_env()
    api_key = env.get("STRIPE_SECRET_KEY", "")
    if not api_key or api_key.endswith("_"):
        print("Error: STRIPE_SECRET_KEY not set in .env")
        sys.exit(1)

    stripe.api_key = api_key
    is_live = api_key.startswith("sk_live_")
    mode = "LIVE" if is_live else "TEST"
    print(f"==> Stripe mode: {mode}")
    if is_live:
        confirm = input("Creating LIVE products. Type 'yes' to continue: ")
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    domain = env.get("CF_DOMAIN", "exitroutes.app")
    api_url = env.get("API_URL", "")

    print("==> Creating products and payment links")

    # ── Standard ─────────────────────────────────────────────────────
    standard_product = stripe.Product.create(
        name="ExitRoutes Standard Migration",
        description=(
            "Full FieldRoutes data migration — customers, subscriptions, "
            "24-month service history, open invoices. GorillaDesk, Jobber, "
            "or Housecall Pro output. 48-hour turnaround guaranteed."
        ),
    )
    standard_price = stripe.Price.create(
        product=standard_product.id,
        unit_amount=19900,
        currency="usd",
    )
    standard_link = stripe.PaymentLink.create(
        line_items=[{"price": standard_price.id, "quantity": 1}],
        after_completion={
            "type": "redirect",
            "redirect": {"url": f"https://{domain}/thank-you?plan=standard"},
        },
        billing_address_collection="auto",
        phone_number_collection={"enabled": False},
    )
    print(f"    Standard ($199): {standard_link.url}")

    # ── Concierge ────────────────────────────────────────────────────
    concierge_product = stripe.Product.create(
        name="ExitRoutes Concierge Migration",
        description=(
            "Everything in Standard + API-direct data pull, chemical log archive, "
            "technician & route mapping, 30-min onboarding call, 7-day support. "
            "Priority 24-hour turnaround."
        ),
    )
    concierge_price = stripe.Price.create(
        product=concierge_product.id,
        unit_amount=34900,
        currency="usd",
    )
    concierge_link = stripe.PaymentLink.create(
        line_items=[{"price": concierge_price.id, "quantity": 1}],
        after_completion={
            "type": "redirect",
            "redirect": {"url": f"https://{domain}/thank-you?plan=concierge"},
        },
        billing_address_collection="auto",
        phone_number_collection={"enabled": False},
    )
    print(f"    Concierge ($349): {concierge_link.url}")

    # ── Webhook endpoint ─────────────────────────────────────────────
    webhook_secret = ""
    if api_url:
        print("==> Registering Stripe webhook")
        webhook_url = f"{api_url}/webhook"
        endpoint = stripe.WebhookEndpoint.create(
            url=webhook_url,
            enabled_events=["checkout.session.completed"],
            description="ExitRoutes purchase handler",
        )
        webhook_secret = endpoint.secret
        print(f"    URL: {webhook_url}")
        print(f"    Secret: {webhook_secret[:12]}...")
    else:
        print("==> Skipping webhook registration (API_URL not set — run bootstrap-lambda.sh first)")
        print("    Re-run this script after API_URL is populated to register the webhook.")

    # ── Patch .env ───────────────────────────────────────────────────
    print("==> Patching .env")
    patch_env("STRIPE_LINK_STANDARD", standard_link.url)
    patch_env("STRIPE_LINK_CONCIERGE", concierge_link.url)
    if webhook_secret:
        patch_env("STRIPE_WEBHOOK_SECRET", webhook_secret)

    print()
    print("✓ Done.")
    print()
    print("Next steps:")
    if not api_url:
        print("  1. Run:  bash scripts/bootstrap-lambda.sh")
        print("  2. Run:  python scripts/create_stripe_products.py  (again, to register webhook)")
        print("  3. Run:  make update-stripe")
    else:
        print("  1. Run:  make update-stripe  (patches Stripe links into index.html)")
        print("  2. Run:  gh secret set STRIPE_WEBHOOK_SECRET --body \"$STRIPE_WEBHOOK_SECRET\"")
        print("  3. Push to deploy updated Lambda env vars")


if __name__ == "__main__":
    main()
