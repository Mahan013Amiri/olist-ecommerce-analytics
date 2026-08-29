"""Load raw CSV files, apply type casting only, save to data/interim/. (Task 0.2)

This module performs ingestion ONLY:
- Reads each of the 9 raw CSV files from data/raw/
- Casts columns to appropriate dtypes (dates -> datetime, ids -> string,
  numeric -> int/float)
- Writes each table as a Parquet file to data/interim/

No logical/business cleaning happens here (that's Task 1.1). No rows are
dropped, no duplicates are removed, no missing values are imputed.
"""

from pathlib import Path

import pandas as pd

from src.utils.config import INTERIM_DATA_DIR, RAW_DATA_DIR, RAW_TABLES

# Per-table casting spec: which columns are dates, and an explicit dtype map
# for everything else. Columns not listed keep pandas' inferred dtype.
_TABLE_SPECS: dict[str, dict] = {
    "customers": {
        "date_cols": [],
        "dtypes": {
            "customer_id": "string",
            "customer_unique_id": "string",
            "customer_zip_code_prefix": "Int64",
            "customer_city": "string",
            "customer_state": "string",
        },
    },
    "orders": {
        "date_cols": [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
        "dtypes": {
            "order_id": "string",
            "customer_id": "string",
            "order_status": "string",
        },
    },
    "order_items": {
        "date_cols": ["shipping_limit_date"],
        "dtypes": {
            "order_id": "string",
            "order_item_id": "Int64",
            "product_id": "string",
            "seller_id": "string",
            "price": "float64",
            "freight_value": "float64",
        },
    },
    "order_payments": {
        "date_cols": [],
        "dtypes": {
            "order_id": "string",
            "payment_sequential": "Int64",
            "payment_type": "string",
            "payment_installments": "Int64",
            "payment_value": "float64",
        },
    },
    "order_reviews": {
        "date_cols": ["review_creation_date", "review_answer_timestamp"],
        "dtypes": {
            "review_id": "string",
            "order_id": "string",
            "review_score": "Int64",
            "review_comment_title": "string",
            "review_comment_message": "string",
        },
    },
    "products": {
        "date_cols": [],
        "dtypes": {
            "product_id": "string",
            "product_category_name": "string",
            "product_name_lenght": "Int64",
            "product_description_lenght": "Int64",
            "product_photos_qty": "Int64",
            "product_weight_g": "Int64",
            "product_length_cm": "Int64",
            "product_height_cm": "Int64",
            "product_width_cm": "Int64",
        },
    },
    "sellers": {
        "date_cols": [],
        "dtypes": {
            "seller_id": "string",
            "seller_zip_code_prefix": "Int64",
            "seller_city": "string",
            "seller_state": "string",
        },
    },
    "geolocation": {
        "date_cols": [],
        "dtypes": {
            "geolocation_zip_code_prefix": "Int64",
            "geolocation_lat": "float64",
            "geolocation_lng": "float64",
            "geolocation_city": "string",
            "geolocation_state": "string",
        },
    },
    "category_translation": {
        "date_cols": [],
        "dtypes": {
            "product_category_name": "string",
            "product_category_name_english": "string",
        },
    },
}


def ingest_table(table_name: str) -> pd.DataFrame:
    """Load one raw CSV table and apply type casting only.

    Parameters
    ----------
    table_name : str
        Key into RAW_TABLES / _TABLE_SPECS (e.g. "orders", "customers").

    Returns
    -------
    pd.DataFrame
        The table with dtypes cast, no rows dropped or modified.

    Raises
    ------
    KeyError
        If table_name is not a known table.
    FileNotFoundError
        If the raw CSV file does not exist at the expected path.
    """
    if table_name not in RAW_TABLES:
        raise KeyError(
            f"Unknown table '{table_name}'. Expected one of {list(RAW_TABLES)}."
        )

    csv_path = RAW_DATA_DIR / RAW_TABLES[table_name]
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Raw file for '{table_name}' not found at: {csv_path}"
        )

    spec = _TABLE_SPECS.get(table_name, {"date_cols": [], "dtypes": {}})

    df = pd.read_csv(csv_path)

    # Cast explicit dtypes (only for columns that actually exist in the file)
    dtypes = {col: dt for col, dt in spec["dtypes"].items() if col in df.columns}
    df = df.astype(dtypes)

    # Cast date columns
    for col in spec["date_cols"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def save_interim(df: pd.DataFrame, table_name: str) -> Path:
    """Write a DataFrame to data/interim/<table_name>.parquet.

    Parameters
    ----------
    df : pd.DataFrame
    table_name : str

    Returns
    -------
    Path
        The path the file was written to.
    """
    INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = INTERIM_DATA_DIR / f"{table_name}.parquet"
    df.to_parquet(out_path, index=False)
    return out_path


def ingest_all() -> dict[str, pd.DataFrame]:
    """Ingest all 9 raw tables and save each to data/interim/.

    Returns
    -------
    dict[str, pd.DataFrame]
        Mapping of table_name -> ingested DataFrame.

    Notes
    -----
    If any single table fails to ingest, the error is raised immediately
    (fail fast) rather than silently skipping it, since a missing/broken
    raw file should stop the pipeline early.
    """
    tables: dict[str, pd.DataFrame] = {}
    for table_name in RAW_TABLES:
        print(f"Ingesting '{table_name}'...")
        try:
            df = ingest_table(table_name)
        except (KeyError, FileNotFoundError) as exc:
            print(f"  FAILED: {exc}")
            raise
        out_path = save_interim(df, table_name)
        print(f"  OK: {len(df):,} rows -> {out_path}")
        tables[table_name] = df
    return tables


if __name__ == "__main__":
    ingest_all()