import json
import logging
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent / "config"

DESTINATION_CONFIGS = {
    "GorillaDesk":    "gorilladesk.json",
    "Jobber":         "jobber.json",
    "Housecall Pro":  "housecallpro.json",
}


class FieldMapper:
    """Maps cleaned FieldRoutes DataFrames to a destination platform's column names."""

    def __init__(self, destination: str):
        if destination not in DESTINATION_CONFIGS:
            raise ValueError(
                f"Unknown destination: {destination!r}. "
                f"Choose from: {list(DESTINATION_CONFIGS)}"
            )
        config_path = CONFIG_DIR / DESTINATION_CONFIGS[destination]
        with open(config_path) as f:
            self.config = json.load(f)
        self.destination = destination

    def map(self, tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """Apply column mapping for all provided tables."""
        mapped = {}
        for table, df in tables.items():
            if table not in self.config:
                logger.debug("No mapping config for table %s — passing through as-is", table)
                mapped[table] = df.copy()
                continue
            mapped[table] = self._map_table(df, table)
        return mapped

    def _map_table(self, df: pd.DataFrame, table: str) -> pd.DataFrame:
        table_config = self.config[table]
        column_map: dict[str, str] = table_config.get("column_map", {})
        drop_cols: list[str] = table_config.get("drop", [])

        df = df.copy()

        # Log unmapped source columns
        unmapped = [c for c in df.columns if c not in column_map and c not in drop_cols]
        if unmapped:
            logger.info(
                "%s → %s: unmapped columns (excluded from output): %s",
                table, self.destination, unmapped,
            )

        # Keep only columns that are in the map
        keep = [c for c in df.columns if c in column_map]
        df = df[keep]

        # Rename
        df = df.rename(columns=column_map)

        return df
