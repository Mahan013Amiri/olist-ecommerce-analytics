"""Tests for feature engineering. (Task 1.4+)"""

import pandas as pd
import pytest

from src.features.common_features import build_common_features


@pytest.fixture
def clean_tables():
    orders = pd.DataFrame(
        {
            "order_id": ["o_normal", "o_late", "o_no_items", "o_canceled_with_date", "o_delivered_no_date"],
            "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered"],
            "order_delivered_customer_date": pd.to_datetime(
                ["2018-01-05", "2018-01-20", "2018-01-05", "2018-01-05", pd.NaT]
            ),
            "order_estimated_delivery_date": pd.to_datetime(
                ["2018-01-10", "2018-01-10", "2018-01-10", "2018-01-10", "2018-01-10"]
            ),
        }
    )

    order_items = pd.DataFrame(
        {
            "order_id": ["o_normal", "o_normal", "o_late", "o_canceled_with_date", "o_delivered_no_date"],
            "order_item_id": [1, 2, 1, 1, 1],
            "price": [100.0, 50.0, 200.0, 80.0, 40.0],
            "freight_value": [10.0, 5.0, 20.0, 8.0, 4.0],
        }
    )
    # NOTE: "o_no_items" deliberately has no rows in order_items.

    return {"orders": orders, "order_items": order_items}


def test_grain_one_row_per_order(clean_tables):
    result = build_common_features(clean_tables)
    assert len(result) == len(clean_tables["orders"])
    assert result["order_id"].is_unique


def test_item_aggregation_normal_order(clean_tables):
    result = build_common_features(clean_tables).set_index("order_id")
    row = result.loc["o_normal"]
    assert row["order_item_count"] == 2
    assert row["order_total_value"] == 150.0
    assert row["order_freight_value"] == 15.0


def test_order_with_no_items_gets_zero_count_and_nan_values(clean_tables):
    result = build_common_features(clean_tables).set_index("order_id")
    row = result.loc["o_no_items"]
    assert row["order_item_count"] == 0
    assert pd.isna(row["order_total_value"])
    assert pd.isna(row["order_freight_value"])


def test_delivery_delay_negative_when_early(clean_tables):
    result = build_common_features(clean_tables).set_index("order_id")
    row = result.loc["o_normal"]
    assert row["delivery_delay_days"] == -5.0
    assert row["is_delayed"] == False


def test_delivery_delay_positive_when_late(clean_tables):
    result = build_common_features(clean_tables).set_index("order_id")
    row = result.loc["o_late"]
    assert row["delivery_delay_days"] == 10.0
    assert row["is_delayed"] == True


def test_delay_is_nan_for_non_delivered_status(clean_tables):
    """Canceled orders must not get a delivery_delay_days, even if a
    delivered_customer_date happens to be present (flag_canceled_with_date)."""
    result = build_common_features(clean_tables).set_index("order_id")
    row = result.loc["o_canceled_with_date"]
    assert pd.isna(row["delivery_delay_days"])
    assert pd.isna(row["is_delayed"])


def test_delay_is_nan_when_delivered_but_no_date(clean_tables):
    """delivered orders missing delivered_customer_date (flag_delivered_no_date)
    must naturally produce NaN, not an error."""
    result = build_common_features(clean_tables).set_index("order_id")
    row = result.loc["o_delivered_no_date"]
    assert pd.isna(row["delivery_delay_days"])
    assert pd.isna(row["is_delayed"])

from src.features.customer_features import build_customer_features


@pytest.fixture
def clean_tables_customer():
    """Fixture for Task 3.1 tests: 4 orders across 3 customer_unique_ids.

    - u1: two delivered orders, placed under two different customer_id
      values (c1, c2) — mirrors the real Olist pattern where each order
      gets a fresh customer_id. Tests that the customer_id -> unique_id
      join correctly aggregates repeat purchases.
    - u2: a single canceled order (has order_items, but should NOT count
      toward total_spend since it was never delivered).
    - u3: a single delivered order, not a repeat customer.
    """
    customers = pd.DataFrame(
        {
            "customer_id": ["c1", "c2", "c3", "c4"],
            "customer_unique_id": ["u1", "u1", "u2", "u3"],
        }
    )
    orders = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3", "o4"],
            "customer_id": ["c1", "c2", "c3", "c4"],
            "order_status": ["delivered", "delivered", "canceled", "delivered"],
            "order_purchase_timestamp": pd.to_datetime(
                ["2018-01-01", "2018-02-01", "2018-01-15", "2018-03-01"]
            ),
            "order_delivered_customer_date": pd.to_datetime(
                ["2018-01-05", "2018-02-05", "2018-01-18", "2018-03-05"]
            ),
            "order_estimated_delivery_date": pd.to_datetime(
                ["2018-01-10", "2018-02-10", "2018-01-20", "2018-03-10"]
            ),
        }
    )
    order_items = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3", "o4"],
            "order_item_id": [1, 1, 1, 1],
            "price": [100.0, 200.0, 80.0, 50.0],
            "freight_value": [10.0, 20.0, 8.0, 5.0],
        }
    )
    return {"orders": orders, "order_items": order_items, "customers": customers}


def _build(clean_tables_customer):
    common = build_common_features(clean_tables_customer)
    return build_customer_features(clean_tables_customer, common)


def test_customer_grain_matches_unique_customer_ids(clean_tables_customer):
    result = _build(clean_tables_customer)
    assert len(result) == clean_tables_customer["customers"]["customer_unique_id"].nunique()
    assert result["customer_unique_id"].is_unique


def test_repeat_customer_aggregates_across_customer_id(clean_tables_customer):
    """u1 placed orders under two different customer_id values (c1, c2);
    both must roll up into a single u1 row."""
    result = _build(clean_tables_customer).set_index("customer_unique_id")
    row = result.loc["u1"]
    assert row["total_orders"] == 2
    assert row["total_orders_delivered"] == 2
    assert row["is_repeat_customer"] == True
    assert row["total_spend"] == 300.0
    assert row["total_freight"] == 30.0


def test_canceled_only_customer_has_nan_spend_not_zero(clean_tables_customer):
    """u2's only order was canceled (never delivered), even though it has
    order_items. total_spend must be NaN, not 0 — 'no data' != 'spent nothing'."""
    result = _build(clean_tables_customer).set_index("customer_unique_id")
    row = result.loc["u2"]
    assert row["total_orders"] == 1
    assert row["total_orders_delivered"] == 0
    assert pd.isna(row["total_spend"])
    assert pd.isna(row["total_freight"])
    assert row["is_repeat_customer"] == False


def test_single_delivered_order_customer_not_repeat(clean_tables_customer):
    result = _build(clean_tables_customer).set_index("customer_unique_id")
    row = result.loc["u3"]
    assert row["total_orders"] == 1
    assert row["total_orders_delivered"] == 1
    assert row["is_repeat_customer"] == False
    assert row["total_spend"] == 50.0


def test_first_and_last_purchase_dates(clean_tables_customer):
    result = _build(clean_tables_customer).set_index("customer_unique_id")
    row = result.loc["u1"]
    assert row["first_purchase_date"] == pd.Timestamp("2018-01-01")
    assert row["last_purchase_date"] == pd.Timestamp("2018-02-01")