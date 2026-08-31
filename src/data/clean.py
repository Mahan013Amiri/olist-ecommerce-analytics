"""Per-table cleaning functions. (Task 1.1)"""
import pandas as pd


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    date_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in date_cols:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")

    out["flag_delivered_no_date"] = (out["order_status"] == "delivered") & (
        out["order_delivered_customer_date"].isna()
    )
    out["flag_canceled_with_date"] = (out["order_status"] == "canceled") & (
        out["order_delivered_customer_date"].notna()
    )

    out = out.drop_duplicates(subset=out.columns.tolist())
    out = out.drop_duplicates(subset="order_id", keep="first")

    return out.reset_index(drop=True)

def clean_order_items(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["price"] = pd.to_numeric(out["price"], errors="coerce")
    out["freight_value"] = pd.to_numeric(out["freight_value"], errors="coerce")

    out = out.drop_duplicates(subset=out.columns.tolist())
    out = out.drop_duplicates(subset=["order_id", "order_item_id"], keep="first")

    return out.reset_index(drop=True)


def clean_payments(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["payment_value"] = pd.to_numeric(out["payment_value"], errors="coerce")

    is_zero = out["payment_value"] == 0
    is_voucher = out["payment_type"] == "voucher"

    out["flag_zero_value_expected"] = is_zero & is_voucher
    out["flag_zero_value_suspicious"] = is_zero & ~is_voucher

    out = out.drop_duplicates(subset=out.columns.tolist())
    out = out.drop_duplicates(subset=["order_id", "payment_sequential"], keep="first")

    return out.reset_index(drop=True)

def clean_order_reviews(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    date_cols = ["review_creation_date", "review_answer_timestamp"]
    for col in date_cols:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")

    out = out.drop_duplicates(subset=out.columns.tolist())
    out = out.drop_duplicates(subset=["review_id", "order_id"], keep="first")

    dup_review_ids = out["review_id"][out["review_id"].duplicated(keep=False)]
    out["flag_duplicate_review_id"] = out["review_id"].isin(set(dup_review_ids))

    return out.reset_index(drop=True)

def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.drop_duplicates(subset=out.columns.tolist())
    out = out.drop_duplicates(subset="customer_id", keep="first")
    return out.reset_index(drop=True)

def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.drop_duplicates(subset=out.columns.tolist())
    out = out.drop_duplicates(subset="product_id", keep="first")

    metadata_cols = [
        "product_category_name",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
    ]
    dimension_cols = [
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]

    out["flag_missing_metadata"] = out[metadata_cols].isna().all(axis=1)
    out["flag_missing_dimensions"] = out[dimension_cols].isna().any(axis=1)

    return out.reset_index(drop=True)

def clean_sellers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.drop_duplicates(subset=out.columns.tolist())
    out = out.drop_duplicates(subset="seller_id", keep="first")
    return out.reset_index(drop=True)

def handle_duplicates_geolocation(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.drop_duplicates(subset=out.columns.tolist())

    agg_dict = {
        "geolocation_lat": "mean",
        "geolocation_lng": "mean",
    }

    def _mode_or_first(s):
        m = s.mode()
        return m.iloc[0] if not m.empty else s.iloc[0]

    agg_dict["geolocation_city"] = _mode_or_first
    agg_dict["geolocation_state"] = _mode_or_first

    result = out.groupby("geolocation_zip_code_prefix", as_index=False).agg(agg_dict)
    return result.reset_index(drop=True)

def clean_all_tables(interim: dict) -> dict:
    return {
        "orders": clean_orders(interim["orders"]),
        "order_items": clean_order_items(interim["order_items"]),
        "payments": clean_payments(interim["order_payments"]),
        "reviews": clean_order_reviews(interim["order_reviews"]),
        "customers": clean_customers(interim["customers"]),
        "products": clean_products(interim["products"]),
        "sellers": clean_sellers(interim["sellers"]),
        "geolocation": handle_duplicates_geolocation(interim["geolocation"]),
    }