# Grain Registry

> هر Dataset جدیدی که ساخته می‌شود باید یک ردیف به این جدول اضافه کند.
> Convention: هرجا «مشتری» یعنی `customer_unique_id`، نه `customer_id`.

| Table / Dataset | Grain | Key | Notes |
|---|---|---|---|
| `customers` | `customer_id` | `customer_id` | 99,441 rows; `customer_unique_id` has only 96,096 unique → 3,345 real customers with repeat purchases |
| `orders` | `order_id` | `order_id` | 99,441 rows; `flag_delivered_no_date` (8 rows), `flag_canceled_with_date` (6 rows) |
| `order_items` | `(order_id, order_item_id)` | composite | 112,650 rows; 775 orders have no item rows at all |
| `payments` | `(order_id, payment_sequential)` | composite | 103,886 rows; `flag_zero_value_expected` (6, voucher), `flag_zero_value_suspicious` (3, not_defined) |
| `reviews` | `(review_id, order_id)` | composite | 99,224 rows; **`review_id` alone is NOT unique** — `flag_duplicate_review_id` (1,603 rows) |
| `products` | `product_id` | `product_id` | 32,951 rows; `flag_missing_metadata` (610), `flag_missing_dimensions` (2) |
| `sellers` | `seller_id` | `seller_id` | 3,095 rows; >60% sellers in SP state |
| `geolocation` | `zip_code_prefix` (after aggregation) | `geolocation_zip_code_prefix` | Raw had 26% exact duplicates; aggregated to 19,015 rows (mean lat/lng, mode city/state) |
| `common_features` | `order_id` | `order_id` | 99,441 rows; order-level features built from `order_items` + `orders` (Task 1.4). `order_item_count=0` and monetary values are `NaN` for the 775 orders with no item rows; `delivery_delay_days`/`is_delayed` are `NaN` unless `order_status == "delivered"` |
| `customer_features` | `customer_unique_id` | `customer_unique_id` | 96,096 rows; built from `orders` + `customers` + `common_features` (Task 3.1). Rolls up FULL order history per customer (no time cutoff) — for RFM/Segmentation/Analytics only, NOT predictive modeling. `total_spend`/`total_freight` are `NaN` (not 0) for the 2,738 customers with zero delivered orders; `is_repeat_customer` is based on `total_orders_delivered > 1` |
| `rfm_summary` | `customer_unique_id` | `customer_unique_id` | Built from `customer_features` (Task 3.1); excludes 2,738 customers with 0 delivered orders → 93,358 rows. Reference Date = max(last_purchase_date) = 2018-10-17. Monetary = price+freight. |
<!-- New datasets will be added below as they are created in later tasks -->