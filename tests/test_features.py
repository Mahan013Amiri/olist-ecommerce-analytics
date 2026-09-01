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