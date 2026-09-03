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


## Task 1.3 — Caching Infrastructure

**چیکار شد:**
- `src/data/pipeline.py` نوشته شد: تابع `load_data(rebuild=False)` که کل زنجیره‌ی
  `ingest → interim → clean → processed` رو با یک Cache دومرحله‌ای مدیریت می‌کنه:
  1. اگه `rebuild=False` و هر ۸ فایل `data/processed/*_clean.parquet` موجود باشن → مستقیم از اونجا خونده می‌شن (نه ingest نه clean اجرا میشه).
  2. وگرنه، اگه هر ۹ فایل `data/interim/*.parquet` موجود باشن → به‌جای اجرای دوباره‌ی `ingest_all()`، از همون‌ها خونده می‌شن.
  3. در غیر این صورت (یا `rebuild=True`) → `ingest_all()` و بعدش `clean_all_tables()` از صفر اجرا می‌شن و نتیجه در `data/processed/` ذخیره میشه.
- `src/utils/io.py` اصلاح شد: `write_parquet` حالا مسیر فایل نوشته‌شده رو برمی‌گردونه (قبلاً `None` برمی‌گردوند)، هماهنگ با الگوی `save_interim` در `ingest.py`.
- `tests/test_pipeline_cache.py` نوشته شد: ۴ تست با `monkeypatch` + `tmp_path`، کاملاً مستقل از داده‌ی واقعی (یک دنیای ساختگی ۲-جدولی):
  - Cache کامل processed موجوده → نه ingest نه clean صدا زده میشن
  - فقط interim موجوده → ingest صدا زده نمیشه، clean اجرا و processed ذخیره میشه
  - `rebuild=True` → حتی با وجود هر دو Cache، ingest دوباره اجرا میشه
  - هیچ Cache‌ای نیست → ingest اجرا میشه

**نتیجه‌ی اجرای واقعی روی داده‌ی کامل:**
- `rebuild=False` با processed cache موجود → فقط یک خط لاگ، بدون اجرای دوباره‌ی پایپ‌لاین ✅
- `rebuild=True` → ingestion کامل (۹ جدول) + cleaning کامل (۸ جدول) اجرا شد؛ تمام تعداد ردیف‌ها دقیقاً مطابق Task 0.2/1.1 بودن (orders: 99,441 / order_items: 112,650 / geolocation بعد از Aggregate: 19,015 و ...)

**نتیجه‌ی تست‌ها:** هر ۴ تست جدید Pass شدن؛ کل Test Suite پروژه (۲۳ تست) بدون Regression پاس شد.

**نکته برای Task 1.4:** از این به بعد، هر Task بعدی (مثل `build_common_features`) باید داده‌ی خودش رو از طریق `load_data(rebuild=False)` بگیره، نه مستقیم از `clean.py`/`ingest.py` — تا از همین Cache یکپارچه استفاده بشه.


## Task 1.4 — Common Feature Layer + Grain Registry + Feature Registry

**چیکار شد:**
- `src/features/common_features.py` نوشته شد: تابع `build_common_features(clean_tables)`
  که یک جدول فیچر در سطح `order_id` می‌سازه، از روی `orders` و `order_items` (خروجی `load_data()`).
- فیچرهای ساخته‌شده:
  - `order_item_count`, `order_total_value`, `order_freight_value` — از `order_items` Aggregate شدن،
    Available At: `order_approved_at`. برای ۷۷۵ سفارش بدون ردیف آیتم: `order_item_count=0`،
    مقادیر مالی `NaN` (نه صفر، چون "بدون داده" با "صفر تومان" فرق داره).
  - `delivery_delay_days`, `is_delayed` — از `orders`، Available At: `post_delivery`. فقط برای
    `order_status == "delivered"` محاسبه می‌شن؛ برای بقیه‌ی وضعیت‌ها (از جمله ۶ مورد
    `flag_canceled_with_date`) و همچنین ۸ مورد `flag_delivered_no_date` (چون تاریخ ندارن)،
    به‌طور طبیعی `NaN` می‌مونن.
- بخش `if __name__ == "__main__"` به همون فایل اضافه شد که با `load_data(rebuild=False)`
  داده رو می‌گیره و نتیجه رو در `data/processed/common_features.parquet` ذخیره می‌کنه
  (هماهنگ با الگوی `ingest.py`/`pipeline.py`).
- `docs/grain_registry.md` کامل پر شد: ۸ جدول پایه (`customers` تا `geolocation`) + ردیف جدید
  `common_features` با یافته‌های واقعی Task 0.2/1.1.
