# Validation Report

**Overall:** ALL CHECKS PASSED

## Schema Validation (post-ingestion, `data/interim/`)

| Table | Check | Status | Count | Details |
|---|---|---|---|---|
| customers | required_columns_present | PASS | 0 | All expected columns present |
| customers | dtype_family_matches | PASS | 0 | All dtypes compatible |
| orders | required_columns_present | PASS | 0 | All expected columns present |
| orders | dtype_family_matches | PASS | 0 | All dtypes compatible |
| order_items | required_columns_present | PASS | 0 | All expected columns present |
| order_items | dtype_family_matches | PASS | 0 | All dtypes compatible |
| order_payments | required_columns_present | PASS | 0 | All expected columns present |
| order_payments | dtype_family_matches | PASS | 0 | All dtypes compatible |
| order_reviews | required_columns_present | PASS | 0 | All expected columns present |
| order_reviews | dtype_family_matches | PASS | 0 | All dtypes compatible |
| products | required_columns_present | PASS | 0 | All expected columns present |
| products | dtype_family_matches | PASS | 0 | All dtypes compatible |
| sellers | required_columns_present | PASS | 0 | All expected columns present |
| sellers | dtype_family_matches | PASS | 0 | All dtypes compatible |
| geolocation | required_columns_present | PASS | 0 | All expected columns present |
| geolocation | dtype_family_matches | PASS | 0 | All dtypes compatible |
| category_translation | required_columns_present | PASS | 0 | All expected columns present |
| category_translation | dtype_family_matches | PASS | 0 | All dtypes compatible |

## Business Validation (post-cleaning, `data/processed/`)

| Table | Check | Status | Count | Details |
|---|---|---|---|---|
| orders | delivery_date >= purchase_date | PASS | 0 | delivered_customer_date precedes purchase_timestamp |
| orders | order_id_unique (grain) | PASS | 0 | OK |
| orders | flag_delivered_no_date (informational, from Task 1.1) | PASS | 8 | delivered orders without a delivery date |
| orders | flag_canceled_with_date (informational, from Task 1.1) | PASS | 6 | canceled orders with a delivery date |
| order_items | price >= 0 | PASS | 0 | OK |
| order_items | freight_value >= 0 | PASS | 0 | OK |
| order_items | (order_id, order_item_id)_unique (grain) | PASS | 0 | OK |
| payments | payment_value >= 0 | PASS | 0 | OK |
| payments | (order_id, payment_sequential)_unique (grain) | PASS | 0 | OK |
| payments | flag_zero_value_expected (informational, from Task 1.1) | PASS | 6 | zero-value voucher payments (expected) |
| payments | flag_zero_value_suspicious (informational, from Task 1.1) | PASS | 3 | zero-value not_defined payments (suspicious) |
| reviews | review_score in [1,5] | PASS | 0 | OK |
| reviews | review_id_alone_is_NOT_the_grain (informational) | PASS | 814 | Expected > 0 - confirms review_id alone must never be used as a key |
| reviews | (review_id, order_id)_unique (grain) | PASS | 0 | Documented safe grain (Grain Registry) |
| geolocation | geolocation_zip_code_prefix_unique_after_aggregation (grain) | PASS | 0 | Post-aggregation grain must be one row per zip prefix |
| order_items | order_id_exists_in_orders (referential integrity) | PASS | 0 | OK |
| payments | order_id_exists_in_orders (referential integrity) | PASS | 0 | OK |
| reviews | order_id_exists_in_orders (referential integrity) | PASS | 0 | OK |

> Checks marked *(informational)* report a known/expected finding from Task 0.2 / 1.1 (e.g. duplicate `review_id`, flagged rows). They always pass - the count itself is the useful signal, not pass/fail.