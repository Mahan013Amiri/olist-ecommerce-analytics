"""Tests for RFM analysis and scoring. (Task 3.2)"""

import pandas as pd
import pytest

from src.features.rfm import calculate_rfm


@pytest.fixture
def customer_features():
    """Synthetic customer_features fixture covering RFM edge cases.

    Reference date used across tests: 2018-10-17.

    Customers:
    - cust_no_delivery : 0 delivered orders -> must be EXCLUDED entirely.
    - cust_a, cust_b    : identical frequency (2) -> must get identical F_score
                          (tie-safety under the heavy-tie regime, since most
                          of the fixture's mass sits at frequency=1-2).
    - cust_recent       : last_purchase_date very close to reference_date
                          -> highest R_score among the fixture.
    - cust_old          : last_purchase_date far from reference_date
                          -> lowest R_score among the fixture.
    - cust_frequent     : frequency far above the rest (tail case)
                          -> F_score must exceed the dominant tied group.
    - cust_high_value / cust_low_value : monetary spread, to check M_score
      direction and the "price" vs "price+freight" definition switch.
    """
    return pd.DataFrame(
        {
            "customer_unique_id": [
                "cust_no_delivery",
                "cust_a",
                "cust_b",
                "cust_recent",
                "cust_old",
                "cust_frequent",
                "cust_high_value",
                "cust_low_value",
            ],
            "total_orders": [1, 2, 2, 1, 1, 10, 1, 1],
            "total_orders_delivered": [0, 2, 2, 1, 1, 10, 1, 1],
            "first_purchase_date": pd.to_datetime(
                [
                    "2018-01-01",
                    "2018-01-01",
                    "2018-01-05",
                    "2018-10-10",
                    "2016-01-01",
                    "2016-06-01",
                    "2018-05-01",
                    "2018-05-01",
                ]
            ),
            "last_purchase_date": pd.to_datetime(
                [
                    "2018-01-01",
                    "2018-06-01",
                    "2018-06-01",
                    "2018-10-16",
                    "2016-01-01",
                    "2018-09-01",
                    "2018-05-01",
                    "2018-05-01",
                ]
            ),
            "total_spend": [None, 100.0, 100.0, 50.0, 50.0, 500.0, 1000.0, 10.0],
            "total_freight": [None, 10.0, 10.0, 5.0, 5.0, 50.0, 20.0, 2.0],
            "avg_delivery_delay_days": [None, -2.0, -2.0, 0.0, 1.0, -5.0, -1.0, 0.0],
            "is_repeat_customer": [False, True, True, False, False, True, False, False],
        }
    )


@pytest.fixture
def reference_date():
    return pd.Timestamp("2018-10-17")


def test_excludes_customers_with_no_delivered_orders(customer_features, reference_date):
    rfm = calculate_rfm(customer_features, reference_date=reference_date)
    assert "cust_no_delivery" not in rfm["customer_unique_id"].values
    assert len(rfm) == len(customer_features) - 1


def test_no_duplicate_customers(customer_features, reference_date):
    rfm = calculate_rfm(customer_features, reference_date=reference_date)
    assert rfm["customer_unique_id"].duplicated().sum() == 0


def test_recency_direction(customer_features, reference_date):
    rfm = calculate_rfm(customer_features, reference_date=reference_date)
    r_recent = rfm.loc[rfm["customer_unique_id"] == "cust_recent", "R_score"].iloc[0]
    r_old = rfm.loc[rfm["customer_unique_id"] == "cust_old", "R_score"].iloc[0]
    assert r_recent > r_old


def test_tie_safety_identical_frequency_gets_identical_score(customer_features, reference_date):
    rfm = calculate_rfm(customer_features, reference_date=reference_date)
    f_a = rfm.loc[rfm["customer_unique_id"] == "cust_a", "F_score"].iloc[0]
    f_b = rfm.loc[rfm["customer_unique_id"] == "cust_b", "F_score"].iloc[0]
    assert f_a == f_b


def test_tail_preservation_high_frequency_scores_higher(customer_features, reference_date):
    rfm = calculate_rfm(customer_features, reference_date=reference_date)
    f_frequent = rfm.loc[rfm["customer_unique_id"] == "cust_frequent", "F_score"].iloc[0]
    f_typical = rfm.loc[rfm["customer_unique_id"] == "cust_recent", "F_score"].iloc[0]
    assert f_frequent > f_typical


def test_monetary_definition_price_plus_freight(customer_features, reference_date):
    rfm = calculate_rfm(
        customer_features, reference_date=reference_date, monetary_definition="price+freight"
    )
    row = rfm.loc[rfm["customer_unique_id"] == "cust_high_value"].iloc[0]
    assert row["monetary"] == 1000.0 + 20.0


def test_monetary_definition_price_only(customer_features, reference_date):
    rfm = calculate_rfm(
        customer_features, reference_date=reference_date, monetary_definition="price"
    )
    row = rfm.loc[rfm["customer_unique_id"] == "cust_high_value"].iloc[0]
    assert row["monetary"] == 1000.0


def test_monetary_direction(customer_features, reference_date):
    rfm = calculate_rfm(customer_features, reference_date=reference_date)
    m_high = rfm.loc[rfm["customer_unique_id"] == "cust_high_value", "M_score"].iloc[0]
    m_low = rfm.loc[rfm["customer_unique_id"] == "cust_low_value", "M_score"].iloc[0]
    assert m_high > m_low


def test_invalid_monetary_definition_raises(customer_features, reference_date):
    with pytest.raises(ValueError):
        calculate_rfm(customer_features, reference_date=reference_date, monetary_definition="bogus")


def test_reference_date_override_is_respected(customer_features):
    custom_ref = pd.Timestamp("2020-01-01")
    rfm = calculate_rfm(customer_features, reference_date=custom_ref)
    row = rfm.loc[rfm["customer_unique_id"] == "cust_recent"].iloc[0]
    expected_recency = (custom_ref - pd.Timestamp("2018-10-16")).days
    assert row["recency_days"] == expected_recency


def test_reference_date_defaults_to_max_last_purchase_date(customer_features):
    rfm = calculate_rfm(customer_features, reference_date=None)
    expected_ref = customer_features["last_purchase_date"].max()
    row = rfm.loc[rfm["customer_unique_id"] == "cust_recent"].iloc[0]
    expected_recency = (expected_ref - pd.Timestamp("2018-10-16")).days
    assert row["recency_days"] == expected_recency


def test_rfm_segment_and_score_sum_consistency(customer_features, reference_date):
    rfm = calculate_rfm(customer_features, reference_date=reference_date)
    for _, row in rfm.iterrows():
        expected_segment = f"{row['R_score']}{row['F_score']}{row['M_score']}"
        assert row["rfm_segment"] == expected_segment
        expected_sum = row["R_score"] + row["F_score"] + row["M_score"]
        assert row["rfm_score_sum"] == expected_sum