- `docs/feature_registry.md` کامل پر شد: ۵ فیچر (`order_item_count`, `order_total_value`,
  `order_freight_value`, `delivery_delay_days`, `is_delayed`) با `Available At` و
  `Allowed/Forbidden Tasks` صریح — طبق Temporal Leakage Policy (بخش ۴ architecture.md).
- `tests/test_features.py` نوشته شد: ۷ تست واحد روی Fixture مصنوعی، شامل تست صریح برای هر
  حالت مرزی (سفارش عادی، دیرکرد، بدون آیتم، `canceled` با تاریخ، `delivered` بدون تاریخ).

**نتیجه‌ی اجرای واقعی روی داده‌ی کامل (۹۹,۴۴۱ سفارش):**

| بررسی | عدد | مطابق یافته‌های قبلی؟ |
|---|---|---|
| `shape` | (99441, 6) | ✅ Grain = order_id، همه‌ی سفارش‌ها حاضرن |
| `order_item_count == 0` | 775 | ✅ مطابق Task 0.2/1.1 |
| `order_total_value`/`order_freight_value` NaN | 775 | ✅ همون سفارش‌های بی‌آیتم |
| `delivery_delay_days` غیر NaN (یعنی delivered با تاریخ کامل) | 96,470 | ✅ 99,441 − 2,971 |
| `delivery_delay_days` NaN | 2,971 | ✅ شامل غیر-delivered + ۸ مورد delivered بی‌تاریخ |
| `is_delayed == True` | 6,534 | معقول (~۶.۸٪ سفارش‌های تکمیل‌شده) |

**نتیجه‌ی تست‌ها:** هر ۷ تست `test_features.py` Pass شدن.

**فایل‌های تولیدشده/تغییرکرده:** `src/features/common_features.py`,
`data/processed/common_features.parquet` (لوکال، commit نمی‌شه)، `docs/grain_registry.md`,
`docs/feature_registry.md`, `tests/test_features.py`.

**نکته برای Task 2.1 / 3.1:** از این به بعد، هر Task بعدی که نیاز به فیچرهای سطح order داره
(مثل EDA، Customer Features، Delivery Delay Prediction) باید `common_features.parquet` رو
مستقیم بخونه یا از `build_common_features(load_data())` بگیره — نه این‌که دوباره از صفر
Aggregate بسازه. همچنین قبل از استفاده از `delivery_delay_days`/`is_delayed` در هر مدل
Predictive، حتماً `docs/feature_registry.md` چک بشه (ممنوع برای `delivery_delay_prediction`
و `repeat_purchase`).


## Task 2.1 — Business EDA & KPI Dashboard

**چیکار شد:**
- پوشه‌ی جدید `src/analysis/` ساخته شد (طبق architecture.md نسخه‌ی به‌روزشده)، شامل:
  - `eda_business.py`: تابع `prepare_eda_data` که یک "spine" سطح order می‌سازه (از `common_features` + `order_status`/`order_purchase_timestamp` از `orders` + `customer_state` از `customers`)، به‌همراه توابع تحلیلی `delivery_delay_distribution`, `monthly_delay_trend`, `delay_by_state`, `order_status_breakdown`, `attach_review_scores`, `review_score_delay_correlation`، و ۴ تابع رسم نمودار (Matplotlib) که در `reports/figures/` ذخیره می‌شن. تابع `generate_eda_report` همه‌ی این‌ها رو کنار هم اجرا می‌کنه و `reports/task_2_1_eda.md` رو می‌سازه.
  - `kpi_dashboard.py`: تابع `compute_kpis` که ۹ KPI کسب‌وکاری رو هرکدوم با **Numerator/Denominator صریح** (نه فرضی) محاسبه می‌کنه، و `generate_kpi_report` که جدول خوانای Markdown می‌سازه.
- `tabulate` به `requirements.txt` اضافه شد (وابستگی `DataFrame.to_markdown()`).
- `tests/test_kpi_dashboard.py` نوشته شد: ۱۰ تست روی یک Fixture دستی ۶-سفارشی که همه‌ی حالت‌های مرزی (delayed/on-time/no-delay-data/canceled/no-items/no-review) رو پوشش می‌ده و تأیید می‌کنه هر KPI روی Denominator درست حساب می‌شه (نه یک مخرج نادرست مثل کل سفارش‌ها به‌جای سفارش‌های واجد شرط).

