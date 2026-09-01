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


## Task 1.2 — Data Validation Layer

**چیکار شد:**
- `src/data/validate.py` نوشته شد: دو مرحله طبق معماری —
  - **Schema Validation** (`validate_schema`): روی ۹ جدول `data/interim/`، چک می‌کنه ستون‌های موردانتظار موجودن و خانواده‌ی dtype‌شون (int/float/datetime/object) درسته.
  - **Business Validation** (`validate_business_rules`): روی ۸ جدول `data/processed/`، قوانین `delivery_date >= purchase_date`، `price/freight/payment_value >= 0`، `review_score ∈ [1,5]`، یکتایی `(order_id, order_item_id)` و `(review_id, order_id)`، یکتایی `zip_code_prefix` بعد از Aggregation، و Referential Integrity (`order_id` در `order_items`/`payments`/`reviews` باید در `orders` وجود داشته باشه).
- به‌جای تشخیص دوباره‌ی مشکلات شناخته‌شده، ستون‌های `flag_*` ساخته‌شده در Task 1.1 رو مستقیم می‌خونه و به‌صورت **informational** (همیشه Pass، با شمارش دقیق) گزارش می‌کنه.
- `src/utils/io.py` تکمیل شد: `read_parquet`, `write_parquet`, `file_exists` (فقط توابع پایه‌ی I/O — منطق Cache/Hash همچنان برای Task 1.3 باقی می‌مونه).
- `tests/test_validate.py` نوشته شد: ۱۴ تست واحد روی Fixtureهای مصنوعی، شامل تست صریح روی نکته‌ی کلیدی پروژه (`review_id` تنها باید Duplicate پیدا کنه، ولی `(review_id, order_id)` نباید).
- Output: `reports/validation_report.md`

**نتیجه‌ی اجرای واقعی روی داده‌ی کامل (۹۹,۴۴۱ سفارش):** `ALL CHECKS PASSED` — همه‌ی اعداد Informational دقیقاً با یافته‌های Task 0.2/1.1 مطابقت داشتن:

| یافته | عدد گزارش‌شده | مطابق مستندات؟ |
|---|---|---|
| `flag_delivered_no_date` | ۸ | ✅ |
| `flag_canceled_with_date` | ۶ | ✅ |
| `flag_zero_value_expected` (voucher) | ۶ | ✅ |
| `flag_zero_value_suspicious` | ۳ | ✅ |
| `review_id` تکراری (تنها، بدون `order_id`) | ۸۱۴ | ✅ دقیقاً مطابق architecture.md |
| Referential Integrity (۳ جدول) | ۰ Orphan | ✅ کیفیت داده تأیید شد |

هیچ Business Rule واقعی (نه Informational) Fail نشد — یعنی Cleaning انجام‌شده در Task 1.1 از نظر منطق کسب‌وکار سالمه.

**نکته برای Task 1.3:** `src/utils/io.py` الان `read_parquet`/`write_parquet`/`file_exists` رو داره؛ منطق `load_data(rebuild=False)` باید روی همین توابع ساخته بشه، نه از صفر.