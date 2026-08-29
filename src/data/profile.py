"""Generate a data profiling report from ingested tables. (Task 0.2)

Reads the interim (type-cast) tables and produces reports/data_profile.md
covering: row counts, schema/dtypes, missing values, duplicates on the
documented grain, and cardinality of key columns.

This module does NOT clean or modify data — it only reports on it.
"""

from pathlib import Path

import pandas as pd

from src.utils.config import INTERIM_DATA_DIR, REPORTS_DIR

# Documented grain (primary key) per table, per docs/architecture.md section 1.
# A tuple means a composite key.
_GRAIN: dict[str, tuple[str, ...]] = {
    "customers": ("customer_id",),
    "orders": ("order_id",),
    "order_items": ("order_id", "order_item_id"),
    "order_payments": ("order_id", "payment_sequential"),
    "order_reviews": ("review_id", "order_id"),
    "products": ("product_id",),
    "sellers": ("seller_id",),
    "geolocation": (),  # raw grain is not row-unique; documented separately
    "category_translation": ("product_category_name",),
}


def load_interim_tables() -> dict[str, pd.DataFrame]:
    """Load all interim Parquet tables produced by ingest.py.

    Returns
    -------
    dict[str, pd.DataFrame]

    Raises
    ------
    FileNotFoundError
        If a table's interim Parquet file doesn't exist yet
        (i.e. ingest.py hasn't been run).
    """
    tables = {}
    for path in sorted(INTERIM_DATA_DIR.glob("*.parquet")):
        tables[path.stem] = pd.read_parquet(path)
    if not tables:
        raise FileNotFoundError(
            f"No interim Parquet files found in {INTERIM_DATA_DIR}. "
            "Run `python -m src.data.ingest` first."
        )
    return tables


def profile_table(name: str, df: pd.DataFrame) -> str:
    """Build the Markdown profiling section for a single table.

    Parameters
    ----------
    name : str
    df : pd.DataFrame

    Returns
    -------
    str
        A Markdown section (starts with "## <name>").
    """
    lines = [f"## `{name}`", ""]
    lines.append(f"- **Rows:** {len(df):,}")
    lines.append(f"- **Columns:** {len(df.columns)}")
    lines.append("")

    # Schema table
    lines.append("| Column | Dtype | Missing (n) | Missing (%) |")
    lines.append("|---|---|---|---|")
    n = len(df)
    for col in df.columns:
        missing_n = int(df[col].isna().sum())
        missing_pct = (missing_n / n * 100) if n else 0.0
        lines.append(f"| `{col}` | {df[col].dtype} | {missing_n:,} | {missing_pct:.2f}% |")
    lines.append("")

    # Duplicates on documented grain
    grain = _GRAIN.get(name, ())
    if grain and all(c in df.columns for c in grain):
        dup_count = int(df.duplicated(subset=list(grain)).sum())
        unique_count = df[list(grain)].drop_duplicates().shape[0]
        lines.append(
            f"- **Grain:** `{', '.join(grain)}` — "
            f"{unique_count:,} unique combinations, "
            f"**{dup_count:,} duplicate rows** on this key"
        )
    elif not grain:
        lines.append(
            "- **Grain:** not row-unique before aggregation "
            "(see architecture notes for this table)"
        )
    lines.append("")

    return "\n".join(lines)