**نتایج کلیدی (روی داده‌ی کامل ۹۹,۴۴۱ سفارش):**

| KPI | مقدار | Denominator |
|---|---|---|
| Delivery Delay Rate | 6.77% | 96,470 (eligible delivered) |
| On-Time Delivery Rate | 93.23% | 96,470 (eligible delivered) |
| Avg Delivery Delay | -11.88 روز (زودتر از موعد) | 96,470 |
| Avg Delay of Late Orders | 10.62 روز | 6,534 (فقط delayed) |
| Order Completion Rate | 97.02% | 99,441 (کل سفارش‌ها) |
| Order-with-Item Rate | 99.22% | 99,441 |
| Canceled Rate | 0.63% | 99,441 |
| Freight-to-Value Ratio | 16.57% | فقط سفارش‌های دارای آیتم

## Task 3.1 — Customer Feature Table

**چیکار شد:**
- `src/features/customer_features.py` نوشته شد: تابع `build_customer_features(clean_tables, common_features)`
  که یک جدول فیچر در سطح `customer_unique_id` می‌سازه، از روی `orders` + `customers` (نگاشت
  `customer_id → customer_unique_id`) + `common_features` (خروجی Task 1.4).
- برخلاف `common_features` (که سطح order و بدون Cutoff زمانیه)، این جدول از **کل تاریخچه‌ی**
  هر مشتری استفاده می‌کنه — چون فقط برای RFM/Segmentation/Business Analytics (Task 3.2, 3.3)
  در نظر گرفته شده، نه Predictive Modeling آینده‌محور (طبق Leakage Policy، بخش ۴ architecture.md).
- فیچرهای ساخته‌شده: `total_orders`, `total_orders_delivered`, `first_purchase_date`,
  `last_purchase_date`, `total_spend`, `total_freight`, `avg_delivery_delay_days`, `is_repeat_customer`.
- تصمیم صریح: `total_spend`/`total_freight` فقط روی سفارش‌های `delivered` جمع می‌شن (همسو با
  پیش‌فرض `eligible_statuses=["delivered"]` که در Task 3.2 هم استفاده می‌شه). برای مشتری‌هایی
  که هیچ سفارش delivered ندارن، این دو ستون `NaN` می‌مونن (نه صفر) — دقیقاً همون کانونشن
  Task 1.4 («بدون داده» ≠ «صفر»)، با `sum(min_count=1)` پیاده‌سازی شد.
- `is_repeat_customer` بر اساس `total_orders_delivered > 1` تعریف شد (رفتار خرید تکراری واقعی،
  نه صرفاً ثبت سفارشی که ممکنه لغو شده باشه).
- `tests/test_features.py` تکمیل شد: ۵ تست جدید روی یک Fixture مصنوعی جدید (۴ سفارش،
  ۳ مشتری یکتا، شامل یک مشتری با دو `customer_id` متفاوت که باید به یک `customer_unique_id`
  Roll-up بشن) — پوشش‌دهنده‌ی حالت‌های مرزی: تجمیع مشتری تکراری، مشتری فقط-canceled
  (باید NaN بگیره نه صفر)، مشتری تک‌سفارشی، و صحت `first/last_purchase_date`.

**نتایج واقعی (روی داده‌ی کامل):**

| بررسی | عدد | یادداشت |
|---|---|---|
| `shape` | (96096, 9) | Grain = `customer_unique_id`، دقیقاً برابر با یافته‌ی Task 0.2 |
| `total_orders > 1` | 2,997 مشتری | تعداد مشتری‌های چندسفارشی (متفاوت از عدد ۳,۳۴۵ که تعداد سفارش مازاده، نه تعداد مشتری) |
| `total_orders_delivered > 1` (`is_repeat_customer == True`) | 2,801 مشتری | |
| `total_orders_delivered == 0` | 2,738 مشتری | دقیقاً برابر با تعداد `total_spend`/`total_freight` که `NaN` هستن ✅ |
| `first_purchase_date > last_purchase_date` | 0 | Sanity Check پاس شد |

**نتیجه‌ی تست‌ها:** هر ۱۲ تست `test_features.py` (۷ قدیمی + ۵ جدید) Pass شدن؛ بدون Regression.

**فایل‌های تولیدشده/تغییرکرده:** `src/features/customer_features.py`,
`data/processed/customer_features.parquet` (لوکال، commit نمی‌شه)، `tests/test_features.py`,
`docs/grain_registry.md` (ردیف جدید برای `customer_features`).

