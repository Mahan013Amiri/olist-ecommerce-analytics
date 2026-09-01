"""Common features shared across multiple tasks. (Task 1.4)

Grain: order_id (one row per order).
All monetary/count features are aggregated from order_items and are
available at order_approved_at. delivery_delay_days / is_delayed are only
available post_delivery and only defined for order_status == "delivered"
(see docs/feature_registry.md for Allowed/Forbidden Tasks).
"""

import pandas as pd


def build_common_features(clean_tables: dict) -> pd.DataFrame:
    """Build the order-level common feature table.

    Parameters
    ----------
    clean_tables : dict
        Output of load_data(), keyed by table name
        (orders, order_items, payments, reviews, customers, products,
        sellers, geolocation).

    Returns
    -------
    pd.DataFrame
        One row per order_id, with columns:
        - order_item_count (available_at: order_approved_at)
        - order_total_value (available_at: order_approved_at)
        - order_freight_value (available_at: order_approved_at)
        - delivery_delay_days (available_at: post_delivery)
        - is_delayed (available_at: post_delivery)
    """
    orders = clean_tables["orders"]
    order_items = clean_tables["order_items"]

    # --- item-level aggregation (order_approved_at) ---
    item_agg = order_items.groupby("order_id", as_index=False).agg(
        order_item_count=("order_item_id", "count"),
        order_total_value=("price", "sum"),
        order_freight_value=("freight_value", "sum"),
    )

    features = orders[["order_id", "order_status", "order_delivered_customer_date",
                        "order_estimated_delivery_date"]].merge(
        item_agg, on="order_id", how="left"
    )

    # 775 orders with no item rows: count -> 0, monetary values stay NaN
    features["order_item_count"] = features["order_item_count"].fillna(0).astype(int)

    # --- delivery delay (post_delivery, delivered orders only) ---
    is_delivered = features["order_status"] == "delivered"

    delay_days = (
        features["order_delivered_customer_date"] - features["order_estimated_delivery_date"]
    ).dt.days

    features["delivery_delay_days"] = delay_days.where(is_delivered)
    features["is_delayed"] = (features["delivery_delay_days"] > 0).where(
        features["delivery_delay_days"].notna()
    )

    return features.drop(
        columns=["order_status", "order_delivered_customer_date", "order_estimated_delivery_date"]
    ).reset_index(drop=True)

if __name__ == "__main__":
    from src.data.pipeline import load_data
    from src.utils.config import PROCESSED_DATA_DIR
    from src.utils.io import write_parquet

    clean_tables = load_data(rebuild=False)
    common_features = build_common_features(clean_tables)

    out_path = write_parquet(common_features, PROCESSED_DATA_DIR / "common_features.parquet")
    print(f"OK: {len(common_features):,} rows -> {out_path}")