# Grain Registry

> هر Dataset جدیدی که ساخته می‌شود باید یک ردیف به این جدول اضافه کند.
> Convention: هرجا «مشتری» یعنی `customer_unique_id`، نه `customer_id`.

| Table / Dataset | Grain | Key | Notes |
|---|---|---|---|
| `customers` | `customer_id` | `customer_id` | 99,441 rows; `customer_unique_id` has only 96,096 unique → 3,345 real customers with repeat purchases |
| `orders` | `order_id` | `order_id` | 99,441 rows; 2 delivered without delivery date; 6 canceled with delivery date |
| `order_items` | `(order_id, order_item_id)` | composite | 775 orders have no item rows |
| `order_payments` | `(order_id, payment_sequential)` | composite | 2,961 orders with multiple payment methods |
| `order_reviews` | `(review_id, order_id)` | composite | **`review_id` alone is NOT unique** — 814 duplicates found |
| `products` | `product_id` | `product_id` | 610 products with incomplete metadata |
| `sellers` | `seller_id` | `seller_id` | >60% sellers in SP state |
| `geolocation` | `zip_code_prefix` (after aggregation) | `zip_code_prefix` | Raw: 26% exact duplicates; must aggregate before use |
| `category_translation` | `product_category_name` | `product_category_name` | Simple lookup table |

<!-- New datasets will be added below as they are created in later tasks -->
