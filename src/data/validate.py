"""Schema and business validation. (Task 1.2)

Two-stage validation per docs/architecture.md (بخش ۲ و ۳ / Task 1.2):

1. ``validate_schema``       — runs on interim tables, right after ingestion.
                                Fail-fast check: are the expected columns and
                                dtype *families* present?
2. ``validate_business_rules`` — runs on cleaned/processed tables. Checks
                                business rules (ranges, temporal consistency,
                                grain uniqueness, referential integrity) and
                                cross-checks the `flag_*` columns produced in
                                Task 1.1 (src/data/clean.py) rather than
                                re-detecting the same issues from scratch.

Both stages return a list of ``ValidationResult`` objects. Nothing here
raises on failure — failures are reported, not enforced, matching the
project's "light validation, not an execution engine" philosophy (same
spirit as docs/feature_registry.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.utils.config import (
    CLEAN_TABLES,
    INTERIM_DATA_DIR,
    PROCESSED_DATA_DIR,
    RAW_TABLES,
    REPORTS_DIR,
)
from src.utils.io import read_parquet


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """One row of the validation report."""

    check: str
    table: str
    passed: bool
    count: int | None = None
    details: str = ""

    def to_row(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        count_str = f"{self.count:,}" if self.count is not None else "-"
        details = self.details or ("OK" if self.passed else "")
        return f"| {self.table} | {self.check} | {status} | {count_str} | {details} |"


# ---------------------------------------------------------------------------
# Stage 1 — Schema Validation (post-ingestion, data/interim/)
# ---------------------------------------------------------------------------

# Expected columns and *dtype family* only (int / float / datetime / object).
# Deliberately lenient on exact numpy width (int32 vs int64) — the job here
# is to catch missing/renamed columns from a broken ingestion run, not to
# police dtype precision.
EXPECTED_SCHEMAS: dict[str, dict[str, str]] = {
    "orders": {
        "order_id": "object",
        "customer_id": "object",
        "order_status": "object",
        "order_purchase_timestamp": "datetime",
        "order_approved_at": "datetime",
        "order_delivered_carrier_date": "datetime",
        "order_delivered_customer_date": "datetime",
        "order_estimated_delivery_date": "datetime",
    },
    "order_items": {
        "order_id": "object",
        "order_item_id": "int",
        "product_id": "object",
        "seller_id": "object",
        "shipping_limit_date": "datetime",
        "price": "float",
        "freight_value": "float",
    },
    "order_payments": {
        "order_id": "object",
        "payment_sequential": "int",
        "payment_type": "object",
        "payment_installments": "int",
        "payment_value": "float",
    },
    "order_reviews": {
        "review_id": "object",
        "order_id": "object",
        "review_score": "int",
        "review_creation_date": "datetime",
        "review_answer_timestamp": "datetime",
    },
    "customers": {
        "customer_id": "object",
        "customer_unique_id": "object",
        "customer_zip_code_prefix": "int",
        "customer_city": "object",
        "customer_state": "object",
    },
    "products": {
        "product_id": "object",
        "product_category_name": "object",
        "product_weight_g": "int",
        "product_length_cm": "int",
        "product_height_cm": "int",
        "product_width_cm": "int",
    },
    "sellers": {
        "seller_id": "object",
        "seller_zip_code_prefix": "int",
        "seller_city": "object",
        "seller_state": "object",
    },
    "geolocation": {
        "geolocation_zip_code_prefix": "int",
        "geolocation_lat": "float",
        "geolocation_lng": "float",
    },
    "category_translation": {
        "product_category_name": "object",
        "product_category_name_english": "object",
    },
}


def _dtype_family(dtype_str: str) -> str:
    if dtype_str.startswith("datetime"):
        return "datetime"
    if dtype_str.startswith("int") or dtype_str.startswith("Int"):
        return "int"
    if dtype_str.startswith("float"):
        return "float"
    if dtype_str in ("object", "string", "category", "str"):
        return "object"
    if dtype_str.startswith("bool"):
        return "bool"
    return dtype_str


def validate_schema(
    df: pd.DataFrame, expected_schema: dict[str, str], table_name: str = ""
) -> list[ValidationResult]:
    """Check that ``df`` has the expected columns with compatible dtype families."""
    results: list[ValidationResult] = []

    missing = [c for c in expected_schema if c not in df.columns]
    results.append(
        ValidationResult(
            check="required_columns_present",
            table=table_name,
            passed=len(missing) == 0,
            count=len(missing),
            details=f"Missing: {missing}" if missing else "All expected columns present",
        )
    )

    mismatches = []
    for col, expected_dtype in expected_schema.items():
        if col not in df.columns:
            continue
        actual = str(df[col].dtype)
        if _dtype_family(actual) != _dtype_family(expected_dtype):
            mismatches.append(f"{col}: expected~{expected_dtype}, got {actual}")

    results.append(
        ValidationResult(
            check="dtype_family_matches",
            table=table_name,
            passed=len(mismatches) == 0,
            count=len(mismatches),
            details="; ".join(mismatches) if mismatches else "All dtypes compatible",
        )
    )

    return results


# ---------------------------------------------------------------------------
# Stage 2 — Business Validation (post-cleaning, data/processed/)
# ---------------------------------------------------------------------------


def _validate_orders(df: pd.DataFrame) -> list[ValidationResult]:
    results = []

    if "order_delivered_customer_date" in df.columns and "order_purchase_timestamp" in df.columns:
        has_both = df["order_delivered_customer_date"].notna() & df["order_purchase_timestamp"].notna()
        inverted = has_both & (df["order_delivered_customer_date"] < df["order_purchase_timestamp"])
        results.append(
            ValidationResult(
                check="delivery_date >= purchase_date",
                table="orders",
                passed=int(inverted.sum()) == 0,
                count=int(inverted.sum()),
                details="delivered_customer_date precedes purchase_timestamp",
            )
        )

    dup = int(df["order_id"].duplicated().sum())
    results.append(
        ValidationResult(
            check="order_id_unique (grain)",
            table="orders",
            passed=dup == 0,
            count=dup,
        )
    )

    # Cross-check Task 1.1 flags — informational, expected to be > 0.
    for flag_col, label in [
        ("flag_delivered_no_date", "delivered orders without a delivery date"),
        ("flag_canceled_with_date", "canceled orders with a delivery date"),
    ]:
        if flag_col in df.columns:
            results.append(
                ValidationResult(
                    check=f"{flag_col} (informational, from Task 1.1)",
                    table="orders",
                    passed=True,
                    count=int(df[flag_col].sum()),
                    details=label,
                )
            )

    return results


def _validate_order_items(df: pd.DataFrame) -> list[ValidationResult]:
    results = []

    neg_price = int((df["price"] < 0).sum())
    results.append(
        ValidationResult(
            check="price >= 0", table="order_items", passed=neg_price == 0, count=neg_price
        )
    )

    neg_freight = int((df["freight_value"] < 0).sum())
    results.append(
        ValidationResult(
            check="freight_value >= 0",
            table="order_items",
            passed=neg_freight == 0,
            count=neg_freight,
        )
    )

    dup = int(df.duplicated(subset=["order_id", "order_item_id"]).sum())
    results.append(
        ValidationResult(
            check="(order_id, order_item_id)_unique (grain)",
            table="order_items",
            passed=dup == 0,
            count=dup,
        )
    )

    return results


def _validate_payments(df: pd.DataFrame) -> list[ValidationResult]:
    results = []

    neg_value = int((df["payment_value"] < 0).sum())
    results.append(
        ValidationResult(
            check="payment_value >= 0", table="payments", passed=neg_value == 0, count=neg_value
        )
    )

    dup = int(df.duplicated(subset=["order_id", "payment_sequential"]).sum())
    results.append(
        ValidationResult(
            check="(order_id, payment_sequential)_unique (grain)",
            table="payments",
            passed=dup == 0,
            count=dup,
        )
    )

    for flag_col, label in [
        ("flag_zero_value_expected", "zero-value voucher payments (expected)"),
        ("flag_zero_value_suspicious", "zero-value not_defined payments (suspicious)"),
    ]:
        if flag_col in df.columns:
            results.append(
                ValidationResult(
                    check=f"{flag_col} (informational, from Task 1.1)",
                    table="payments",
                    passed=True,
                    count=int(df[flag_col].sum()),
                    details=label,
                )
            )

    return results


def _validate_reviews(df: pd.DataFrame) -> list[ValidationResult]:
    results = []

    if "review_score" in df.columns:
        out_of_range = int((~df["review_score"].between(1, 5)).sum())
        results.append(
            ValidationResult(
                check="review_score in [1,5]",
                table="reviews",
                passed=out_of_range == 0,
                count=out_of_range,
            )
        )

    # Confirms the real finding: review_id ALONE is not unique. This check is
    # expected to report count > 0 — that is the correct outcome, not a bug.
    dup_review_id_alone = int(df["review_id"].duplicated().sum())
    results.append(
        ValidationResult(
            check="review_id_alone_is_NOT_the_grain (informational)",
            table="reviews",
            passed=True,
            count=dup_review_id_alone,
            details="Expected > 0 - confirms review_id alone must never be used as a key",
        )
    )

    dup_composite = int(df.duplicated(subset=["review_id", "order_id"]).sum())
    results.append(
        ValidationResult(
            check="(review_id, order_id)_unique (grain)",
            table="reviews",
            passed=dup_composite == 0,
            count=dup_composite,
            details="Documented safe grain (Grain Registry)",
        )
    )

    return results


def _validate_geolocation(df: pd.DataFrame) -> list[ValidationResult]:
    results = []
    key_col = "zip_code_prefix" if "zip_code_prefix" in df.columns else "geolocation_zip_code_prefix"
    if key_col in df.columns:
        dup = int(df[key_col].duplicated().sum())
        results.append(
            ValidationResult(
                check=f"{key_col}_unique_after_aggregation (grain)",
                table="geolocation",
                passed=dup == 0,
                count=dup,
                details="Post-aggregation grain must be one row per zip prefix",
            )
        )
    return results


def _validate_referential_integrity(tables: dict[str, pd.DataFrame]) -> list[ValidationResult]:
    """Every child order_id must exist in the orders table."""
    results = []
    orders = tables.get("orders")
    if orders is None or "order_id" not in orders.columns:
        return results
    valid_order_ids = set(orders["order_id"])

    for child_name in ("order_items", "payments", "reviews"):
        child = tables.get(child_name)
        if child is None or "order_id" not in child.columns:
            continue
        orphans = int((~child["order_id"].isin(valid_order_ids)).sum())
        results.append(
            ValidationResult(
                check="order_id_exists_in_orders (referential integrity)",
                table=child_name,
                passed=orphans == 0,
                count=orphans,
            )
        )
    return results


_TABLE_VALIDATORS = {
    "orders": _validate_orders,
    "order_items": _validate_order_items,
    "payments": _validate_payments,
    "reviews": _validate_reviews,
    "geolocation": _validate_geolocation,
}


def validate_business_rules(tables: dict[str, pd.DataFrame]) -> list[ValidationResult]:
    """Run all business-rule checks across the cleaned tables in ``tables``.

    ``tables`` is keyed by the CLEAN_TABLES names (orders, order_items,
    payments, reviews, customers, products, sellers, geolocation) — i.e. the
    same dict shape ``load_data()`` (Task 1.3) will eventually return.
    """
    results: list[ValidationResult] = []

    for table_name, validator in _TABLE_VALIDATORS.items():
        df = tables.get(table_name)
        if df is not None:
            results.extend(validator(df))

    results.extend(_validate_referential_integrity(tables))

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_validation_report(
    schema_results: list[ValidationResult],
    business_results: list[ValidationResult],
    output_path: Path | None = None,
) -> Path:
    output_path = output_path or (REPORTS_DIR / "validation_report.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n_fail = sum(1 for r in schema_results + business_results if not r.passed)
    header = "ALL CHECKS PASSED" if n_fail == 0 else f"{n_fail} CHECK(S) FAILED"

    lines = [
        "# Validation Report",
        "",
        f"**Overall:** {header}",
        "",
        "## Schema Validation (post-ingestion, `data/interim/`)",
        "",
        "| Table | Check | Status | Count | Details |",
        "|---|---|---|---|---|",
        *[r.to_row() for r in schema_results],
        "",
        "## Business Validation (post-cleaning, `data/processed/`)",
        "",
        "| Table | Check | Status | Count | Details |",
        "|---|---|---|---|---|",
        *[r.to_row() for r in business_results],
        "",
        "> Checks marked *(informational)* report a known/expected finding from "
        "Task 0.2 / 1.1 (e.g. duplicate `review_id`, flagged rows). They always "
        "pass - the count itself is the useful signal, not pass/fail.",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# End-to-end runner
# ---------------------------------------------------------------------------


def run_full_validation() -> Path:
    """Load interim + processed tables straight from disk and write the report.

    Kept independent of ``load_data()`` (Task 1.3, not built yet) on purpose —
    Task 1.2 only needs read access to what Task 0.2 and 1.1 already produced.
    """
    schema_results: list[ValidationResult] = []
    for table_name in RAW_TABLES:
        path = INTERIM_DATA_DIR / f"{table_name}.parquet"
        if not path.is_file():
            schema_results.append(
                ValidationResult(
                    check="file_exists", table=table_name, passed=False, details=f"Missing: {path}"
                )
            )
            continue
        df = read_parquet(path)
        schema = EXPECTED_SCHEMAS.get(table_name)
        if schema:
            schema_results.extend(validate_schema(df, schema, table_name))

    processed_tables: dict[str, pd.DataFrame] = {}
    for table_name in CLEAN_TABLES:
        path = PROCESSED_DATA_DIR / f"{table_name}_clean.parquet"
        if path.is_file():
            processed_tables[table_name] = read_parquet(path)

    business_results = validate_business_rules(processed_tables)

    return generate_validation_report(schema_results, business_results)


if __name__ == "__main__":
    report_path = run_full_validation()
    print(f"Validation report written to: {report_path}")