**نکته برای Task 3.2:** RFM باید مستقیماً از `customer_features.parquet` (یا
`build_customer_features(load_data(), build_common_features(...))`) بخونه، نه دوباره از صفر
Aggregate بسازه. `total_spend` همین الان طبق تعریف Monetary مرسوم (`price + freight` روی
سفارش‌های delivered) حساب شده — فقط Reference Date برای Recency باید در Task 3.2 صریحاً
مستند بشه.


## Task 3.2 — RFM Analysis & Scoring

**چیکار شد:**
- `src/features/rfm.py` نوشته شد: تابع `calculate_rfm(customer_features, reference_date=None, monetary_definition="price+freight")`
  که یک جدول RFM در سطح `customer_unique_id` می‌سازه، مستقیماً از روی خروجی Task 3.1 (`customer_features`).
- سه تصمیم صریح RFM طبق خواسته‌ی architecture.md مستند شدن:
  - **Reference Date**: پیش‌فرض `max(last_purchase_date)` روی کل مشتری‌ها (یعنی آخرین تاریخ سفارش در کل دیتاست)؛ قابل override با پارامتر.
  - **Monetary Definition**: پیش‌فرض `"price+freight"` (یعنی `total_spend + total_freight`)؛ گزینه‌ی جایگزین `"price"`.
  - **Eligible Orders**: `order_status == "delivered"` — این تصمیم در Task 3.1 قفل شده (چون `total_spend`/`total_freight`/`total_orders_delivered` از قبل فقط روی delivered حساب شدن)؛ به همین دلیل پارامتر `eligible_statuses` در امضای `calculate_rfm` وجود نداره (چون اثری نمی‌کرد و API گمراه‌کننده می‌شد).
- مشتری‌های بدون هیچ سفارش delivered (`total_orders_delivered == 0`) از جدول RFM **کاملاً حذف** شدن، نه اینکه `monetary=0` بگیرن — چون NaN به معنای «بدون داده» است، نه «صفر تومان» (همون کانوانسیون Task 1.4/3.1).

**یافته‌ی روش‌شناسی مهم (کشف‌شده حین توسعه، نه از قبل پیش‌بینی‌شده):**
یک روش Scoring واحد برای هر سه بُعد RFM کافی نبود. دو تلاش اول Fail شدن:
1. `rank(method="first") + qcut` روی ردیف‌های خام: چون ~۹۷٪ مشتری‌ها دقیقاً `frequency=1` دارن، این روش بین این مشتری‌های کاملاً یکسان امتیاز متفاوت و دلبخواهی (بر مبنای ترتیب الفبایی `customer_unique_id`) پخش می‌کرد — یه باگ واقعی، نه یه انتخاب طراحی.
2. `qcut` روی مقادیر خام با `duplicates="drop"`: باگ اول رو حل کرد ولی باعث شد `F_score` کاملاً به یک سطح سقوط کنه (چون صدک‌های ۲۰-۸۰ام همه روی مقدار غالب `1` می‌افتادن و مرزها Merge می‌شدن) — یعنی مشتری با ۱۵ سفارش هم امتیاز یکسان با مشتری یک‌بارخریدار می‌گرفت.

**راه‌حل نهایی:** یک استراتژی دو‌رژیمی خودکار در `_quantile_score`:
- اگه یک مقدار به‌تنهایی بیش از ۳۰٪ جمعیت رو پوشش بده (مثل Frequency، Heavy-tie regime)، مرزهای Quantile روی **فضای مقادیر یکتا** (نه ردیف‌ها) حساب می‌شن — این تعادل جمعیتی ۲۰-۲۰-۲۰-۲۰-۲۰ رو فدا می‌کنه ولی دم توزیع (مشتری‌های پرتکرار) رو قابل‌تفکیک نگه می‌داره.
- در غیر این صورت (مثل Recency و Monetary، Standard regime)، از `rank(method="average") + qcut` استفاده می‌شه که هم Tie-safe هست هم واقعاً جمعیت رو ۲۰-۲۰-۲۰-۲۰-۲۰ تقسیم می‌کنه.

**نتایج واقعی (روی داده‌ی کامل):**

