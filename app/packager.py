import io
import zipfile
import logging
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

IMPORT_GUIDES = {
    "GorillaDesk": """GORILLADESK IMPORT GUIDE
========================

1. CUSTOMERS  (customers.csv)
   Settings → Import Data → Customers
   Match columns as labelled. Set "first_name" and "last_name" as required.

2. SUBSCRIPTIONS  (subscriptions.csv)
   Settings → Import Data → Recurring Services
   Link each row to a customer via customer_id before importing.

3. SERVICE HISTORY  (service_history.csv)
   Settings → Import Data → Work Orders (Historical)
   Import after customers are in the system.

4. OPEN INVOICES  (open_invoices.csv)
   Use the "balance" field on the customer record, or create invoices manually
   for customers with a non-zero outstanding_balance.

NOTES
-----
- Import customers first — other imports reference them.
- If an import fails, check for missing required fields flagged in migration_report.txt.
- GorillaDesk support: support@gorilladesk.com
""",

    "Jobber": """JOBBER IMPORT GUIDE
===================

1. CLIENTS  (customers.csv)
   Gear icon → Import → Clients → Upload CSV
   Required fields: First Name or Company Name.

2. RECURRING JOBS  (subscriptions.csv)
   Create jobs manually after importing clients, or use Jobber's recurring job setup.
   The subscriptions.csv gives you all the data you need.

3. JOB HISTORY  (service_history.csv)
   Gear icon → Import → Work Requests (past jobs)
   Link each row to a client via Client ID.

4. OUTSTANDING BALANCES  (open_invoices.csv)
   Review and create invoices manually for clients with a non-zero Outstanding Balance.

NOTES
-----
- Import clients before jobs.
- Jobber support: support@getjobber.com
""",

    "Housecall Pro": """HOUSECALL PRO IMPORT GUIDE
===========================

1. CUSTOMERS  (customers.csv)
   Settings → Import → Customers → Upload CSV
   Required: first_name (or company_name) + street + city + state + zip.

2. JOBS / RECURRING  (subscriptions.csv)
   Use the data to manually set up recurring jobs after customers are imported.

3. JOB HISTORY  (service_history.csv)
   Settings → Import → Jobs (historical)
   Link each row to a customer via customer_id.

4. OPEN INVOICES  (open_invoices.csv)
   Create invoices manually for customers with a non-zero outstanding_balance.

NOTES
-----
- Housecall Pro support: support@housecallpro.com
""",
}


class MigrationPackager:
    """Generates a ZIP migration package from mapped DataFrames."""

    def package(
        self,
        mapped_tables: dict[str, pd.DataFrame],
        validation_report: dict,
        destination: str,
        original_tables: dict[str, pd.DataFrame] | None = None,
    ) -> bytes:
        """
        Returns ZIP file contents as bytes.

        Args:
            mapped_tables:      destination-formatted DataFrames
            validation_report:  dict from DataCleaner.clean()
            destination:        e.g. "GorillaDesk"
            original_tables:    pre-mapping tables (for open_invoices derivation)
        """
        buf = io.BytesIO()

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Core CSVs
            for table, df in mapped_tables.items():
                zf.writestr(f"{table}.csv", df.to_csv(index=False))

            # Open invoices — customers with balance > 0
            open_invoices = self._build_open_invoices(mapped_tables, original_tables, destination)
            if open_invoices is not None:
                zf.writestr("open_invoices.csv", open_invoices.to_csv(index=False))

            # Migration report
            zf.writestr(
                "migration_report.txt",
                self._build_report(validation_report, mapped_tables, destination),
            )

            # Import guide
            guide = IMPORT_GUIDES.get(destination, "See your platform's documentation for import instructions.")
            zf.writestr("README.txt", guide)

        return buf.getvalue()

    def _build_open_invoices(
        self,
        mapped_tables: dict[str, pd.DataFrame],
        original_tables: dict[str, pd.DataFrame] | None,
        destination: str,
    ) -> pd.DataFrame | None:
        src = original_tables or mapped_tables
        customers = src.get("customers")
        if customers is None:
            return None

        # Try to find the balance column
        balance_col = next(
            (c for c in customers.columns if "balance" in c.lower()), None
        )
        if balance_col is None:
            return None

        try:
            customers = customers.copy()
            customers["_balance_num"] = pd.to_numeric(customers[balance_col], errors="coerce").fillna(0)
            open_inv = customers[customers["_balance_num"] > 0].drop(columns=["_balance_num"])
            return open_inv if not open_inv.empty else None
        except Exception as e:
            logger.warning("Could not build open_invoices: %s", e)
            return None

    def _build_report(
        self,
        report: dict,
        mapped_tables: dict[str, pd.DataFrame],
        destination: str,
    ) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        subs_count = len(mapped_tables.get("subscriptions", pd.DataFrame()))
        hist_count = len(mapped_tables.get("service_history", pd.DataFrame()))

        lines = [
            "SWITCHKIT MIGRATION REPORT",
            f"Generated: {now}",
            f"Destination: {destination}",
            "",
            "SUMMARY",
            "-------",
            f"Total customers processed: {report.get('total_customers', 0)}",
            f"Active customers:          {report.get('active_customers', 0)}",
            f"Inactive customers:        {report.get('total_customers', 0) - report.get('active_customers', 0)}",
            f"Subscriptions migrated:    {subs_count}",
            f"Service records migrated:  {hist_count}",
            "",
        ]

        missing_email = report.get("missing_email", [])
        if missing_email:
            lines += [
                f"WARNINGS — Missing email ({len(missing_email)} customers):",
                "-" * 40,
            ]
            for cid in missing_email:
                lines.append(f"  CustomerID {cid}")
            lines.append("")

        invalid_phone = report.get("invalid_phone", [])
        if invalid_phone:
            lines += [
                f"WARNINGS — Invalid/missing phone ({len(invalid_phone)} customers):",
                "-" * 40,
            ]
            for cid in invalid_phone:
                lines.append(f"  CustomerID {cid}")
            lines.append("")

        dupes = report.get("duplicate_flags", [])
        if dupes:
            lines += [
                f"WARNINGS — Potential duplicates ({len(dupes)} pairs):",
                "-" * 40,
            ]
            for pair in dupes:
                lines.append(f"  CustomerID {pair[0]} and {pair[1]} may be the same customer")
            lines.append("")

        missing_addr = report.get("missing_address_fields", [])
        if missing_addr:
            lines += [
                f"WARNINGS — Incomplete address ({len(missing_addr)} customers):",
                "-" * 40,
            ]
            for cid in missing_addr:
                lines.append(f"  CustomerID {cid}")
            lines.append("")

        if not any([missing_email, invalid_phone, dupes, missing_addr]):
            lines += ["No warnings — all records look clean.", ""]

        lines += [
            "NEXT STEPS",
            "----------",
            "See README.txt for step-by-step import instructions.",
            "Questions? Email steven@t12n.ai",
        ]

        return "\n".join(lines)