def known_findings_report(tables: dict[str, pd.DataFrame]) -> str:
    """Reproduce the specific cross-table findings documented in
    docs/architecture.md section 1, verified programmatically here
    rather than assumed from manual exploration.

    Parameters
    ----------
    tables : dict[str, pd.DataFrame]

    Returns
    -------
    str
        A Markdown section titled "Known Findings Verification".
    """
    lines = ["## Known Findings Verification", ""]

    customers = tables["customers"]
    orders = tables["orders"]
    order_items = tables["order_items"]
    order_payments = tables["order_payments"]
    order_reviews = tables["order_reviews"]
    geolocation = tables["geolocation"]

    # 1. Repeat customers: customer_id rows vs distinct customer_unique_id
    n_customer_ids = customers["customer_id"].nunique()
    n_unique_customers = customers["customer_unique_id"].nunique()
    repeat_customers = n_customer_ids - n_unique_customers
    lines.append(
        f"- **Repeat customers:** {n_customer_ids:,} unique `customer_id` vs "
        f"{n_unique_customers:,} unique `customer_unique_id` -> "
        f"**{repeat_customers:,} customers with repeat purchases**"
    )

    # 2. Orders with zero item rows
    order_ids_with_items = set(order_items["order_id"].unique())
    all_order_ids = set(orders["order_id"].unique())
    missing_item_orders = all_order_ids - order_ids_with_items
    lines.append(
        f"- **Orders with no item rows:** {len(missing_item_orders):,}"
    )
    if missing_item_orders:
        status_counts = (
            orders[orders["order_id"].isin(missing_item_orders)]["order_status"]
            .value_counts()
        )
        breakdown = ", ".join(f"{s}: {c}" for s, c in status_counts.items())
        lines.append(f"  - Status breakdown: {breakdown}")

    # 3. Zero-value payments
    zero_payments = order_payments[order_payments["payment_value"] == 0]
    lines.append(
        f"- **Zero-value payments:** {len(zero_payments):,} total"
    )
    if len(zero_payments):
        type_counts = zero_payments["payment_type"].value_counts()
        breakdown = ", ".join(f"{t}: {c}" for t, c in type_counts.items())
        lines.append(f"  - By payment_type: {breakdown}")

    # 4. Delivered orders without a delivery date
    delivered_no_date = orders[
        (orders["order_status"] == "delivered")
        & (orders["order_delivered_customer_date"].isna())
    ]
    lines.append(
        f"- **`delivered` orders missing delivery date:** "
        f"{len(delivered_no_date):,}"
    )

    # 5. Canceled orders that DO have a delivery date
    canceled_with_date = orders[
        (orders["order_status"] == "canceled")
        & (orders["order_delivered_customer_date"].notna())
    ]
    lines.append(
        f"- **`canceled` orders with a delivery date:** "
        f"{len(canceled_with_date):,}"
    )

    # 6. review_id duplicates when NOT combined with order_id
    dup_review_id_alone = int(order_reviews.duplicated(subset=["review_id"]).sum())
    lines.append(
        f"- **Duplicate `review_id` (alone, not combined with `order_id`):** "
        f"{dup_review_id_alone:,} (confirms `review_id` alone is NOT a safe key)"
    )

    # 7. Geolocation exact duplicate rows
    dup_geo = int(geolocation.duplicated().sum())
    dup_geo_pct = dup_geo / len(geolocation) * 100 if len(geolocation) else 0.0
    lines.append(
        f"- **Geolocation exact duplicate rows:** {dup_geo:,} ({dup_geo_pct:.1f}%)"
    )

    lines.append("")
    return "\n".join(lines)


def build_report(tables: dict[str, pd.DataFrame]) -> str:
    """Assemble the full Markdown report for all tables.

    Parameters
    ----------
    tables : dict[str, pd.DataFrame]

    Returns
    -------
    str
        Full Markdown document.
    """
    parts = [
        "# Data Profile Report",
        "",
        "> Generated by `src/data/profile.py` (Task 0.2) from `data/interim/` tables.",
        "> Type-cast only — no cleaning has been applied yet.",
        "",
    ]
    for name in sorted(tables):
        parts.append(profile_table(name, tables[name]))
    parts.append(known_findings_report(tables))
    return "\n".join(parts)


def save_report(report_text: str) -> Path:
    """Write the report to reports/data_profile.md.

    Parameters
    ----------
    report_text : str

    Returns
    -------
    Path
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "data_profile.md"
    out_path.write_text(report_text, encoding="utf-8")
    return out_path


def run() -> Path:
    """Load interim tables, build the profile report, and save it.

    Returns
    -------
    Path
        Path to the written report.
    """
    print("Loading interim tables...")
    tables = load_interim_tables()
    print(f"  Loaded {len(tables)} tables: {sorted(tables)}")

    print("Building profile report...")
    report_text = build_report(tables)

    out_path = save_report(report_text)
    print(f"Report saved to: {out_path}")
    return out_path


if __name__ == "__main__":
    run()