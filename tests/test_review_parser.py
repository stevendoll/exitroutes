"""
Tests for ReviewParser — pain scoring and signal detection.
"""

import pytest
from api.parsers.review_parser import ReviewParser, MIN_PAIN_SCORE


@pytest.fixture
def parser():
    return ReviewParser()


class TestPainScore:
    def test_data_hostage_owner_high_score(self, parser):
        """Owner citing data hostage and switching → expect score ≥ 8."""
        raw = {
            "rating":        1,
            "reviewer_role": "Owner",
            "cons_text":     "They hold your data hostage and want $500 for an incomplete backup. Impossible to leave.",
        }
        score = parser.calculate_pain_score(raw)
        assert score >= 8

    def test_switching_mention_mid_score(self, parser):
        """Switching mention only, 2-star review → expect 5–7."""
        raw = {
            "rating":    2,
            "cons_text": "We are switching to GorillaDesk next month.",
        }
        score = parser.calculate_pain_score(raw)
        assert 5 <= score <= 7

    def test_pricing_frustration_office_manager(self, parser):
        """Pricing complaint by office manager, 3-star → rating(1) + pricing(1) = 2."""
        raw = {
            "rating":        3,
            "reviewer_role": "Office Manager",
            "cons_text":     "The price keeps going up every year. Too expensive now.",
        }
        score = parser.calculate_pain_score(raw)
        assert score >= 2

    def test_positive_review_below_threshold(self, parser):
        """Positive review → should be filtered out (score < MIN_PAIN_SCORE)."""
        raw = {
            "rating":    5,
            "cons_text": "Nothing major to complain about.",
        }
        score = parser.calculate_pain_score(raw)
        assert score < MIN_PAIN_SCORE

    def test_support_complaint_owner_mid_score(self, parser):
        """Support complaint by owner → expect 4–6."""
        raw = {
            "rating":        2,
            "reviewer_role": "CEO",
            "cons_text":     "No support. No one answers the phone. Can't get help.",
        }
        score = parser.calculate_pain_score(raw)
        assert 4 <= score <= 6


class TestDetectSignals:
    def test_data_hostage_detected(self, parser):
        raw = {"cons_text": "They want $500 for our data export."}
        signals = parser.detect_signals(raw)
        assert signals["is_data_hostage"] is True

    def test_switching_detected(self, parser):
        raw = {"full_review_text": "We are switching from FieldRoutes to Jobber."}
        signals = parser.detect_signals(raw)
        assert signals["is_switching"] is True

    def test_support_detected(self, parser):
        raw = {"cons_text": "No one answers. Support is terrible."}
        signals = parser.detect_signals(raw)
        assert signals["is_support_issue"] is True

    def test_pricing_detected(self, parser):
        raw = {"cons_text": "Way too expensive. Price increases every year."}
        signals = parser.detect_signals(raw)
        assert signals["is_pricing_issue"] is True

    def test_no_signals_clean_review(self, parser):
        raw = {"cons_text": "Works fine for our small operation."}
        signals = parser.detect_signals(raw)
        assert signals["is_data_hostage"] is False
        assert signals["is_switching"]    is False
        assert signals["is_support_issue"] is False
        assert signals["is_pricing_issue"] is False


class TestFingerprint:
    def test_same_inputs_same_hash(self, parser):
        fp1 = parser.generate_fingerprint("capterra", "John O.", "Test Pest Co")
        fp2 = parser.generate_fingerprint("capterra", "John O.", "Test Pest Co")
        assert fp1 == fp2

    def test_different_source_different_hash(self, parser):
        fp1 = parser.generate_fingerprint("capterra", "John O.", "Test Pest Co")
        fp2 = parser.generate_fingerprint("g2",       "John O.", "Test Pest Co")
        assert fp1 != fp2

    def test_case_insensitive(self, parser):
        fp1 = parser.generate_fingerprint("capterra", "JOHN O.", "TEST PEST CO")
        fp2 = parser.generate_fingerprint("capterra", "john o.", "test pest co")
        assert fp1 == fp2


class TestParse:
    def test_parse_high_pain_returns_dict(self, parser):
        raw = {
            "rating":        1,
            "reviewer_role": "Owner",
            "reviewer_name": "Jane D.",
            "business_name": "Acme Pest",
            "cons_text":     "Data hostage. Switching to GorillaDesk.",
            "source_url":    "https://capterra.com/test",
        }
        result = parser.parse(raw, "capterra")
        assert result is not None
        assert result["contact_type"] == "lead"
        assert result["outreach_status"] == "new"
        assert result["source"] == "capterra"
        assert result["pain_score"] >= MIN_PAIN_SCORE

    def test_parse_low_pain_returns_none(self, parser):
        raw = {
            "rating":    5,
            "cons_text": "All good.",
        }
        assert parser.parse(raw, "capterra") is None

    def test_parse_includes_signals(self, parser):
        raw = {
            "rating":    1,
            "cons_text": "Data hostage. $500. Switching to Jobber.",
        }
        result = parser.parse(raw, "capterra")
        assert result["is_data_hostage"] is True
        assert result["is_switching"]    is True
