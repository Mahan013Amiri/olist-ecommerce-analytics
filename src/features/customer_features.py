"""Customer-level feature table. Grain: customer_unique_id. (Task 3.1)

For RFM / Segmentation / Business Analytics only — NOT for future-oriented
predictive modeling (see docs/architecture.md, Temporal Semantics & Leakage
Policy, section 4, and src/features/repeat_purchase_dataset.py for the
time-cutoff dataset used in Task 4.1).

Uses each customer's FULL order history (no observation_time cutoff), since
this table feeds descriptive analytics, not a point-in-time prediction task.

Monetary figures (`total_spend`, `total_freight`) are summed over
`order_status == "delivered"` orders only, consistent with the default
`eligible_statuses=["delivered"]` used later in RFM (Task 3.2) — money only
counts once it was actually fulfilled.
"""

import pandas as pd


def build_customer_features(clean_tables: dict, common_features: pd.DataFrame) -> pd.DataFrame:
    """Build the customer-level feature table.

    Parameters
    ----------
    clean_tables : dict
        Output of load_data(), keyed by table name. Uses "orders" and
        "customers".
    common_features : pd.DataFrame
        Output of build_common_features(clean_tables) — order-level table
        with order_item_count, order_total_value, order_freight_value,
        delivery_delay_days, is_delayed.

    Returns
    -------
    pd.DataFrame
        One row per customer_unique_id, with columns:
        - total_orders: count of all orders, any status
        - total_orders_delivered: count of orders with order_status == "delivered"
        - first_purchase_date / last_purchase_date: min/max order_purchase_timestamp
        - total_spend: sum(order_total_value) over delivered orders only
        - total_freight: sum(order_freight_value) over delivered orders only
        - avg_delivery_delay_days: mean(delivery_delay_days), NaN-safe
        - is_repeat_customer: total_orders_delivered > 1
    """
    orders = clean_tables["orders"]
    customers = clean_tables["customers"]

    order_level = orders[
        ["order_id", "customer_id", "order_status", "order_purchase_timestamp"]
    ].merge(common_features, on="order_id", how="left")

    order_level = order_level.merge(
        customers[["customer_id", "customer_unique_id"]], on="customer_id", how="left"
    )

    is_delivered = order_level["order_status"] == "delivered"
    order_level["_delivered_total_value"] = order_level["order_total_value"].where(is_delivered)
    order_level["_delivered_freight_value"] = order_level["order_freight_value"].where(is_delivered)

    grouped = order_level.groupby("customer_unique_id")

    features = grouped.agg(
        total_orders=("order_id", "count"),
        total_orders_delivered=("order_status", lambda s: (s == "delivered").sum()),
        first_purchase_date=("order_purchase_timestamp", "min"),
        last_purchase_date=("order_purchase_timestamp", "max"),
        total_spend=("_delivered_total_value", lambda s: s.sum(min_count=1)),
        total_freight=("_delivered_freight_value", lambda s: s.sum(min_count=1)),
        avg_delivery_delay_days=("delivery_delay_days", "mean"),
    ).reset_index()

    features["is_repeat_customer"] = features["total_orders_delivered"] > 1

    return features


if __name__ == "__main__":
    from src.data.pipeline import load_data
    from src.features.common_features import build_common_features
    from src.utils.config import PROCESSED_DATA_DIR
    from src.utils.io import write_parquet

    clean_tables = load_data(rebuild=False)
    common_features = build_common_features(clean_tables)
    customer_features = build_customer_features(clean_tables, common_features)
    out_path = write_parquet(customer_features, PROCESSED_DATA_DIR / "customer_features.parquet")
    print(f"OK: {len(customer_features):,} rows -> {out_path}")