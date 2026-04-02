import io
import logging
import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "customers": {"CustomerID", "FirstName", "LastName", "Phone1", "IsActive"},
    "subscriptions": {"SubscriptionID", "CustomerID", "ServiceType", "Status"},
    "service_history": {"AppointmentID", "CustomerID", "ServiceDate", "Status"},
}

SIGNATURE_COLUMNS = {
    "customers": {"CustomerID", "FirstName", "LastName", "BillingAddress1"},
    "subscriptions": {"SubscriptionID", "CustomerID", "ServiceType", "Frequency"},
    "service_history": {"AppointmentID", "CustomerID", "ServiceDate", "ChemicalsUsed"},
}


class FieldRoutesParser:
    """Parses FieldRoutes CSV exports into typed DataFrames."""

    def parse(self, files: dict[str, str | bytes | io.IOBase]) -> dict[str, pd.DataFrame]:
        """
        Args:
            files: {filename_or_label: file_path_or_bytes_or_file_object}

        Returns:
            {"customers": df, "subscriptions": df, "service_history": df}
            Any table not found in the uploaded files is omitted.
        """
        results: dict[str, pd.DataFrame] = {}

        for label, source in files.items():
            df = self._read(label, source)
            if df is None:
                continue
            table = self._detect_table(df, label)
            if table is None:
                logger.warning("Could not identify table type for: %s — skipping", label)
                continue
            if table in results:
                logger.warning("Duplicate table type %s from %s — skipping", table, label)
                continue
            self._check_required_columns(df, table, label)
            results[table] = df
            logger.info("Loaded %s: %d rows, %d columns", table, len(df), len(df.columns))

        return results

    def _read(self, label: str, source) -> pd.DataFrame | None:
        read_kwargs = dict(
            dtype=str,
            na_values=["", "NULL", "null", "N/A", "n/a"],
            keep_default_na=False,
            skipinitialspace=True,
        )
        encodings = ["utf-8-sig", "utf-8", "latin-1"]

        for enc in encodings:
            try:
                if isinstance(source, (str, bytes)):
                    df = pd.read_csv(source, encoding=enc, **read_kwargs)
                else:
                    source.seek(0)
                    df = pd.read_csv(source, encoding=enc, **read_kwargs)
                df.columns = [c.strip() for c in df.columns]
                df = df.dropna(how="all")
                return df
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error("Failed to read %s: %s", label, e)
                return None

        logger.error("Could not decode %s with any known encoding", label)
        return None

    def _detect_table(self, df: pd.DataFrame, label: str) -> str | None:
        cols = set(df.columns)
        scores = {}
        for table, sig in SIGNATURE_COLUMNS.items():
            scores[table] = len(sig & cols)
        best = max(scores, key=scores.get)
        if scores[best] >= 2:
            return best
        # Fall back: check filename hint
        lower = label.lower()
        for table in SIGNATURE_COLUMNS:
            if table.replace("_", "") in lower.replace("_", "").replace("-", ""):
                return table
        return None

    def _check_required_columns(self, df: pd.DataFrame, table: str, label: str):
        missing = REQUIRED_COLUMNS[table] - set(df.columns)
        if missing:
            logger.warning("%s (%s) is missing expected columns: %s", table, label, missing)
        extra = set(df.columns) - set().union(*SIGNATURE_COLUMNS.values())
        if extra:
            logger.debug("%s has unmapped columns (will be passed through): %s", table, extra)
