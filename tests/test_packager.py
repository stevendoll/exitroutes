import io
import zipfile
import pytest
import pandas as pd
from packager import MigrationPackager


MAPPED_CUSTOMERS = pd.DataFrame({
    "first_name": ["James", "Maria"],
    "last_name":  ["Thornton", "Gonzalez"],
    "email":      ["jthornton@gmail.com", "mariag@hotmail.com"],
    "balance":    ["0.00", "45.00"],
})

MAPPED_SUBSCRIPTIONS = pd.DataFrame({
    "customer_id":  ["1001", "1002"],
    "service_type": ["General Pest Control", "General Pest Control"],
    "status":       ["Active", "Active"],
})

MAPPED_SERVICE_HISTORY = pd.DataFrame({
    "customer_id":  ["1001"],
    "service_date": ["2026-03-15"],
    "status":       ["Completed"],
})

EMPTY_REPORT = {
    "total_customers": 2,
    "active_customers": 2,
    "missing_email": [],
    "invalid_phone": [],
    "duplicate_flags": [],
    "missing_address_fields": [],
}

REPORT_WITH_WARNINGS = {
    "total_customers": 2,
    "active_customers": 1,
    "missing_email": ["1002"],
    "invalid_phone": ["1003"],
    "duplicate_flags": [("1001", "1004")],
    "missing_address_fields": [],
}


def open_zip(raw: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(raw))


class TestPackager:
    def setup_method(self):
        self.packager = MigrationPackager()
        self.tables = {
            "customers":      MAPPED_CUSTOMERS,
            "subscriptions":  MAPPED_SUBSCRIPTIONS,
            "service_history": MAPPED_SERVICE_HISTORY,
        }

    def test_returns_bytes(self):
        result = self.packager.package(self.tables, EMPTY_REPORT, "GorillaDesk")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_valid_zip(self):
        result = self.packager.package(self.tables, EMPTY_REPORT, "GorillaDesk")
        assert zipfile.is_zipfile(io.BytesIO(result))

    def test_contains_customers_csv(self):
        result = self.packager.package(self.tables, EMPTY_REPORT, "GorillaDesk")
        zf = open_zip(result)
        assert "customers.csv" in zf.namelist()

    def test_contains_migration_report(self):
        result = self.packager.package(self.tables, EMPTY_REPORT, "GorillaDesk")
        zf = open_zip(result)
        assert "migration_report.txt" in zf.namelist()

    def test_contains_readme(self):
        result = self.packager.package(self.tables, EMPTY_REPORT, "GorillaDesk")
        zf = open_zip(result)
        assert "README.txt" in zf.namelist()

    def test_report_includes_destination(self):
        result = self.packager.package(self.tables, EMPTY_REPORT, "GorillaDesk")
        zf = open_zip(result)
        report_text = zf.read("migration_report.txt").decode()
        assert "GorillaDesk" in report_text

    def test_report_includes_summary_counts(self):
        result = self.packager.package(self.tables, EMPTY_REPORT, "GorillaDesk")
        zf = open_zip(result)
        report_text = zf.read("migration_report.txt").decode()
        assert "Total customers processed: 2" in report_text

    def test_report_includes_warnings(self):
        result = self.packager.package(self.tables, REPORT_WITH_WARNINGS, "GorillaDesk")
        zf = open_zip(result)
        report_text = zf.read("migration_report.txt").decode()
        assert "Missing email" in report_text
        assert "1002" in report_text
        assert "Invalid" in report_text

    def test_open_invoices_extracted(self):
        # Customers with balance > 0 should appear in open_invoices.csv
        original = pd.DataFrame({
            "CustomerID": ["1001", "1002"],
            "balance":    ["0.00", "45.00"],
        })
        result = self.packager.package(
            self.tables, EMPTY_REPORT, "GorillaDesk",
            original_tables={"customers": original},
        )
        zf = open_zip(result)
        assert "open_invoices.csv" in zf.namelist()
        content = zf.read("open_invoices.csv").decode()
        assert "1002" in content
        assert "1001" not in content

    def test_readme_gorilladesk_content(self):
        result = self.packager.package(self.tables, EMPTY_REPORT, "GorillaDesk")
        zf = open_zip(result)
        readme = zf.read("README.txt").decode()
        assert "GorillaDesk" in readme

    def test_readme_jobber_content(self):
        result = self.packager.package(self.tables, EMPTY_REPORT, "Jobber")
        zf = open_zip(result)
        readme = zf.read("README.txt").decode()
        assert "Jobber" in readme

    def test_clean_report_says_no_warnings(self):
        result = self.packager.package(self.tables, EMPTY_REPORT, "GorillaDesk")
        zf = open_zip(result)
        report_text = zf.read("migration_report.txt").decode()
        assert "No warnings" in report_text
