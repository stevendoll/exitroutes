import pytest
import pandas as pd
from mapper import FieldMapper


CUSTOMERS_DF = pd.DataFrame({
    "CustomerID":       ["1001"],
    "FirstName":        ["James"],
    "LastName":         ["Thornton"],
    "CompanyName":      [""],
    "Email":            ["jthornton@gmail.com"],
    "Phone1":           ["(770) 555-0142"],
    "Phone2":           [None],
    "BillingAddress1":  ["142 Oak Ridge Rd"],
    "BillingAddress2":  [None],
    "BillingCity":      ["Marietta"],
    "BillingState":     ["GA"],
    "BillingZip":       ["30062"],
    "ServiceAddress1":  ["142 Oak Ridge Rd"],
    "ServiceAddress2":  [None],
    "ServiceCity":      ["Marietta"],
    "ServiceState":     ["GA"],
    "ServiceZip":       ["30062"],
    "Notes":            [""],
    "Balance":          ["0.00"],
    "IsActive":         [True],
    "CreatedDate":      ["2021-03-15"],
    "address_is_same":  [True],
})

SUBSCRIPTIONS_DF = pd.DataFrame({
    "SubscriptionID":   ["SUB-2001"],
    "CustomerID":       ["1001"],
    "ServiceType":      ["General Pest Control"],
    "Frequency":        ["Monthly"],
    "Price":            ["89.00"],
    "NextServiceDate":  ["2026-04-15"],
    "TechnicianID":     ["T03"],
    "Status":           ["Active"],
    "AutoPay":          ["1"],
    "ContractStartDate": ["2021-03-15"],
    "ContractEndDate":  [None],
})


class TestGorillaDesk:
    def setup_method(self):
        self.mapper = FieldMapper("GorillaDesk")

    def test_renames_first_name(self):
        result = self.mapper.map({"customers": CUSTOMERS_DF})
        assert "first_name" in result["customers"].columns
        assert "FirstName" not in result["customers"].columns

    def test_renames_email(self):
        result = self.mapper.map({"customers": CUSTOMERS_DF})
        assert "email" in result["customers"].columns

    def test_drops_customer_id(self):
        result = self.mapper.map({"customers": CUSTOMERS_DF})
        assert "CustomerID" not in result["customers"].columns
        assert "customer_id" not in result["customers"].columns

    def test_subscription_mapping(self):
        result = self.mapper.map({"subscriptions": SUBSCRIPTIONS_DF})
        assert "service_type" in result["subscriptions"].columns
        assert "ServiceType" not in result["subscriptions"].columns

    def test_value_preserved(self):
        result = self.mapper.map({"customers": CUSTOMERS_DF})
        assert result["customers"]["first_name"].iloc[0] == "James"


class TestJobber:
    def setup_method(self):
        self.mapper = FieldMapper("Jobber")

    def test_renames_to_jobber_columns(self):
        result = self.mapper.map({"customers": CUSTOMERS_DF})
        assert "First Name" in result["customers"].columns
        assert "Last Name" in result["customers"].columns
        assert "Email" in result["customers"].columns

    def test_billing_columns_renamed(self):
        result = self.mapper.map({"customers": CUSTOMERS_DF})
        assert "Billing Street" in result["customers"].columns
        assert "Billing City" in result["customers"].columns


class TestHousecallPro:
    def setup_method(self):
        self.mapper = FieldMapper("Housecall Pro")

    def test_renames_to_hcp_columns(self):
        result = self.mapper.map({"customers": CUSTOMERS_DF})
        assert "first_name" in result["customers"].columns
        assert "mobile_number" in result["customers"].columns
        assert "street" in result["customers"].columns


class TestUnknownDestination:
    def test_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown destination"):
            FieldMapper("ServiceTitan")


class TestPassthrough:
    def test_unknown_table_passes_through(self):
        mapper = FieldMapper("GorillaDesk")
        df = pd.DataFrame({"foo": [1], "bar": [2]})
        result = mapper.map({"unknown_table": df})
        assert "unknown_table" in result
        pd.testing.assert_frame_equal(result["unknown_table"], df)

    def test_all_three_destinations_available(self):
        for dest in ["GorillaDesk", "Jobber", "Housecall Pro"]:
            mapper = FieldMapper(dest)
            result = mapper.map({"customers": CUSTOMERS_DF})
            assert "customers" in result
            assert len(result["customers"]) == 1
