"""Pipeline orchestration with caching: load_data(rebuild=False). (Task 1.3)

This module is the single entry point for getting clean, analysis-ready
tables. It wraps the chain 0.2 (ingest) -> 1.1 (clean) with a simple
file-existence cache: if the outputs of a stage already exist on disk and
rebuild=False, that stage is skipped and the outputs are read from parquet
instead of being recomputed.

No new cleaning/ingestion logic lives here — this module only decides
*whether* to call ingest.py / clean.py, and handles reading/writing via
src/utils/io.py.
"""

import pandas as pd

from src.data.clean import clean_all_tables
from src.data.ingest import ingest_all
from src.utils.config import CLEAN_TABLES, INTERIM_DATA_DIR, PROCESSED_DATA_DIR, RAW_TABLES
from src.utils.io import file_exists, read_parquet, write_parquet


def _processed_path(table_name: str):
    return PROCESSED_DATA_DIR / f"{table_name}_clean.parquet"


def _interim_path(table_name: str):
    return INTERIM_DATA_DIR / f"{table_name}.parquet"


def _all_processed_exist() -> bool:
    return all(file_exists(_processed_path(name)) for name in CLEAN_TABLES)


def _all_interim_exist() -> bool:
    return all(file_exists(_interim_path(name)) for name in RAW_TABLES)


def _load_processed_from_cache() -> dict[str, pd.DataFrame]:
    print("Loading clean tables from data/processed/ cache...")
    return {name: read_parquet(_processed_path(name)) for name in CLEAN_TABLES}


def _load_or_build_interim(rebuild: bool) -> dict[str, pd.DataFrame]:
    if not rebuild and _all_interim_exist():
        print("Loading raw-cast tables from data/interim/ cache...")
        return {name: read_parquet(_interim_path(name)) for name in RAW_TABLES}

    print("Interim cache missing or rebuild=True — running ingestion...")
    return ingest_all()


def load_data(rebuild: bool = False) -> dict[str, pd.DataFrame]:
    """Load the 8 cleaned tables, using on-disk caches when possible.

    Parameters
    ----------
    rebuild : bool, default False
        If False (default), reuse cached parquet files from
        data/processed/ (and data/interim/ if needed) whenever they exist.
        If True, ignore all caches and rerun ingestion + cleaning from the
        raw CSVs.

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys match CLEAN_TABLES: orders, order_items, payments, reviews,
        customers, products, sellers, geolocation.
    """
    if not rebuild and _all_processed_exist():
        return _load_processed_from_cache()

    interim = _load_or_build_interim(rebuild)

    print("Running per-table cleaning...")
    clean_tables = clean_all_tables(interim)

    print("Saving cleaned tables to data/processed/...")
    for name, df in clean_tables.items():
        out_path = write_parquet(df, _processed_path(name))
        print(f"  OK: {len(df):,} rows -> {out_path}")

    return clean_tables


if __name__ == "__main__":
    load_data(rebuild=False)