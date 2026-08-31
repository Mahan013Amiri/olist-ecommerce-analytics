# Progress Log

> گزارش تفصیلی هر Task تکمیل‌شده — چیکار شد، چه فایل‌هایی ساخته/تغییر کردند، چه یافته‌هایی به‌دست اومد.
> برای وضعیت خلاصه، به جدول Task Progress در `README.md` نگاه کن.

## Task 0.1 — Project Setup & Environment

**چیکار شد:**
- ساختار کامل Repo چیده شد (`data/`, `src/`, `tests/`, `docs/`, `notebooks/`, `models/`, `reports/`, `dashboard/`)
- `requirements.txt`, `.gitignore`, `README.md` نوشته شدند
- `src/utils/config.py` با مسیرهای مرکزی پروژه پیاده‌سازی شد
- تمام فایل‌های `src/` به‌صورت Stub (فقط Docstring) ساخته شدند، آماده برای Taskهای بعدی
- `tests/test_setup.py` نوشته شد — چک می‌کند ساختار پوشه‌ها و Config سالم است

**نتیجه:** اسکلت پروژه قابل clone و اجرا آماده شد.

---

## Task 0.2 — Data Ingestion & Profiling

**چیکار شد:**
- `src/data/ingest.py` نوشته شد: هر ۹ فایل CSV خام از `data/raw/` خوانده می‌شود، نوع ستون‌ها Cast می‌شود (تاریخ‌ها، اعداد، شناسه‌ها)، و هر کدام به‌صورت Parquet در `data/interim/` ذخیره می‌شود — بدون هیچ Cleaning منطقی
- `src/data/profile.py` نوشته شد: هر جدول را بررسی می‌کند (تعداد ردیف، Schema، درصد Missing، تعداد Duplicate روی Grain مستند) و نتیجه را در `reports/data_profile.md` ذخیره می‌کند
- یک بخش «Known Findings Verification» به گزارش اضافه شد که یافته‌های کلیدی را مستقیماً از داده بازتولید می‌کند (نه بر پایه‌ی فرض)

**نتایج کلیدی (از `reports/data_profile.md`):**
- ۹۹,۴۴۱ مشتری (`customer_id`) در برابر ۹۶,۰۹۶ مشتری یکتا (`customer_unique_id`) → **۳,۳۴۵ مشتری با خرید تکراری**
- **۷۷۵ سفارش** بدون هیچ ردیف آیتمی (عمدتاً وضعیت `unavailable` و `canceled`)
- **۹ پرداخت** با مبلغ صفر (۶ مورد `voucher`، ۳ مورد `not_defined`)
- **۸ سفارش** با وضعیت `delivered` که تاریخ تحویل ندارند
- **۶ سفارش** با وضعیت `canceled` که تاریخ تحویل دارند
- **۸۱۴ مورد** `review_id` تکراری وقتی به‌تنهایی (بدون `order_id`) چک شود — تأیید می‌کند Grain امن این جدول باید `(review_id, order_id)` باشد
- **۲۶۱,۸۳۱ ردیف (۲۶.۲٪)** کاملاً تکراری در جدول خام `geolocation`

**فایل‌های تولیدشده:** `data/interim/*.parquet` (۹ فایل، لوکال، commit نمی‌شود) + `reports/data_profile.md` (commit شده)

**نکته برای Task 1.1:** این یافته‌ها (به‌خصوص ۸ سفارش `delivered` بی‌تاریخ) باید در Task 1.1 مبنای تصمیم‌گیری صریح قرار بگیرند.

## Task 1.1 — Per-Table Cleaning

**چیکار شد:**
- `src/data/clean.py` نوشته شد: یک تابع Clean مستقل برای هر ۸ جدول
  (`clean_orders`, `clean_order_items`, `clean_payments`,
  `clean_order_reviews`, `clean_customers`, `clean_products`,
  `clean_sellers`, `handle_duplicates_geolocation`) + `clean_all_tables`
  که همه رو اجرا و در `data/processed/` ذخیره می‌کنه.
- سیاست: هیچ ردیفی به‌خاطر مشکوک‌بودن حذف نشد؛ فقط Duplicate کامل حذف شد.
  هر مورد مشکوک با ستون `flag_*` مستند شد.

**نتایج واقعی (روی داده‌ی کامل ۹۹,۴۴۱ سفارشی):**

| جدول | ورودی | خروجی | Flag |
|---|---|---|---|
| orders | 99,441 | 99,441 | flag_delivered_no_date=8, flag_canceled_with_date=6 |
| order_items | 112,650 | 112,650 | — |
| payments | 103,886 | 103,886 | flag_zero_value_expected=6, flag_zero_value_suspicious=3 |
| reviews | 99,224 | 99,224 | flag_duplicate_review_id=1603 |
| customers | 99,441 | 99,441 | — |
| products | 32,951 | 32,951 | flag_missing_metadata=610, flag_missing_dimensions=2 |
| sellers | 3,095 | 3,095 | — |
| geolocation | 1,000,163 | 19,015 | Aggregate شد روی zip_code_prefix |

**فایل‌های تولیدشده:** `src/data/clean.py`,
`data/processed/{orders,order_items,payments,reviews,customers,products,sellers,geolocation}_clean.parquet`
(لوکال، commit نمی‌شن طبق `.gitignore`).

**نکته برای Task 1.2:** ستون‌های `flag_*` باید در Validation استفاده بشن،
نه اینکه دوباره از صفر تشخیص داده بشن.