"""Tests for POST /intake."""

import json
from unittest.mock import patch, MagicMock
from tests.conftest import make_lead


def _make_event(body: dict) -> dict:
    return {
        "body": json.dumps(body),
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/intake",
        "headers": {},
    }


class TestIntake:
    def test_missing_email_returns_400(self, db):
        from api.intake import handle
        resp = handle(_make_event({"name": "John"}))
        assert resp["statusCode"] == 400

    def test_valid_submission_returns_201(self, db):
        from api.intake import handle
        with patch("api.intake.DynamoClient", return_value=db), \
             patch("api.intake._notify_slack"), \
             patch("api.intake._send_email"):
            resp = handle(_make_event({
                "name":          "Jane Owner",
                "email":         "jane@pestco.com",
                "from_platform": "FieldRoutes",
                "to_platform":   "GorillaDesk",
                "notes":         "Need help ASAP",
                "plan":          "standard",
            }))
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert "contact_id" in body

    def test_contact_stored_in_dynamo(self, db):
        from api.intake import handle
        with patch("api.intake.DynamoClient", return_value=db), \
             patch("api.intake._notify_slack"), \
             patch("api.intake._send_email"):
            resp = handle(_make_event({
                "name":  "Test User",
                "email": "test@example.com",
            }))
        cid     = json.loads(resp["body"])["contact_id"]
        contact = db.get_contact(cid)
        assert contact is not None
        assert contact["contact_type"] == "customer"
        assert contact["source"] == "intake"
        assert contact["email"] == "test@example.com"

    def test_slack_called(self, db):
        from api.intake import handle
        with patch("api.intake.DynamoClient", return_value=db), \
             patch("api.intake._notify_slack") as mock_slack, \
             patch("api.intake._send_email"):
            handle(_make_event({"email": "x@y.com"}))
        mock_slack.assert_called_once()

    def test_ses_called(self, db):
        from api.intake import handle
        with patch("api.intake.DynamoClient", return_value=db), \
             patch("api.intake._notify_slack"), \
             patch("api.intake._send_email") as mock_ses:
            handle(_make_event({"email": "x@y.com"}))
        mock_ses.assert_called_once()
