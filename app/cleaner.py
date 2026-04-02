import re
import logging
import pandas as pd

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r"\D")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_phone(raw: str) -> str | None:
    """Return (555) 555-5555 or None if unformattable."""
    if not raw or not isinstance(raw, str):
        return None
    digits = PHONE_RE.sub("", raw)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if len(digits) == 11 and digits[0] == "1":
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return None


def _validate_email(val: str | None) -> bool:
    if not val or not isinstance(val, str):
        return False
    return bool(EMAIL_RE.match(val.strip()))


class DataCleaner:
    """Cleans and validates parsed FieldRoutes DataFrames."""

    def clean(
        self, tables: dict[str, pd.DataFrame]
    ) -> tuple[dict[str, pd.DataFrame], dict]:
        """
        Returns:
            (cleaned_tables, validation_report)
        """
        report: dict = {
            "total_customers": 0,
            "active_customers": 0,
            "missing_email": [],
            "invalid_phone": [],
            "duplicate_flags": [],
            "missing_address_fields": [],
        }

        cleaned = {}

        if "customers" in tables:
            df, report = self._clean_customers(tables["customers"], report)
            cleaned["customers"] = df

        if "subscriptions" in tables:
            cleaned["subscriptions"] = self._clean_subscriptions(tables["subscriptions"])

        if "service_history" in tables:
            cleaned["service_history"] = self._clean_service_history(tables["service_history"])

        return cleaned, report

    def _clean_customers(
        self, df: pd.DataFrame, report: dict
    ) -> tuple[pd.DataFrame, dict]:
        df = df.copy()

        # Strip whitespace from all string columns
        str_cols = df.select_dtypes(include="object").columns
        df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())

        # Phone normalization
        for col in ("Phone1", "Phone2"):
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda v: _normalize_phone(v) if pd.notna(v) else None
                )

        # Flag invalid/missing Phone1
        if "Phone1" in df.columns:
            bad_phone = df[df["Phone1"].isna()]["CustomerID"].dropna().tolist()
            report["invalid_phone"] = bad_phone
            if bad_phone:
                logger.warning("Invalid/missing Phone1 for %d customers", len(bad_phone))

        # Email validation
        if "Email" in df.columns:
            missing_email = df[~df["Email"].apply(_validate_email)]["CustomerID"].dropna().tolist()
            report["missing_email"] = missing_email
            if missing_email:
                logger.warning("Missing/invalid email for %d customers", len(missing_email))

        # Service address fallback to billing
        sa_fields = [("ServiceAddress1", "BillingAddress1"),
                     ("ServiceAddress2", "BillingAddress2"),
                     ("ServiceCity", "BillingCity"),
                     ("ServiceState", "BillingState"),
                     ("ServiceZip", "BillingZip")]
        for sa, ba in sa_fields:
            if sa in df.columns and ba in df.columns:
                mask = df[sa].isna()
                df.loc[mask, sa] = df.loc[mask, ba]

        # Flag: address_is_same
        if all(c in df.columns for c in ("ServiceAddress1", "BillingAddress1")):
            df["address_is_same"] = df["ServiceAddress1"] == df["BillingAddress1"]

        # Address completeness check
        addr_cols = ["BillingCity", "BillingState", "BillingZip"]
        if all(c in df.columns for c in addr_cols):
            incomplete = df[df[addr_cols].isna().any(axis=1)]["CustomerID"].dropna().tolist()
            report["missing_address_fields"] = incomplete

        # Title-case street addresses
        for col in ("BillingAddress1", "ServiceAddress1"):
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda v: v.title() if isinstance(v, str) else v
                )

        # Deduplication detection
        dupes: list[tuple[str, str]] = []
        if "CustomerID" in df.columns:
            # Exact CustomerID duplicates
            dupe_ids = df[df.duplicated("CustomerID", keep=False)]["CustomerID"].dropna().unique()
            for cid in dupe_ids:
                group = df[df["CustomerID"] == cid]["CustomerID"].tolist()
                if len(group) > 1:
                    dupes.append(tuple(group[:2]))

            # Same email
            if "Email" in df.columns:
                valid_emails = df[df["Email"].apply(_validate_email)]
                email_dupes = valid_emails[valid_emails.duplicated("Email", keep=False)]
                for email, group in email_dupes.groupby("Email"):
                    ids = group["CustomerID"].tolist()
                    if len(ids) >= 2:
                        dupes.append((ids[0], ids[1]))

            # Same service address + last name
            addr_key_cols = [c for c in ("LastName", "ServiceAddress1", "ServiceZip") if c in df.columns]
            if len(addr_key_cols) == 3:
                addr_dupes = df[df.duplicated(addr_key_cols, keep=False) & df[addr_key_cols].notna().all(axis=1)]
                for _, group in addr_dupes.groupby(addr_key_cols):
                    ids = group["CustomerID"].tolist()
                    if len(ids) >= 2:
                        pair = (ids[0], ids[1])
                        if pair not in dupes:
                            dupes.append(pair)

        report["duplicate_flags"] = list(dict.fromkeys(dupes))  # deduplicate pairs

        # Active / inactive split (keep both, add label)
        if "IsActive" in df.columns:
            df["IsActive"] = df["IsActive"].map({"1": True, "0": False, "True": True, "False": False}).fillna(False)
            report["active_customers"] = int(df["IsActive"].sum())
        report["total_customers"] = len(df)

        return df, report

    def _clean_subscriptions(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        str_cols = df.select_dtypes(include="object").columns
        df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())
        return df

    def _clean_service_history(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        str_cols = df.select_dtypes(include="object").columns
        df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())
        return df
