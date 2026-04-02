import io
import pytest
from parser import FieldRoutesParser

CUSTOMERS_CSV = """\
CustomerID,FirstName,LastName,CompanyName,BillingAddress1,BillingCity,BillingState,BillingZip,ServiceAddress1,ServiceCity,ServiceState,ServiceZip,Phone1,Phone2,Email,Balance,Notes,IsActive,CreatedDate
1001,James,Thornton,,142 Oak Ridge Rd,Marietta,GA,30062,142 Oak Ridge Rd,Marietta,GA,30062,770-555-0142,,jthornton@gmail.com,0.00,,1,2021-03-15
1002,Maria,Gonzalez,,891 Sunset Blvd,Atlanta,GA,30308,,,,(404) 555-0891,,mariag@hotmail.com,45.00,,1,2021-07-22
"""

SUBSCRIPTIONS_CSV = """\
SubscriptionID,CustomerID,ServiceType,Frequency,Price,NextServiceDate,TechnicianID,Status,AutoPay,ContractStartDate,ContractEndDate
SUB-2001,1001,General Pest Control,Monthly,89.00,2026-04-15,T03,Active,1,2021-03-15,
SUB-2002,1002,General Pest Control,Quarterly,65.00,2026-05-01,T01,Active,1,2021-07-22,
"""

SERVICE_HISTORY_CSV = """\
AppointmentID,CustomerID,SubscriptionID,ServiceDate,TechnicianID,Status,ChemicalsUsed,AmountApplied,Notes,InvoiceAmount,AmountPaid
APT-3001,1001,SUB-2001,2026-03-15,T03,Completed,Temprid SC,1.2 oz,,89.00,89.00
APT-3002,1002,SUB-2002,2026-01-20,T01,Completed,Suspend SC,0.8 oz,,65.00,65.00
"""

UNRECOGNIZED_CSV = """\
foo,bar,baz
1,2,3
"""


def make_file(content: str) -> io.BytesIO:
    return io.BytesIO(content.encode("utf-8"))


class TestFieldRoutesParser:
    def setup_method(self):
        self.parser = FieldRoutesParser()

    def test_detects_customers(self):
        result = self.parser.parse({"customers.csv": make_file(CUSTOMERS_CSV)})
        assert "customers" in result
        assert len(result["customers"]) == 2

    def test_detects_subscriptions(self):
        result = self.parser.parse({"subs.csv": make_file(SUBSCRIPTIONS_CSV)})
        assert "subscriptions" in result
        assert len(result["subscriptions"]) == 2

    def test_detects_service_history(self):
        result = self.parser.parse({"history.csv": make_file(SERVICE_HISTORY_CSV)})
        assert "service_history" in result
        assert len(result["service_history"]) == 2

    def test_parses_multiple_files(self):
        result = self.parser.parse({
            "customers.csv":    make_file(CUSTOMERS_CSV),
            "subs.csv":         make_file(SUBSCRIPTIONS_CSV),
            "history.csv":      make_file(SERVICE_HISTORY_CSV),
        })
        assert set(result.keys()) == {"customers", "subscriptions", "service_history"}

    def test_skips_unrecognized_file(self):
        result = self.parser.parse({"random.csv": make_file(UNRECOGNIZED_CSV)})
        assert result == {}

    def test_strips_whitespace_from_headers(self):
        csv_with_spaces = CUSTOMERS_CSV.replace("CustomerID", " CustomerID ")
        result = self.parser.parse({"customers.csv": make_file(csv_with_spaces)})
        assert "customers" in result
        assert "CustomerID" in result["customers"].columns

    def test_handles_bom_encoding(self):
        bom_content = "\ufeff" + CUSTOMERS_CSV
        result = self.parser.parse({"customers.csv": make_file(bom_content)})
        assert "customers" in result
        # BOM should be stripped from column names
        assert "CustomerID" in result["customers"].columns

    def test_drops_all_empty_rows(self):
        csv_with_blanks = CUSTOMERS_CSV + "\n\n\n"
        result = self.parser.parse({"customers.csv": make_file(csv_with_blanks)})
        assert len(result["customers"]) == 2