| بررسی | عدد | یادداشت |
|---|---|---|
| `shape` (بعد از Exclusion) | (93358, 9) | 96,096 − 2,738 مشتری بدون سفارش delivered |
| Reference Date | 2018-10-17 17:30:18 | آخرین `last_purchase_date` در کل دیتاست |
| `R_score` توزیع | ~18,5xx–18,8xx در هر سطح (۵ سطح) | Population-balanced، طبق انتظار |
| `M_score` توزیع | ~18,66x–18,67x در هر سطح (۵ سطح) | Population-balanced، طبق انتظار |
| `F_score` توزیع | 1: 93,130 \| 2: 209 \| 3: 9 \| 4: 8 \| 5: 2 | Heavy-tie regime؛ دم توزیع حفظ شده |
| `customer_unique_id` تکراری | 0 | Sanity Check پاس شد |

**نتیجه‌ی تست‌ها:** `tests/test_rfm.py` نوشته شد — ۱۲ تست، شامل دو تست مستقیم برای همون دو باگ کشف‌شده (Tie-safety و Tail-preservation)، به‌علاوه‌ی تست‌های Exclusion، جهت Recency/Monetary، تعریف‌های مختلف Monetary، `reference_date` override، و صحت `rfm_segment`/`rfm_score_sum`. هر ۱۲ تست Pass شدن.

**فایل‌های تولیدشده/تغییرکرده:** `src/features/rfm.py`, `tests/test_rfm.py`,
`reports/rfm_summary.csv` (لوکال، commit نمی‌شه)، `reports/rfm_metadata.md`,
`docs/grain_registry.md` (ردیف جدید برای `rfm_summary`).

**نکته برای Task 3.3:** Segmentation باید مستقیماً از `rfm_summary.csv` (یا `calculate_rfm(...)` مستقیم)
بخونه، نه دوباره از صفر RFM بسازه. ستون `rfm_score_sum` (عددی، ۳ تا ۱۵) به‌احتمال زیاد به‌عنوان یکی از
Input Feature‌های KMeans مفیده؛ ولی چون `F_score` توزیع بسیار Skewed داره (اکثریت مطلق روی سطح ۱)، باید
حین Scaling (Task 3.3) به این نکته توجه بشه که این بُعد عملاً واریانس کمی داره و ممکنه در Clustering
اثر کمی داشته باشه — این خودش یه یافته‌ی کسب‌وکاری واقعیه (اکثر مشتری‌های Olist یک‌بارخریدارن).


## Task 3.3 — Customer Segmentation

**چیکار شد:**
- `src/models/segmentation.py` نوشته شد: پایپ‌لاین کامل Segmentation طبق الگوی
  Scaling → Candidate K → Silhouette → Profiling.
- **Feature Engineering:** `recency_days` فقط Scale شد (کم‌Skew‌تره)؛ `frequency`
  و `monetary` هر دو `log1p` شدن قبل از `StandardScaler`. `frequency` علاوه‌براین
  در صدک ۹۹ام Cap شد (جزئیات کامل در یافته‌ی زیر).
- **K Selection:** بازه‌ی `k=2` تا `k=8` با Elbow (Inertia) + Silhouette Score
  روی **کل داده** (بدون Sampling، طبق تصمیم صریح) ارزیابی شد.
- `tests/test_segmentation.py` نوشته شد: ۱۱ تست، شامل یک تست Regression مستقیم
  برای باگ Median-tie کشف‌شده (جزئیات زیر).

**یافته‌ی مهم ۱ — تشخیص و رد یک Artifact مشکوک در K=2 (نه فقط پذیرش کورکورانه‌ی بالاترین Silhouette):**
K=2 یک Silhouette غیرمنتظره بالا داشت (۰.۷۱۸) در مقابل k=3..8 (۰.۳۴–۰.۳۷). به‌جای
پذیرش این عدد به‌عنوان «بهترین K»، بررسی شد که این جهش از کجا میاد:
- بررسی اندازه‌ی Cluster‌ها نشون داد یک Cluster با دقیقاً ۲,۸۰۱ عضو (۳٪ جمعیت)
  در **هر مقدار K** (از ۲ تا ۵) بدون تغییر تکرار می‌شه.
- یک Cross-tab مستقیم بین این Cluster و شرط `frequency >= 2` نشون داد **۱۰۰٪
  تطابق دقیق** (بدون حتی یک استثنا در ۹۳,۳۵۸ ردیف) — یعنی این یک ساختار واقعی
  و پایدار در داده‌ست (تفکیک مشتری تکرارخریدار)، نه یک Artifact محاسباتی.
