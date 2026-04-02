"""
Stripe webhook handler — checkout.session.completed
→ SES confirmation email to customer
→ Slack #money notification
"""
import json
import os
import urllib.request
import urllib.error
import logging
import boto3
import stripe

logger = logging.getLogger()
logger.setLevel(logging.INFO)

WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]
FROM_EMAIL     = os.environ.get("FROM_EMAIL", "steven@t12n.ai")
TYPEFORM_LINK  = os.environ.get("TYPEFORM_LINK", "")
SLACKMAIL_URL  = os.environ["SLACKMAIL_URL"]
SLACKMAIL_KEY  = os.environ["SLACKMAIL_API_KEY"]

PLAN_LABELS = {
    "standard":  ("Standard Migration", 199),
    "concierge": ("Concierge Migration", 349),
}


def handler(event, context):
    payload    = event.get("body") or ""
    sig_header = (event.get("headers") or {}).get("stripe-signature", "")

    try:
        evt = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as e:
        logger.warning("Invalid Stripe signature: %s", e)
        return {"statusCode": 400, "body": "Invalid signature"}
    except Exception as e:
        logger.error("Webhook parse error: %s", e)
        return {"statusCode": 400, "body": "Bad request"}

    logger.info("Received event: %s", evt["type"])

    if evt["type"] == "checkout.session.completed":
        _handle_checkout(evt["data"]["object"])

    return {"statusCode": 200, "body": "ok"}


def _handle_checkout(session: dict):
    details      = session.get("customer_details") or {}
    name         = details.get("name") or ""
    email        = details.get("email") or ""
    amount_cents = session.get("amount_total") or 0
    amount       = amount_cents / 100

    # Determine plan from success_url metadata or amount
    plan = "concierge" if amount >= 300 else "standard"
    plan_label, _ = PLAN_LABELS[plan]

    logger.info("Purchase: %s $%.0f — %s <%s>", plan_label, amount, name, email)

    _notify_slack(name, email, plan_label, amount)

    if email:
        _send_confirmation(name, email, plan_label)
    else:
        logger.warning("No customer email — skipping confirmation send")


def _notify_slack(name: str, email: str, plan_label: str, amount: float):
    text = (
        f"New order: *{plan_label}* (${amount:.0f})\n"
        f"Customer: {name or '(no name)'} — {email or '(no email)'}"
    )
    body = json.dumps({"channel": "money", "text": text}).encode()
    req = urllib.request.Request(
        f"{SLACKMAIL_URL}/slack",
        data=body,
        headers={
            "Authorization": f"Bearer {SLACKMAIL_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        logger.info("Slack notified")
    except urllib.error.URLError as e:
        logger.warning("Slack notification failed: %s", e)


def _send_confirmation(name: str, email: str, plan_label: str):
    first = name.split()[0] if name else "there"
    intake_url = TYPEFORM_LINK or "https://exitroutes.app"

    subject = f"Your ExitRoutes order — next steps"
    body = f"""\
Hi {first},

Payment received — you're in.

Here's what happens next:

1. Fill out this short intake form so we know exactly what you need:
   {intake_url}

2. We'll reply within 2 hours with a secure upload link for your
   FieldRoutes export files, plus instructions for pulling everything
   you need.

3. Within 48 hours of receiving your files, you'll have your complete
   migration package.

Any questions, just reply to this email.

— Steven
steven@t12n.ai | ExitRoutes
"""

    ses = boto3.client("ses", region_name="us-east-1")
    try:
        ses.send_email(
            Source=FROM_EMAIL,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": subject},
                "Body":    {"Text": {"Data": body}},
            },
        )
        logger.info("Confirmation sent to %s", email)
    except Exception as e:
        logger.error("SES send failed: %s", e)
