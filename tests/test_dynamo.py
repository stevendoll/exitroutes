"""
Tests for DynamoClient — all DB operations, run against moto mock.
"""

import pytest
from tests.conftest import make_lead
from api.db.dynamo import DUPLICATE


class TestPutContact:
    def test_put_returns_id(self, db):
        data = make_lead()
        cid  = db.put_contact(data)
        assert isinstance(cid, str)
        assert len(cid) == 36  # UUID

    def test_put_dedup_same_fingerprint(self, db):
        data = make_lead(fingerprint="fp-unique-xyz")
        db.put_contact(data)
        result = db.put_contact(make_lead(fingerprint="fp-unique-xyz"))
        assert result == DUPLICATE

    def test_put_no_fingerprint_allows_duplicates(self, db):
        """Contacts without fingerprint (e.g. customers) are not deduped."""
        data = make_lead(fingerprint="", contact_type="customer")
        id1  = db.put_contact(data)
        id2  = db.put_contact(data)
        assert id1 != DUPLICATE
        assert id2 != DUPLICATE
        assert id1 != id2


class TestGetContact:
    def test_get_existing(self, db):
        data = make_lead()
        cid  = db.put_contact(data)
        got  = db.get_contact(cid)
        assert got is not None
        assert got["contact_id"] == cid
        assert got["business_name"] == "Test Pest Co"

    def test_get_missing_returns_none(self, db):
        assert db.get_contact("nonexistent-id") is None

    def test_get_strips_pk_sk(self, db):
        cid = db.put_contact(make_lead())
        got = db.get_contact(cid)
        assert "PK" not in got
        assert "SK" not in got


class TestUpdateContact:
    def test_update_outreach_status(self, db):
        cid    = db.put_contact(make_lead())
        result = db.update_contact(cid, {"outreach_status": "contacted"})
        assert result["outreach_status"] == "contacted"

    def test_update_notes(self, db):
        cid    = db.put_contact(make_lead())
        result = db.update_contact(cid, {"outreach_notes": "Left voicemail"})
        assert result["outreach_notes"] == "Left voicemail"

    def test_update_rejects_unknown_keys(self, db):
        cid    = db.put_contact(make_lead())
        result = db.update_contact(cid, {"pain_score": 99, "outreach_notes": "ok"})
        got    = db.get_contact(cid)
        # pain_score should NOT be changed; only outreach_notes
        assert str(got.get("pain_score")) == "8"  # original value


class TestListContacts:
    def test_list_by_type(self, db):
        for _ in range(3):
            db.put_contact(make_lead(fingerprint=""))
        for _ in range(2):
            db.put_contact(make_lead(contact_type="customer", source="intake", fingerprint=""))
        leads, _ = db.list_contacts(contact_type="lead")
        assert len(leads) == 3

    def test_list_by_source(self, db):
        db.put_contact(make_lead(source="capterra", fingerprint="fp1"))
        db.put_contact(make_lead(source="capterra", fingerprint="fp2"))
        db.put_contact(make_lead(source="g2",       fingerprint="fp3"))
        items, _ = db.list_contacts(source="capterra")
        assert len(items) == 2

    def test_list_by_status(self, db):
        for _ in range(4):
            db.put_contact(make_lead(outreach_status="new",       fingerprint=""))
        db.put_contact(make_lead(outreach_status="contacted", fingerprint=""))
        items, _ = db.list_contacts(status="new")
        assert len(items) == 4

    def test_pain_sort_descending(self, db):
        for score in (3, 7, 9):
            db.put_contact(make_lead(pain_score=score, fingerprint=""))
        items, _ = db.list_contacts(contact_type="lead")
        scores = [int(i["pain_score"]) for i in items]
        assert scores == sorted(scores, reverse=True)


class TestGetByFingerprint:
    def test_found(self, db):
        db.put_contact(make_lead(fingerprint="fp-abc"))
        got = db.get_contact_by_fingerprint("fp-abc")
        assert got is not None
        assert got["fingerprint"] == "fp-abc"

    def test_not_found(self, db):
        assert db.get_contact_by_fingerprint("no-such-fp") is None


class TestSessionTokens:
    def test_create_and_retrieve_magic_link(self, db):
        cid   = db.put_contact(make_lead())
        token = db.create_magic_link_token(cid, ttl_minutes=15)
        item  = db.get_token(cid, token)
        assert item is not None
        assert item["token_type"] == "magic_link"

    def test_create_and_retrieve_session(self, db):
        cid   = db.put_contact(make_lead())
        token = db.create_session_token(cid, ttl_days=7)
        item  = db.get_token(cid, token)
        assert item is not None
        assert item["token_type"] == "session"

    def test_delete_token(self, db):
        cid   = db.put_contact(make_lead())
        token = db.create_session_token(cid)
        db.delete_token(cid, token)
        assert db.get_token(cid, token) is None

    def test_expired_token_returns_none(self, db):
        import time
        from unittest.mock import patch
        cid   = db.put_contact(make_lead())
        # Create token with 1-minute TTL, then fake time to be 2 minutes later
        token = db.create_magic_link_token(cid, ttl_minutes=1)
        future_epoch = int(time.time()) + 120  # 2 minutes ahead
        with patch("time.time", return_value=future_epoch):
            assert db.get_token(cid, token) is None


class TestScrapeRuns:
    def test_put_and_get_run(self, db):
        run_id = "run-001"
        db.put_scrape_run(run_id, ["capterra", "reddit"])
        got = db.get_scrape_run(run_id)
        assert got["run_id"] == run_id
        assert got["status"] == "running"
        assert "capterra" in got["sources"]

    def test_complete_run(self, db):
        run_id = "run-002"
        db.put_scrape_run(run_id, ["g2"])
        db.complete_scrape_run(run_id, {"leads_found": 5, "leads_new": 3})
        got = db.get_scrape_run(run_id)
        assert got["status"] == "completed"
        assert got["stats"]["leads_new"] == 3