- برای رد قطعی فرضیه‌ی «Artifact ناشی از Outlier افراطی»، `frequency` در صدک ۹۹ام
  Cap شد (مقدار Cap = ۲.۰؛ فقط ۲۲۸ مشتری با frequency>2 تحت تأثیر قرار گرفتن) و کل
  فرآیند K-Selection تکرار شد. الگوی مشابه (همون Cluster ۲,۸۰۱‌تایی، همون تطابق
  ۱۰۰٪) دقیقاً تکرار شد — تأیید نهایی که این یک ساختار واقعی‌ست، نه Scale Artifact.
- **تصمیم نهایی: K=4** (نه K=2)، چون K=2 کل ۹۷٪ جمعیت یک‌بارخریدار رو در یک
  Cluster تفکیک‌نشده رها می‌کنه (اطلاعاتی که از قبل با `is_repeat_customer` در
  Task 3.1 داشتیم رو تکرار می‌کنه)، در حالی که K=4 همون تفکیک تکرارخریدار/یک‌بارخریدار
  رو حفظ می‌کنه و علاوه‌براین ۹۷٪ یک‌بارخریدارها رو بر اساس Recency/Monetary به
  ۳ زیرگروه معنادار تقسیم می‌کنه — با هزینه‌ی معقول در Silhouette (۰.۳۷۲ در برابر ۰.۷۱۸).

**یافته‌ی مهم ۲ — باگ Median-tie در نام‌گذاری Cluster‌ها:**
منطق اولیه‌ی `_assign_cluster_names` از یک آستانه‌ی Median (`>= median`) برای
تفکیک High/Low-Value بین ۳ Cluster یک‌بارخریدار استفاده می‌کرد. چون همیشه دقیقاً
۳ Cluster باقی می‌مونه (فرد)، Median همیشه برابر مقدار Cluster میانی بود — و شرط
`>=` باعث می‌شد این Cluster میانی به‌اشتباه «High-Value» طبقه‌بندی بشه (روی داده‌ی
واقعی: Cluster با `monetary=119.5`، که واقعاً بین ۳۱۸.۱ و ۶۹.۰ میانی بود، به اشتباه
«Dormant High-Value» نام گرفت). اصلاح شد به رتبه‌بندی مستقیم (`rank(ascending=False)`)
به‌جای مقایسه با Median: بالاترین Monetary → High-Value، میانی → Mid-Value، پایین‌ترین
→ Low-Value. یک `ValueError` صریح هم اضافه شد که اگه تعداد Cluster‌های غیرتکراری
دقیقاً ۳ نباشه (مثلاً اگه K در آینده تغییر کنه)، به‌جای تولید نام اشتباه، خطای
واضح بده. تست Regression این باگ (`test_cluster_exactly_at_median_not_misclassified`)
در `tests/test_segmentation.py` ثبت شد تا برگشت این باگ در آینده فوراً شناسایی بشه.

**نتایج نهایی (روی داده‌ی کامل، ۹۳,۳۵۸ مشتری از `rfm_summary`):**

| Cluster | اندازه | % جمعیت | mean_recency_days | mean_frequency | mean_monetary | نام نهایی |
|---|---|---|---|---|---|---|
| 3 | 2,801 | 3.00% | 268.3 | 2.11 | 308.5 | Loyal / Repeat Buyers |
| 0 | 27,872 | 29.86% | 221.6 | 1.00 | 318.1 | High-Value Active |
| 1 | 27,001 | 28.92% | 473.5 | 1.00 | 119.5 | Mid-Value Dormant |
| 2 | 35,684 | 38.22% | 195.9 | 1.00 | 69.0 | Low-Value Active |

**نتیجه‌ی تست‌ها:** هر ۱۱ تست `test_segmentation.py` Pass شدن.

**فایل‌های تولیدشده/تغییرکرده:** `src/models/segmentation.py`, `tests/test_segmentation.py`,
`reports/customer_segments.csv` (لوکال، commit نمی‌شه)، `reports/task_3_3_segmentation_summary.md`,
`reports/figures/task_3_3_k_selection_capped.png`, `docs/grain_registry.md` (ردیف جدید
برای `customer_segments`).

**نکته برای Task 4.x و 7.x:** `cluster` (عدد خام KMeans) بین اجراهای مختلف پایدار
نیست — فقط `cluster_label` باید در تحلیل‌های بعدی یا Power BI استفاده بشه. همچنین
این Segmentation صرفاً برای Analytics/Business Reporting (Task 3.3, 7.x) طراحی شده،
نه Predictive Modeling — طبق همون قاعده‌ی Leakage Policy که برای `customer_features`
(Task 3.1) هم صدق می‌کرد (کل تاریخچه‌ی مشتری بدون Cutoff زمانی استفاده شده).