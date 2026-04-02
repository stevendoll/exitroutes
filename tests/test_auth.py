"""Tests for magic link auth flow."""

import json
import time
from unittest.mock import patch


def _admin_contact_data():
    return {
        "contact_type":    "admin",
        "source":          "admin",
        "outreach_status": "new",
        "pain_score":      0,
        "scraped_at":      "",
        "email":           "steven@dolltribe.com",
        "reviewer_name":   "Steven",
    }


def _make_event(method: str, path: str, body: dict | None = None, cookies: dict | None = None) -> dict:
    headers = {}
    if cookies:
        headers["cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    return {
        "requestContext": {"http": {"method": method}},
        "rawPath": path,
        "body": json.dumps(body) if body else None,
        "headers": headers,
        "queryStringParameters": {},
    }


class TestMagicLink:
    def test_unknown_email_returns_200(self, db):
        """Don't reveal whether email is registered."""
        from api.auth import handle_magic_link
        with patch("api.auth.DynamoClient", return_value=db):
            resp = handle_magic_link(_make_event("POST", "/auth/magic-link", {"email": "nobody@example.com"}))
        assert resp["statusCode"] == 200

    def test_missing_email_returns_400(self, db):
        from api.auth import handle_magic_link
        with patch("api.auth.DynamoClient", return_value=db):
            resp = handle_magic_link(_make_event("POST", "/auth/magic-link", {}))
        assert resp["statusCode"] == 400

    def test_known_admin_sends_email(self, db):
        cid = db.put_contact(_admin_contact_data())
        from api.auth import handle_magic_link
        with patch("api.auth.DynamoClient", return_value=db), \
             patch("api.auth._send_magic_link") as mock_send:
            resp = handle_magic_link(_make_event("POST", "/auth/magic-link", {"email": "steven@dolltribe.com"}))
        assert resp["statusCode"] == 200
        mock_send.assert_called_once()

    def test_magic_link_token_stored(self, db):
        cid = db.put_contact(_admin_contact_data())
        from api.auth import handle_magic_link
        with patch("api.auth.DynamoClient", return_value=db), \
             patch("api.auth._send_magic_link") as mock_send:
            handle_magic_link(_make_event("POST", "/auth/magic-link", {"email": "steven@dolltribe.com"}))
        # Verify token was created by checking the call args
        call_args = mock_send.call_args
        token = call_args[0][1]   # (email, token, contact_id)
        item  = db.get_token(cid, token)
        assert item is not None
        assert item["token_type"] == "magic_link"


class TestVerify:
    def test_valid_token_returns_200_and_cookie(self, db):
        cid   = db.put_contact(_admin_contact_data())
        token = db.create_magic_link_token(cid, ttl_minutes=15)
        from api.auth import handle_verify
        with patch("api.auth.DynamoClient", return_value=db):
            event         = _make_event("GET", "/auth/verify")
            event["queryStringParameters"] = {"token": token, "cid": cid}
            resp          = handle_verify(event)
        assert resp["statusCode"] == 200
        # Session cookies should be set
        cookies = resp.get("cookies", [])
        assert any("er_session=" in c for c in cookies)

    def test_magic_link_consumed_after_use(self, db):
        cid   = db.put_contact(_admin_contact_data())
        token = db.create_magic_link_token(cid, ttl_minutes=15)
        from api.auth import handle_verify
        with patch("api.auth.DynamoClient", return_value=db):
            event = _make_event("GET", "/auth/verify")
            event["queryStringParameters"] = {"token": token, "cid": cid}
            handle_verify(event)
        # Token should be gone
        assert db.get_token(cid, token) is None

    def test_invalid_token_returns_401(self, db):
        cid = db.put_contact(_admin_contact_data())
        from api.auth import handle_verify
        with patch("api.auth.DynamoClient", return_value=db):
            event = _make_event("GET", "/auth/verify")
            event["queryStringParameters"] = {"token": "bad-token", "cid": cid}
            resp  = handle_verify(event)
        assert resp["statusCode"] == 401

    def test_missing_params_returns_400(self, db):
        from api.auth import handle_verify
        with patch("api.auth.DynamoClient", return_value=db):
            event = _make_event("GET", "/auth/verify")
            event["queryStringParameters"] = {}
            resp  = handle_verify(event)
        assert resp["statusCode"] == 400


class TestLogout:
    def test_logout_deletes_session(self, db):
        cid   = db.put_contact(_admin_contact_data())
        token = db.create_session_token(cid, ttl_days=7)
        from api.auth import handle_logout
        with patch("api.auth.DynamoClient", return_value=db):
            resp = handle_logout(_make_event("POST", "/auth/logout", cookies={
                "er_session": token,
                "er_contact": cid,
            }))
        assert resp["statusCode"] == 200
        assert db.get_token(cid, token) is None

    def test_logout_clears_cookie(self, db):
        from api.auth import handle_logout
        with patch("api.auth.DynamoClient", return_value=db):
            resp = handle_logout(_make_event("POST", "/auth/logout"))
        header = resp.get("headers", {}).get("Set-Cookie", "")
        assert "Max-Age=0" in header


class TestGetAuthenticatedContact:
    def test_valid_session_returns_contact(self, db):
        cid   = db.put_contact(_admin_contact_data())
        token = db.create_session_token(cid, ttl_days=7)
        from api.auth import get_authenticated_contact
        with patch("api.auth.DynamoClient", return_value=db):
            contact = get_authenticated_contact(_make_event("GET", "/contacts", cookies={
                "er_session": token,
                "er_contact": cid,
            }))
        assert contact is not None
        assert contact["email"] == "steven@dolltribe.com"

    def test_no_cookies_returns_none(self, db):
        from api.auth import get_authenticated_contact
        with patch("api.auth.DynamoClient", return_value=db):
            assert get_authenticated_contact(_make_event("GET", "/contacts")) is None

    def test_bad_token_returns_none(self, db):
        cid = db.put_contact(_admin_contact_data())
        from api.auth import get_authenticated_contact
        with patch("api.auth.DynamoClient", return_value=db):
            assert get_authenticated_contact(_make_event("GET", "/contacts", cookies={
                "er_session": "bad",
                "er_contact": cid,
            })) is None
