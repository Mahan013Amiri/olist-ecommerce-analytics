"""Tests for KPI dashboard with explicit denominators. (Task 2.1)"""

import numpy as np
import pandas as pd
import pytest

from src.analysis.kpi_dashboard import compute_kpis


@pytest.fixture
def sample_df():
    """Small synthetic order-level dataset covering edge cases.

    Orders:
      o1: delivered, delayed (delay=+5), has review (score=2), has items
      o2: delivered, on-time (delay=-10), has review (score=5), has items
      o3: delivered, on-time (delay=0), no review, has items
      o4: canceled, no delay data, has items
      o5: delivered but no delivery date (delay=NaN), has items, has review
      o6: unavailable, no items (item_count=0, financials NaN), no review
    """
    return pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4", "o5", "o6"],
        "order_status": [
            "delivered", "delivered", "delivered",
            "canceled", "delivered", "unavailable",
        ],
        "order_item_count": [1, 2, 1, 1, 1, 0],
        "order_total_value": [100.0, 200.0, 50.0, 80.0, 60.0, np.nan],
        "order_freight_value": [10.0, 20.0, 5.0, 8.0, 6.0, np.nan],
        "delivery_delay_days": [5.0, -10.0, 0.0, np.nan, np.nan, np.nan],
        "is_delayed": [True, False, False, np.nan, np.nan, np.nan],
        "review_score": [2.0, 5.0, np.nan, np.nan, 4.0, np.nan],
    })


def _kpi_row(kpis: pd.DataFrame, name: str) -> pd.Series:
    row = kpis[kpis["kpi_name"] == name]
    assert len(row) == 1, f"expected exactly one row for {name}"
    return row.iloc[0]


def test_delivery_delay_rate_denominator(sample_df):
    """Denominator must be eligible orders (3: o1, o2, o3), not all 6."""
    kpis = compute_kpis(sample_df)
    row = _kpi_row(kpis, "delivery_delay_rate")

    assert row["denominator"] == 3
    assert row["numerator"] == 1  # only o1 is_delayed=True
    assert row["value"] == pytest.approx(1 / 3)


def test_on_time_delivery_rate(sample_df):
    """o2 (-10) and o3 (0) are on-time; o1 (+5) is not."""
    kpis = compute_kpis(sample_df)
    row = _kpi_row(kpis, "on_time_delivery_rate")

    assert row["denominator"] == 3
    assert row["numerator"] == 2
    assert row["value"] == pytest.approx(2 / 3)


def test_avg_delivery_delay_days(sample_df):
    kpis = compute_kpis(sample_df)
    row = _kpi_row(kpis, "avg_delivery_delay_days")

    assert row["denominator"] == 3
    assert row["value"] == pytest.approx((5.0 - 10.0 + 0.0) / 3)


def test_avg_delay_of_late_orders_denominator(sample_df):
    """Denominator must be delayed orders only (1: o1), not eligible (3)."""
    kpis = compute_kpis(sample_df)
    row = _kpi_row(kpis, "avg_delay_of_late_orders")

    assert row["denominator"] == 1
    assert row["value"] == pytest.approx(5.0)


def test_order_completion_rate_denominator(sample_df):
    """Denominator must be ALL orders (6), not eligible."""
    kpis = compute_kpis(sample_df)
    row = _kpi_row(kpis, "order_completion_rate")

    assert row["denominator"] == 6
    assert row["numerator"] == 4  # o1, o2, o3, o5 are delivered
    assert row["value"] == pytest.approx(4 / 6)


def test_order_with_item_rate(sample_df):
    """Only o6 has zero items; denominator is all 6 orders."""
    kpis = compute_kpis(sample_df)
    row = _kpi_row(kpis, "order_with_item_rate")

    assert row["denominator"] == 6
    assert row["numerator"] == 5
    assert row["value"] == pytest.approx(5 / 6)


def test_canceled_rate(sample_df):
    kpis = compute_kpis(sample_df)
    row = _kpi_row(kpis, "canceled_rate")

    assert row["denominator"] == 6
    assert row["numerator"] == 1
    assert row["value"] == pytest.approx(1 / 6)


def test_freight_to_value_ratio_excludes_no_item_orders(sample_df):
    """o6 (no items, NaN financials) must be excluded from both sums."""
    kpis = compute_kpis(sample_df)
    row = _kpi_row(kpis, "freight_to_value_ratio")

    expected_freight = 10.0 + 20.0 + 5.0 + 8.0 + 6.0  # o1-o5, not o6
    expected_value = 100.0 + 200.0 + 50.0 + 80.0 + 60.0

    assert row["numerator"] == pytest.approx(expected_freight)
    assert row["denominator"] == pytest.approx(expected_value)
    assert row["value"] == pytest.approx(expected_freight / expected_value)


def test_avg_review_score_denominator(sample_df):
    """Denominator: delivered orders with non-null review (o1, o2, o5) = 3.

    o3 is delivered but has no review -> excluded.
    o4 is canceled -> excluded regardless of review.
    o6 is unavailable, no review -> excluded.
    """
    kpis = compute_kpis(sample_df)
    row = _kpi_row(kpis, "avg_review_score")

    assert row["denominator"] == 3
    assert row["value"] == pytest.approx((2.0 + 5.0 + 4.0) / 3)


def test_no_kpi_uses_wrong_denominator_silently(sample_df):
    """Sanity check: every KPI's denominator differs meaningfully from a
    naively wrong choice (all orders vs eligible), confirming the fixture
    actually distinguishes the two cases (all=6, eligible=3).
    """
    kpis = compute_kpis(sample_df)
    denominators = set(kpis["denominator"])

    assert 6 in denominators  # KPIs based on all orders
    assert 3 in denominators  # KPIs based on eligible delivered orders
    assert 1 in denominators  # KPI based on delayed orders only