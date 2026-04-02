import json
import pytest
from unittest.mock import patch, MagicMock, call


# ── Helpers ───────────────────────────────────────────────────────────

def make_event(amount_total=19900, email="buyer@example.com", name="Test User"):
    return {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "amount_total": amount_total,
                "customer_details": {"email": email, "name": name},
            }
        },
    }


def make_api_event(body: dict, sig: str = "valid-sig") -> dict:
    return {
        "body": json.dumps(body),
        "headers": {"stripe-signature": sig},
    }


# ── Tests ─────────────────────────────────────────────────────────────

class TestSignatureVerification:
    def test_invalid_signature_returns_400(self):
        import stripe
        with patch("stripe.Webhook.construct_event", side_effect=stripe.error.SignatureVerificationError("bad sig", "sig")):
            import webhook
            response = webhook.handler(make_api_event({}), {})
        assert response["statusCode"] == 400

    def test_valid_signature_returns_200(self):
        evt = make_event()
        with patch("stripe.Webhook.construct_event", return_value=evt), \
             patch("webhook._notify_slack"), \
             patch("webhook._send_confirmation"):
            import webhook
            response = webhook.handler(make_api_event(evt), {})
        assert response["statusCode"] == 200

    def test_malformed_body_returns_400(self):
        import webhook
        with patch("stripe.Webhook.construct_event", side_effect=Exception("parse error")):
            response = webhook.handler({"body": "not json", "headers": {}}, {})
        assert response["statusCode"] == 400


class TestCheckoutHandling:
    def test_standard_plan_detected_by_amount(self):
        evt = make_event(amount_total=19900)
        captured = {}

        def fake_slack(name, email, plan_label, amount):
            captured["plan_label"] = plan_label

        with patch("stripe.Webhook.construct_event", return_value=evt), \
             patch("webhook._notify_slack", side_effect=fake_slack), \
             patch("webhook._send_confirmation"):
            import webhook
            webhook.handler(make_api_event(evt), {})

        assert captured["plan_label"] == "Standard Migration"

    def test_concierge_plan_detected_by_amount(self):
        evt = make_event(amount_total=34900)
        captured = {}

        def fake_slack(name, email, plan_label, amount):
            captured["plan_label"] = plan_label

        with patch("stripe.Webhook.construct_event", return_value=evt), \
             patch("webhook._notify_slack", side_effect=fake_slack), \
             patch("webhook._send_confirmation"):
            import webhook
            webhook.handler(make_api_event(evt), {})

        assert captured["plan_label"] == "Concierge Migration"

    def test_slack_always_notified(self):
        evt = make_event()
        with patch("stripe.Webhook.construct_event", return_value=evt), \
             patch("webhook._notify_slack") as mock_slack, \
             patch("webhook._send_confirmation"):
            import webhook
            webhook.handler(make_api_event(evt), {})
        mock_slack.assert_called_once()

    def test_email_sent_when_email_present(self):
        evt = make_event(email="buyer@example.com")
        with patch("stripe.Webhook.construct_event", return_value=evt), \
             patch("webhook._notify_slack"), \
             patch("webhook._send_confirmation") as mock_email:
            import webhook
            webhook.handler(make_api_event(evt), {})
        mock_email.assert_called_once()

    def test_email_skipped_when_missing(self):
        evt = make_event(email=None)
        with patch("stripe.Webhook.construct_event", return_value=evt), \
             patch("webhook._notify_slack"), \
             patch("webhook._send_confirmation") as mock_email:
            import webhook
            webhook.handler(make_api_event(evt), {})
        mock_email.assert_not_called()

    def test_non_checkout_event_ignored(self):
        evt = {"type": "payment_intent.created", "data": {"object": {}}}
        with patch("stripe.Webhook.construct_event", return_value=evt), \
             patch("webhook._notify_slack") as mock_slack, \
             patch("webhook._send_confirmation") as mock_email:
            import webhook
            response = webhook.handler(make_api_event(evt), {})
        assert response["statusCode"] == 200
        mock_slack.assert_not_called()
        mock_email.assert_not_called()


class TestSlackNotification:
    def test_posts_to_money_channel(self):
        import urllib.request
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            import webhook
            webhook._notify_slack("James T", "j@example.com", "Standard Migration", 199.0)

        call_args = mock_open.call_args[0][0]
        body = json.loads(call_args.data.decode())
        assert body["channel"] == "money"
        assert "Standard Migration" in body["text"]

    def test_slack_failure_does_not_raise(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            import webhook
            webhook._notify_slack("J", "j@x.com", "Standard Migration", 199.0)


class TestConfirmationEmail:
    def test_ses_called_with_correct_recipient(self):
        mock_ses = MagicMock()
        mock_boto3 = MagicMock()
        mock_boto3.client.return_value = mock_ses

        with patch("boto3.client", return_value=mock_ses):
            import webhook
            webhook._send_confirmation("James Thornton", "james@example.com", "Standard Migration")

        mock_ses.send_email.assert_called_once()
        call_kwargs = mock_ses.send_email.call_args[1]
        assert call_kwargs["Destination"]["ToAddresses"] == ["james@example.com"]

    def test_email_body_contains_typeform_link(self):
        mock_ses = MagicMock()
        captured_body = {}

        def capture_send(**kwargs):
            captured_body["text"] = kwargs["Message"]["Body"]["Text"]["Data"]

        mock_ses.send_email.side_effect = capture_send

        with patch("boto3.client", return_value=mock_ses):
            import webhook
            webhook._send_confirmation("James", "j@x.com", "Standard Migration")

        assert "typeform.com" in captured_body["text"]

    def test_uses_first_name_only(self):
        mock_ses = MagicMock()
        captured_body = {}

        def capture_send(**kwargs):
            captured_body["text"] = kwargs["Message"]["Body"]["Text"]["Data"]

        mock_ses.send_email.side_effect = capture_send

        with patch("boto3.client", return_value=mock_ses):
            import webhook
            webhook._send_confirmation("James Thornton", "j@x.com", "Standard Migration")

        assert "Hi James," in captured_body["text"]
        assert "Thornton" not in captured_body["text"]
