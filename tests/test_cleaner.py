import pytest
import pandas as pd
from cleaner import DataCleaner


def make_customers(**overrides) -> pd.DataFrame:
    base = {
        "CustomerID":       ["1001", "1002", "1003"],
        "FirstName":        ["James", "Maria", "Bob"],
        "LastName":         ["Thornton", "Gonzalez", "Smith"],
        "Phone1":           ["770-555-0142", "(404) 555-0891", "5551234567"],
        "Phone2":           [None, None, None],
        "Email":            ["jthornton@gmail.com", "mariag@hotmail.com", None],
        "BillingAddress1":  ["142 Oak Ridge Rd", "891 Sunset Blvd", "100 Main St"],
        "BillingCity":      ["Marietta", "Atlanta", "Decatur"],
        "BillingState":     ["GA", "GA", "GA"],
        "BillingZip":       ["30062", "30308", "30030"],
        "ServiceAddress1":  ["142 Oak Ridge Rd", None, "200 Other St"],
        "ServiceCity":      ["Marietta", None, "Decatur"],
        "ServiceState":     ["GA", None, "GA"],
        "ServiceZip":       ["30062", None, "30030"],
        "Balance":          ["0.00", "45.00", "0.00"],
        "Notes":            [None, None, None],
        "IsActive":         ["1", "1", "0"],
        "CreatedDate":      ["2021-03-15", "2021-07-22", "2020-01-01"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


class TestPhoneNormalization:
    def setup_method(self):
        self.cleaner = DataCleaner()

    def _clean(self, phone: str) -> str | None:
        df = make_customers(Phone1=["1001", phone, "1003"][:1] + [phone] + ["1003"][:1])
        # Just test the cleaner normalizes Phone1
        df = make_customers()
        df.loc[0, "Phone1"] = phone
        cleaned, _ = self.cleaner.clean({"customers": df})
        return cleaned["customers"].loc[0, "Phone1"]

    def test_dashes(self):
        assert self._clean("770-555-0142") == "(770) 555-0142"

    def test_parentheses(self):
        assert self._clean("(404) 555-0891") == "(404) 555-0891"

    def test_digits_only(self):
        assert self._clean("5551234567") == "(555) 123-4567"

    def test_dots(self):
        assert self._clean("770.555.4441") == "(770) 555-4441"

    def test_invalid_returns_none(self):
        import pandas as pd
        result = self._clean("555-PEST")
        assert result is None or pd.isna(result)

    def test_missing_returns_none(self):
        import pandas as pd
        result = self._clean("")
        assert result is None or pd.isna(result)


class TestEmailValidation:
    def setup_method(self):
        self.cleaner = DataCleaner()

    def test_flags_missing_email(self):
        df = make_customers()
        df.loc[2, "Email"] = None  # Bob has no email
        _, report = self.cleaner.clean({"customers": df})
        assert "1003" in report["missing_email"]

    def test_valid_emails_not_flagged(self):
        df = make_customers()
        _, report = self.cleaner.clean({"customers": df})
        assert "1001" not in report["missing_email"]
        assert "1002" not in report["missing_email"]


class TestServiceAddressFallback:
    def setup_method(self):
        self.cleaner = DataCleaner()

    def test_copies_billing_to_service_when_empty(self):
        df = make_customers()
        # Maria (1002) has no service address — should fall back to billing
        cleaned, _ = self.cleaner.clean({"customers": df})
        row = cleaned["customers"][cleaned["customers"]["CustomerID"] == "1002"].iloc[0]
        assert row["ServiceAddress1"] == "891 Sunset Blvd"
        assert row["ServiceCity"] == "Atlanta"

    def test_address_is_same_flag_true(self):
        df = make_customers()
        cleaned, _ = self.cleaner.clean({"customers": df})
        row = cleaned["customers"][cleaned["customers"]["CustomerID"] == "1001"].iloc[0]
        assert bool(row["address_is_same"]) is True

    def test_address_is_same_flag_false(self):
        df = make_customers()
        cleaned, _ = self.cleaner.clean({"customers": df})
        row = cleaned["customers"][cleaned["customers"]["CustomerID"] == "1003"].iloc[0]
        assert bool(row["address_is_same"]) is False


class TestDuplicateDetection:
    def setup_method(self):
        self.cleaner = DataCleaner()

    def test_detects_same_email(self):
        df = make_customers()
        # Give 1001 and 1003 the same email
        df.loc[2, "Email"] = "jthornton@gmail.com"
        _, report = self.cleaner.clean({"customers": df})
        pairs = [set(p) for p in report["duplicate_flags"]]
        assert {"1001", "1003"} in pairs


class TestActiveInactiveSplit:
    def setup_method(self):
        self.cleaner = DataCleaner()

    def test_counts_active_correctly(self):
        df = make_customers()  # 2 active, 1 inactive
        _, report = self.cleaner.clean({"customers": df})
        assert report["total_customers"] == 3
        assert report["active_customers"] == 2


class TestReportStructure:
    def setup_method(self):
        self.cleaner = DataCleaner()

    def test_report_has_all_keys(self):
        df = make_customers()
        _, report = self.cleaner.clean({"customers": df})
        assert "total_customers" in report
        assert "active_customers" in report
        assert "missing_email" in report
        assert "invalid_phone" in report
        assert "duplicate_flags" in report
        assert "missing_address_fields" in report

    def test_passes_through_subscriptions_unchanged(self):
        subs = pd.DataFrame({
            "SubscriptionID": ["S1"],
            "CustomerID": ["1001"],
            "ServiceType": ["General Pest Control"],
            "Status": ["Active"],
        })
        cleaned, _ = self.cleaner.clean({"subscriptions": subs})
        assert "subscriptions" in cleaned
        assert len(cleaned["subscriptions"]) == 1
