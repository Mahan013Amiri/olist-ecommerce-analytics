"""Tests for schema and business validation. (Task 1.2)"""

import pandas as pd
import pytest

from src.data.validate import (
    ValidationResult,
    generate_validation_report,
    validate_business_rules,
    validate_schema,
)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_validate_schema_all_present_and_compatible():
    df = pd.DataFrame(
        {
            "order_id": ["a", "b"],
            "order_status": ["delivered", "shipped"],
        }
    )
    schema = {"order_id": "object", "order_status": "object"}
    results = validate_schema(df, schema, "orders")
    assert all(r.passed for r in results)


def test_validate_schema_detects_missing_column():
    df = pd.DataFrame({"order_id": ["a", "b"]})
    schema = {"order_id": "object", "order_status": "object"}
    results = validate_schema(df, schema, "orders")
    col_check = next(r for r in results if r.check == "required_columns_present")
    assert col_check.passed is False
    assert col_check.count == 1


def test_validate_schema_detects_dtype_mismatch():
    df = pd.DataFrame({"price": ["1.0", "2.0"]})  # object, not float
    schema = {"price": "float"}
    results = validate_schema(df, schema, "order_items")
    dtype_check = next(r for r in results if r.check == "dtype_family_matches")
    assert dtype_check.passed is False


def test_validate_schema_tolerant_of_int_width():
    df = pd.DataFrame({"order_item_id": pd.array([1, 2], dtype="int32")})
    schema = {"order_item_id": "int"}
    results = validate_schema(df, schema, "order_items")
    dtype_check = next(r for r in results if r.check == "dtype_family_matches")
    assert dtype_check.passed is True


# ---------------------------------------------------------------------------
# Business validation — orders
# ---------------------------------------------------------------------------


def test_orders_flags_inverted_delivery_date():
    orders = pd.DataFrame(
        {
            "order_id": ["o1", "o2"],
            "order_purchase_timestamp": pd.to_datetime(["2018-01-10", "2018-01-10"]),
            "order_delivered_customer_date": pd.to_datetime(["2018-01-05", "2018-01-15"]),
        }
    )
    results = validate_business_rules({"orders": orders})
    check = next(r for r in results if r.check == "delivery_date >= purchase_date")
    assert check.passed is False
    assert check.count == 1


def test_orders_grain_uniqueness():
    orders = pd.DataFrame(
        {
            "order_id": ["o1", "o1"],
            "order_purchase_timestamp": pd.to_datetime(["2018-01-01", "2018-01-01"]),
            "order_delivered_customer_date": pd.to_datetime(["2018-01-05", "2018-01-05"]),
        }
    )
    results = validate_business_rules({"orders": orders})
    check = next(r for r in results if r.check == "order_id_unique (grain)")
    assert check.passed is False
    assert check.count == 1


def test_orders_informational_flags_pass_but_report_count():
    orders = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3"],
            "order_purchase_timestamp": pd.to_datetime(["2018-01-01"] * 3),
            "order_delivered_customer_date": pd.to_datetime([None, "2018-01-05", "2018-01-05"]),
            "flag_delivered_no_date": [True, False, False],
            "flag_canceled_with_date": [False, False, True],
        }
    )
    results = validate_business_rules({"orders": orders})
    flag1 = next(r for r in results if r.check.startswith("flag_delivered_no_date"))
    flag2 = next(r for r in results if r.check.startswith("flag_canceled_with_date"))
    assert flag1.passed is True and flag1.count == 1
    assert flag2.passed is True and flag2.count == 1


# ---------------------------------------------------------------------------
# Business validation — order_items / payments
# ---------------------------------------------------------------------------


def test_order_items_negative_price_fails():
    order_items = pd.DataFrame(
        {
            "order_id": ["o1", "o1"],
            "order_item_id": [1, 2],
            "price": [50.0, -10.0],
            "freight_value": [5.0, 5.0],
        }
    )
    results = validate_business_rules({"order_items": order_items})
    check = next(r for r in results if r.check == "price >= 0")
    assert check.passed is False
    assert check.count == 1


def test_order_items_grain_uniqueness():
    order_items = pd.DataFrame(
        {
            "order_id": ["o1", "o1"],
            "order_item_id": [1, 1],
            "price": [50.0, 50.0],
            "freight_value": [5.0, 5.0],
        }
    )
    results = validate_business_rules({"order_items": order_items})
    check = next(r for r in results if "order_item_id)_unique" in r.check)
    assert check.passed is False


def test_payments_zero_value_flags_are_informational():
    payments = pd.DataFrame(
        {
            "order_id": ["o1", "o2"],
            "payment_sequential": [1, 1],
            "payment_value": [0.0, 100.0],
            "flag_zero_value_expected": [True, False],
            "flag_zero_value_suspicious": [False, False],
        }
    )
    results = validate_business_rules({"payments": payments})
    check = next(r for r in results if r.check == "payment_value >= 0")
    assert check.passed is True  # 0.0 is not negative
    flag = next(r for r in results if r.check.startswith("flag_zero_value_expected"))
    assert flag.passed is True and flag.count == 1


# ---------------------------------------------------------------------------
# Business validation — reviews (the key documented finding)
# ---------------------------------------------------------------------------


def test_reviews_review_id_alone_is_not_unique_by_design():
    reviews = pd.DataFrame(
        {
            "review_id": ["r1", "r1", "r2"],
            "order_id": ["o1", "o2", "o3"],
            "review_score": [5, 4, 3],
        }
    )
    results = validate_business_rules({"reviews": reviews})
    dup_alone = next(r for r in results if "NOT_the_grain" in r.check)
    dup_composite = next(r for r in results if "(review_id, order_id)_unique" in r.check)

    # This is the whole point of the check: alone, review_id has duplicates...
    assert dup_alone.passed is True  # informational — never fails
    assert dup_alone.count == 1
    # ...but the composite key (review_id, order_id) is a valid grain.
    assert dup_composite.passed is True
    assert dup_composite.count == 0


def test_reviews_score_out_of_range():
    reviews = pd.DataFrame(
        {
            "review_id": ["r1", "r2"],
            "order_id": ["o1", "o2"],
            "review_score": [5, 7],
        }
    )
    results = validate_business_rules({"reviews": reviews})
    check = next(r for r in results if r.check == "review_score in [1,5]")
    assert check.passed is False
    assert check.count == 1


# ---------------------------------------------------------------------------
# Referential integrity
# ---------------------------------------------------------------------------


def test_referential_integrity_detects_orphan_order_id():
    orders = pd.DataFrame({"order_id": ["o1", "o2"]})
    order_items = pd.DataFrame({"order_id": ["o1", "o999"], "order_item_id": [1, 1], "price": [1.0, 1.0], "freight_value": [0.0, 0.0]})
    results = validate_business_rules({"orders": orders, "order_items": order_items})
    check = next(
        r
        for r in results
        if r.check == "order_id_exists_in_orders (referential integrity)" and r.table == "order_items"
    )
    assert check.passed is False
    assert check.count == 1


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def test_generate_validation_report_writes_markdown(tmp_path):
    schema_results = [ValidationResult(check="c1", table="orders", passed=True, count=0)]
    business_results = [ValidationResult(check="c2", table="reviews", passed=False, count=3)]

    out_path = tmp_path / "reports" / "validation_report.md"
    result_path = generate_validation_report(schema_results, business_results, out_path)

    assert result_path == out_path
    content = out_path.read_text(encoding="utf-8")
    assert "1 CHECK(S) FAILED" in content
    assert "c1" in content and "c2" in content