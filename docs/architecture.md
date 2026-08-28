# معماری پروژه End-to-End: Olist Brazilian E-Commerce
### نسخه ۳.۱ — Final, Right-Sized Architecture

> این سند، سند مرجع نهایی پروژه است. از این به بعد هر Task باید با همین معماری منطبق باشد.
> این نسخه ترکیبی است از: (الف) فلسفه‌ی صحیح نسخه ۲.۱ (Grain-safe، Temporal-safe، بدون Overengineering)، (ب) چند اصلاح واقعاً باارزش از پیشنهاد نسخه ۳.۰ (که در بخش ۱۲ مشخص شده‌اند)، و (ج) یافته‌های واقعی به‌دست‌آمده از یک اکتشاف دستی اولیه روی داده‌ی واقعی (نه فرض روی مستندات عمومی Kaggle) که در بخش ۱ ثبت شده و باید در Task 0.2 به‌شکل حرفه‌ای بازتولید شود. هر بخشی از v3.0 که صرفاً زیرساخت اضافه بود بدون توجیه کافی برای مقیاس این پروژه، **آگاهانه** کنار گذاشته شد — دلیلش در بخش ۱۲ ثبت شده.
>
> **وضعیت پروژه:** هیچ Task ای هنوز اجرا نشده؛ این سند از Task 0.1 به بعد، مبنای اجرای تمیز و حرفه‌ای پروژه است.

---

## ۰. سه قانون سراسری معماری (بدون هزینه، بدون Infrastructure)

قبل از هر تصمیم فنی، این سه سوال باید جواب داشته باشند — این‌ها را از v3.0 گرفتیم چون رایگان و ارزشمندند، بدون نیاز به هیچ کد یا ابزار اضافه:

1. **Grain First** — قبل از هر Join: «واحد هر ردیف این جدول چیست؟»
2. **Time First** — قبل از استفاده از هر Feature در یک مدل: «آیا این Feature در لحظه‌ی پیش‌بینی واقعاً در دسترس بود؟»
3. **Business First** — قبل از هر Metric: «این عدد از چه تصمیم Businessای پشتیبانی می‌کند؟» اگر جواب ندارد، احتمالاً غیرضروری است.

---

## ۱. شناخت دیتاست (بر اساس اکتشاف اولیه، باید در Task 0.2 رسمی و بازتولید شود)

دیتاست از ۹ جدول تشکیل شده. جدول زیر بر پایه‌ی یک اکتشاف اولیه‌ی دستی روی داده‌ی واقعی این پروژه است (نه فرض روی مستندات عمومی Kaggle) و باید در Task 0.2 (که هنوز به‌شکل حرفه‌ای نوشته نشده) به‌طور رسمی، با کد Reusable و Docstring، بازتولید و در `reports/data_profile.md` ثبت شود. این یافته‌ها همین الان مسیر تصمیم‌های معماری زیر را مشخص می‌کنند تا Task 0.2 از اول بداند دنبال چه مواردی باید بگردد:

| جدول | Grain واقعی (تأییدشده) | نکته‌ی حیاتی |
|---|---|---|
| `customers` | `customer_id` (۹۹٬۴۴۱ ردیف، بدون Missing/Duplicate) | `customer_id` یکتا=۹۹٬۴۴۱ ولی `customer_unique_id` یکتا=۹۶٬۰۹۶ → **۳٬۳۴۵ مشتری واقعی خرید تکراری دارند** |
| `orders` | `order_id` (۹۹٬۴۴۱ ردیف) | ۲ سفارش `delivered` بدون تاریخ تحویل (ناسازگاری واقعی)؛ ۶ سفارش `canceled` که تاریخ تحویل دارند |
| `order_items` | `(order_id, order_item_id)` | ۹٬۸۰۳ سفارش بیش از ۱ آیتم دارند (تا ۲۱ آیتم)؛ **۷۷۵ سفارش اصلاً ردیف آیتم ندارند** (عمدتاً `unavailable`/`canceled`، ولی ۱ مورد `shipped` و ۲ مورد `invoiced` مشکوک‌اند) |
| `order_payments` | `(order_id, payment_sequential)` | ۲٬۹۶۱ سفارش با چند روش پرداخت؛ ۹ پرداخت با مبلغ صفر (۶ تای `voucher` طبیعی، ۳ تای `not_defined` مشکوک) |
| `order_reviews` | ⚠️ **`review_id` یکتا نیست** — این یک یافته‌ی واقعی از v2.1 است که هیچ نسخه‌ای از معماری قبل از آن پیش‌بینی نکرده بود؛ ۸۱۴ مورد `review_id` تکراری با محتوای متفاوت (حتی `order_id` متفاوت) پیدا شد. **Grain واقعی و امن: `(review_id, order_id)` با هم، نه `review_id` تنها** | هر Task که این جدول را می‌خواند باید این نکته را رعایت کند |
| `products` | `product_id` (بدون Duplicate) | ۶۱۰ محصول به‌طور هم‌زمان ۴ ستون متادیتا ندارند (ثبت ناقص)؛ ۱ محصول مستقل فقط وزن/ابعاد ندارد |
| `sellers` | `seller_id` (بدون Duplicate) | >۶۰٪ فروشنده‌ها در ایالت SP — تمرکز جغرافیایی بالا |
| `geolocation` | بعد از Aggregation: `zip_code_prefix` | خام: ۱٬۰۰۰٬۱۶۳ ردیف با **۲۶۱٬۸۳۱ ردیف کاملاً تکراری (۲۶٪)**؛ میانگین ۵۳ ردیف lat/lng به ازای هر zip — Aggregation قبل از هر استفاده اجباری است |
| `category_translation` | `product_category_name` | Lookup ساده، بدون مشکل |

---

## ۲. جریان معماری (Pipeline Flow)

```
Raw Data (immutable)
   ↓
Ingestion              → type casting فقط، بدون Cleaning منطقی (data/interim)
   ↓
Schema Validation       → آیا ستون‌ها/dtypeها موجودند؟ (Fail Fast)
   ↓
Per-Table Cleaning      → هر جدول جدا، Grain مستند، بدون Merge سنگین (data/processed, پسوند _clean)
   ↓
Business Validation     → referential integrity, range check, temporal consistency
   ↓
Atomic / Common Features → فیچرهای مشترک، هرکدام با available_at مستند (Feature Registry، بخش ۵)
   ↓
Task-Specific Analytical Datasets → یک Dataset اختصاصی به ازای هر Business Question
   ↓
Analytics / ML          → RFM, Segmentation, Predictive Models
   ↓
Power BI / Reports
```

و یک قانون عمودی روی کل این جریان: **Temporal Semantics & Leakage Policy** (بخش ۴) — این دیگر یک Task جدا نیست، بلکه هر Predictive Task باید از آن تبعیت کند.

**چرا اسم پوشه‌ها را به `canonical/` تغییر ندادیم؟** نسخه‌ی v3.0 پیشنهاد داد `orders_clean.parquet` به `canonical/orders.parquet` تغییر نام یابد. این ایده مفهوماً بد نیست، ولی برای این مقیاس پروژه، نام‌گذاری ساده‌ی `*_clean.parquet` مستقیم در `data/processed/` به همان اندازه گویاست و یک سطح پوشه‌بندی اضافه (`canonical/` در کنار احتمالاً `features/`, `analytics/`, `marts/`) صرفاً پیچیدگی ناوبری اضافه می‌کند بدون سود عملکردی — رد شد (جزئیات در بخش ۱۲).

---

## ۳. Phase و Task ها

### Phase 0 — Foundation
**Task 0.1 – Project Setup & Environment**
- هدف: ساختار Repo، `requirements.txt`، `.gitignore`، README اسکلت، محیط مجازی Python
- Output: اسکلت Repo قابل clone و اجرا
- ارزش: **Must Have**

**Task 0.2 – Data Ingestion & Profiling**
- هدف: بارگذاری ۹ فایل خام (type casting فقط)، ذخیره‌ی نسخه‌ی interim، و تولید گزارش Profiling کامل (schema, missing, duplicates, cardinality)
- Output: `data/interim/*.parquet` + `reports/data_profile.md`
- Dependency: 0.1
- ارزش: **Must Have** — این Task باید طبق دو فایل جدا (`ingest.py` برای بارگذاری، `profile.py` برای گزارش‌گیری)، با Docstring کامل و مدیریت خطا نوشته شود (نه اسکریپت اکتشافی خطی)

### Phase 1 — Core Data Layer
**Task 1.1 – Per-Table Cleaning**
- هر ۸ جدول را جدا Clean کن؛ تصمیمات زیر باید صریح گرفته و مستند شوند (نه پیش‌فرض کورکورانه):
  - `geolocation`: Aggregate بر اساس `zip_code_prefix` (میانگین `lat`/`lng`) قبل از هر استفاده.
  - `order_reviews`: تصمیم بگیر با ۸۱۴ مورد `review_id` تکراری چه کنی — گزینه‌ی پیشنهادی: نگه‌داشتن هر دو ردیف با کلید ترکیبی `(review_id, order_id)`، مستندسازی در Grain Registry که `review_id` به‌تنهایی کلید نیست.
  - ۲ سفارش `delivered` بدون تاریخ تحویل و ۶ سفارش `canceled` با تاریخ تحویل: تصمیم صریح (نگه‌داشتن با پرچم / حذف) و ثبت در گزارش.
  - ۹ پرداخت صفر: ۶ تای `voucher` نگه‌داشته می‌شوند (منطقی)؛ ۳ تای `not_defined` پرچم‌گذاری می‌شوند.
- Output: `data/processed/{orders,order_items,payments,reviews,customers,products,sellers,geolocation}_clean.parquet`
- Dependency: 0.2
- ارزش: **Must Have**

**Task 1.2 – Data Validation Layer (دومرحله‌ای)**
- **Schema Validation** (بعد از Ingestion): ستون‌ها/dtypeها.
- **Business Validation** (بعد از Cleaning): `delivery_date >= purchase_date`, `price >= 0`, `review_score ∈ [1,5]`, یکتایی `(order_id, order_item_id)`، یکتایی `(review_id, order_id)` (نه `review_id` تنها — طبق یافته‌ی واقعی).
- Output: `reports/validation_report.md`
- ارزش: **Must Have**

**Task 1.3 – Caching Infrastructure**
- `load_data(rebuild=False)` — یک Pipeline Execution Concern که کل زنجیره‌ی 0.2→1.1→1.2→1.4 را می‌پوشاند؛ یک گره متوالی جدا در گراف نیست.
- ارزش: **Must Have**

**Task 1.4 – Common Feature Layer + Grain Registry + Feature Registry**
- فیچرهای مشترک بین چند Task (`delivery_delay_days`, `order_total_value`, `order_item_count`, ...).
- **جدید ۳.۱:** همراه با این فیچرها، دو فایل مستندسازی سبک (نه Engine اجرایی) ساخته می‌شود — جزئیات در بخش ۵.
- Output: `data/processed/common_features.parquet` + `docs/grain_registry.md` + `docs/feature_registry.md`
- ارزش: **Must Have**

### Phase 2 — EDA & Business Analytics
**Task 2.1 – Business EDA & KPI Dashboard**
- شامل KPIهایی با Denominator صریح (یافته‌ی خوب v3.0): مثلاً `delay_rate = delayed_orders / eligible_delivered_orders`، نه `/ all_orders`. هر KPI باید Denominatorش را در گزارش بنویسد.
- ارزش: **Must Have**

### Phase 3 — Customer Feature Layer
**Task 3.1 – Customer Feature Table**
- Grain: `customer_unique_id`. فقط برای RFM/Segmentation/Business Analytics — نه Predictive Modeling آینده‌محور (طبق Leakage Policy، بخش ۴).
- ارزش: **Must Have**

**Task 3.2 – RFM Analysis & Scoring**
- **جدید ۳.۱:** سه چیز باید صریح در `reports/rfm_summary.csv` یا متادیتای همراهش مستند شوند (ایده‌ی خوب v3.0):
  - **Reference Date** (نقطه‌ی مبنای محاسبه‌ی Recency — مثلاً آخرین تاریخ سفارش در کل دیتاست)
  - **Monetary Definition** (مثلاً `item price + freight`، نه فقط `price`)
  - **Eligible Orders** (مثلاً فقط سفارش‌های `delivered`، نه همه‌ی وضعیت‌ها)
- ارزش: **Must Have**

**Task 3.3 – Customer Segmentation**
- Pipeline: Scaling → Candidate K → Silhouette → Profiling. KMeans به‌عنوان Baseline؛ HDBSCAN فقط اگر KMeans نتیجه‌ی قابل‌تفسیر نداد (نه پیش‌فرض از اول هر دو).
- ارزش: **Must Have**

### Phase 4 — Predictive Modeling
همه‌ی مدل‌های این فاز باید جدول Temporal Semantics (بخش ۴) را قبل از نوشتن کد تکمیل کرده باشند.

**Task 4.1 – Repeat Purchase Prediction**
- Dataset مستقل: `customer_repeat_purchase_dataset.parquet`، Grain: `(customer_unique_id, observation_time)`.
- Features فقط از `purchase_date <= observation_time`؛ Label = خرید مجدد در `prediction_window_days` بعد از آن.
- ⚠️ مقدار `prediction_window_days` (کاندیدهای ۳۰/۶۰/۹۰/۱۲۰ روز) باید در EDA با توزیع واقعی فاصله‌ی بین خریدهای مشتریان تکراری (همان ۳٬۳۴۵ نفر) اعتبارسنجی شود — عدد ۹۰ فقط نقطه‌ی شروع است، نه قطعی.
- Train/Test Split زمانی، نه تصادفی.
- ارزش: **Should Have**

**Task 4.2 – Delivery Delay Prediction**
- Prediction Time: `order_approved_at`. فیچرهای ممنوع: هر چیز مبتنی بر تاریخ تحویل واقعی.
- **اصلاح Grain (از v3.0، یافته‌ی درست):** چون یک سفارش می‌تواند چند Seller داشته باشد، مدل **Order-level** تعریف می‌شود (`one row = one order`) و فیچرهای Seller باید Aggregate شوند: `seller_count`, `min/max/mean_seller_distance` — نه یک `seller_distance` مبهم و تک‌مقداری.
- تعریف Target (`delayed = ...`): **Validation Required**، نه قطعی — باید با داده واقعی (از جمله همان ۲ سفارش delivered بدون تاریخ) نهایی شود.
- ارزش: **Should Have**

**Task 4.3 – Satisfaction Prediction (Post-delivery)**
- Grain: به‌خاطر یافته‌ی واقعی `review_id` غیریکتا، Grain این Task **`(review_id, order_id)`** است، نه صرفاً «one row per review» (اصلاحی که v3.0 هم چون به داده‌ی واقعی ما دسترسی نداشت، از قلم انداخته بود).
- Prediction Time: بعد از تحویل واقعی (Explanatory، نه Pre-delivery).
- نسخه‌ی Pre-delivery: صراحتاً خارج از Scope فعلی (future extension).
- ارزش: **Should Have**

**Task 4.4 – Sales Forecasting (Optional)**
- **جدید ۳.۱:** همیشه یک Baseline ساده (Naive یا Seasonal Naive) قبل از هر مدل پیچیده‌تر (ETS/ARIMA/Prophet) گزارش شود — بدون Baseline، Accuracy یک مدل معنای مستقلی ندارد.
- محدودیت صادقانه: افق کوتاه‌مدت (۱-۳ ماه)، چون داده فقط ۲۰۱۶-۲۰۱۸ را پوشش می‌دهد.
- ارزش: **Nice to Have**

### Phase 5 — Seller & Product Analysis
**Task 5.1 – Seller Performance**
- هر KPI با Denominator صریح مستند می‌شود (مثل Task 2.1).
- ارزش: **Should Have**

**Task 5.2 – Product / Category Analysis**
- ارزش: **Should Have**

### Phase 6 — Recommendation (Optional)
**Task 6.1 – Category-level Co-purchase** — ارزش: **Nice to Have**

### Phase 7 — Dashboard & Storytelling
**Task 7.1 – Power BI Dashboard** — ارزش: **Must Have**
**Task 7.2 – Final Business Report** — ارزش: **Must Have**

---

## ۴. Temporal Semantics & Data Leakage Policy

هر Predictive Task (4.1, 4.2, 4.3, و اختیاراً 4.4) باید این جدول را قبل از نوشتن کد Feature Engineering تکمیل کند:

| Task | Observation/Prediction Time | Feature Availability | Forbidden Features | Label Window |
|---|---|---|---|---|
| 4.1 Repeat Purchase | `T` (لحظه‌ی مشخص در تاریخچه‌ی هر مشتری) | تراکنش‌های `purchase_date <= T` | هر تراکنش با `purchase_date > T` | خرید مجدد در `prediction_window_days` بعد از `T` (کاندید: با EDA تعیین شود) |
| 4.2 Delivery Delay | `order_approved_at` | `order_purchase_timestamp`, `order_estimated_delivery_date`, seller aggregate features (count/min/max/mean distance), فصل, `freight_value` | `order_delivered_carrier_date`, `order_delivered_customer_date` و هر مشتق آن‌ها | تعریف `delayed` — Validation Required |
| 4.3 Satisfaction (Post-delivery) | بعد از تحویل واقعی | `delivery_delay_days` واقعی, قیمت, دسته محصول | ندارد (Task صراحتاً Post-delivery است) | `review_score` همان سفارش، Grain: `(review_id, order_id)` |
| 4.4 Forecasting (اختیاری) | لحظه‌ی ساخت پیش‌بینی ماهانه | فقط داده‌ی ماه‌های قبل | داده‌ی ماه هدف و بعد از آن | افق ۱-۳ ماه |

---

## ۵. Grain Registry و Feature Registry (نسخه‌ی سبک، بدون Engine)

نسخه‌ی v3.0 پیشنهاد داد این‌ها به‌شکل فایل‌های `.yml` با یک Engine اجرایی و Test Suite مجزا پیاده‌سازی شوند. برای مقیاس این پروژه، این overkill است. نسخه‌ی سبک و کافی:

### `docs/grain_registry.md` (جدول ساده)
یک جدول Markdown با ستون‌های: نام جدول/Dataset | Grain | کلید | نکات. همان جدول بخش ۱ این سند نسخه‌ی اول این فایل است؛ هر Dataset جدید (`customer_features`, `delivery_features`, ...) که ساخته می‌شود باید یک ردیف به این جدول اضافه کند.

### `docs/feature_registry.md` (جدول ساده، نه YAML+Engine)
برای فیچرهای مشترک حساس (مثل `delivery_delay_days`)، یک جدول با ستون‌های: نام Feature | Entity/Grain | Available At | Allowed Tasks | Forbidden Tasks. مثال:

| Feature | Entity | Available At | Allowed Tasks | Forbidden Tasks |
|---|---|---|---|---|
| `delivery_delay_days` | order | post_delivery | satisfaction, seller_analysis | delivery_delay_prediction, repeat_purchase |
| `order_total_value` | order | order_approved_at | delivery_delay_prediction, analytics | — |

**تفاوت با v3.0:** این جدول فقط **مستندسازی** است، نه یک سیستم اجرایی که خودکار Feature را Reject کند. اگر بعداً زمان اضافه ماند، می‌توان **یک** تست ساده اضافه کرد (`tests/test_temporal_leakage.py`) که چک کند ستون‌های ممنوعه‌ی جدول بالا وارد ورودی مدل مربوطه نشده باشند — این یک تست کوچک و ارزان است، نه یک Framework کامل.

---

## ۶. Dependency Graph

```
[0.1 Setup] → [0.2 Ingestion & Profiling] → [1.1 Cleaning] → [1.2 Validation]
                                                                    │
                                                          [1.4 Common Features + Registries]
                                                                    │
        ┌──────────┬──────────┬──────────┬───────────────┬────────┴──────┐
        │          │          │          │               │               │
   [2.1 EDA]  [3.1 Cust.   [4.2 Delivery [4.3 Satisfaction] [5.1 Seller  [5.2 Product
        │      Features]    (order-level, [(review_id,       Performance] Analysis]
        │          │        seller agg.)]  order_id) grain]
        │      [3.2 RFM]
        │          │
        │    [3.3 Segmentation]
        │
   [4.1 Repeat Purchase]  (Dataset مستقل، از 1.1/1.2 مستقیم، Window با EDA تعیین می‌شود)
   [4.4 Forecasting]      (اختیاری، مستقل)
   [6.1 Co-purchase]      (اختیاری، مستقل)
        │
        └─────────────┬──────────────────┐
                       │                  │
              [7.1 Power BI]      [7.2 Final Report]

[Caching] ⟲ می‌پوشاند: 0.2 → 1.1 → 1.2 → 1.4  (Infrastructure عمودی، نه گره متوالی)
```

---

## ۷. ساختار Repository (نسخه‌ی نهایی، بدون پوشه‌ی اضافی)

```
olist-ecommerce-analytics/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
│       ├── {orders,order_items,payments,reviews,customers,products,sellers,geolocation}_clean.parquet
│       ├── common_features.parquet
│       ├── customer_features.parquet
│       ├── customer_repeat_purchase_dataset.parquet
│       ├── delivery_features.parquet
│       ├── satisfaction_features.parquet
│       ├── seller_features.parquet
│       └── sales_timeseries.parquet
│
├── src/
│   ├── data/
│   │   ├── ingest.py
│   │   ├── clean.py
│   │   ├── validate.py         # هم Schema هم Business Validation
│   │   └── pipeline.py         # load_data(rebuild=False)
│   ├── features/
│   │   ├── common_features.py
│   │   ├── customer_features.py
│   │   ├── repeat_purchase_dataset.py
│   │   └── rfm.py
│   ├── models/
│   │   ├── segmentation.py
│   │   ├── repeat_purchase.py
│   │   ├── delivery_delay.py
│   │   ├── satisfaction.py
│   │   └── forecasting.py
│   ├── evaluation/
│   │   └── metrics.py
│   └── utils/
│       ├── config.py
│       └── io.py               # شامل منطق caching/hash
│
├── notebooks/
├── models/
├── reports/
├── dashboard/
├── tests/
│   ├── test_clean.py
│   ├── test_validate.py
│   ├── test_features.py
│   ├── test_temporal_leakage.py   # جدید، سبک — فقط چک ستون‌های ممنوعه طبق Feature Registry
│   └── test_pipeline_cache.py
└── docs/
    ├── architecture.md         # همین سند
    ├── grain_registry.md       # جدید ۳.۱ — سبک
    └── feature_registry.md     # جدید ۳.۱ — سبک
```

**نکته:** `src/models/`, `src/features/` و `src/evaluation/` دقیقاً همان ساختاری‌اند که در Task 0.1 ساخته شد — هیچ پوشه‌ی جدیدی (`ml/`, `tasks/`, `marts/`, `config/`, `analytics/` مجزا از `models/`) اضافه نشد، چون برای ۳ مدل predictive این پروژه، آن تفکیک صرفاً هزینه‌ی ناوبری اضافه می‌کرد بدون فایده‌ی واقعی.

---

## ۸. Reusable Components (API)

```python
# src/data/pipeline.py
load_data(rebuild=False) -> dict[str, pd.DataFrame]

# src/data/clean.py
clean_orders(df) -> pd.DataFrame
clean_order_reviews(df) -> pd.DataFrame   # باید (review_id, order_id) uniqueness را رعایت کند، نه فقط review_id
handle_duplicates_geolocation(df) -> pd.DataFrame

# src/data/validate.py
validate_schema(df, expected_schema) -> ValidationResult
validate_business_rules(tables: dict) -> ValidationResult

# src/features/common_features.py
build_common_features(clean_tables: dict) -> pd.DataFrame

# src/features/customer_features.py
build_customer_features(clean_tables: dict, common_features: pd.DataFrame) -> pd.DataFrame
    # Grain: customer_unique_id — فقط RFM/Segmentation/Analytics

# src/features/repeat_purchase_dataset.py
build_repeat_purchase_dataset(clean_tables: dict, observation_time, prediction_window_days=90) -> pd.DataFrame
    # Grain: (customer_unique_id, observation_time)

# src/features/rfm.py
calculate_rfm(customer_features, reference_date, monetary_definition="price+freight", eligible_statuses=["delivered"]) -> pd.DataFrame
    # پارامترهای صریح Reference Date / Monetary / Eligible Orders، نه پیش‌فرض پنهان

# src/models/segmentation.py
fit_segments(rfm_df) -> (model, labels)
get_customer_segment(customer_unique_id: str) -> str

# src/models/repeat_purchase.py
predict_repeat_purchase(customer_unique_id: str) -> float

# src/models/delivery_delay.py
build_order_level_seller_features(order_items_df, sellers_df) -> pd.DataFrame
    # خروجی: seller_count, min/max/mean_seller_distance — نه یک ستون مبهم seller_distance

# الگوی یکسان هر مدل predictive (4.1/4.2/4.3):
preprocess(features_df) -> X, y
train(X, y) -> model
predict(model, X) -> pd.Series
evaluate(model, X_test, y_test) -> dict
save_model(model, path) -> None
```

**Convention سراسری:** هرجا «مشتری» یعنی `customer_unique_id`، نه `customer_id`.

---

## ۹. اولویت‌بندی Portfolio

| سطح | Taskها |
|---|---|
| **Must Have** | 0.1, 0.2, 1.1, 1.2, 1.3, 1.4, 2.1, 3.1, 3.2, 3.3, 7.1, 7.2 |
| **Should Have** | 4.1, 4.2, 4.3, 5.1, 5.2 |
| **Nice to Have** | 4.4, 6.1 |

---

## ۱۰. Roadmap

```
0.1 → 0.2 → 1.1 → 1.2 → 1.4 (+ Grain/Feature Registry)
 → 2.1 → 3.1 → 3.2 (+ متادیتای Reference Date/Monetary/Eligible) → 3.3
 → 4.2 (order-level + seller aggregation, Target: Validation Required)
 → 4.3 (Post-delivery, Grain: review_id+order_id)
 → 4.1 (Dataset مستقل، Window با EDA)
 → 5.1 (+ Denominator صریح) → 5.2
 (اختیاری) 4.4 (+ Baseline اول) → 6.1
 → 7.1 → 7.2
```

---

## ۱۱. جدول تصمیم‌ها (این‌ها هنوز باز و نیازمند بررسی روی داده‌ی واقعی‌اند)

| تصمیم باز | کجا باید حل شود |
|---|---|
| نحوه‌ی برخورد با ۸۱۴ `review_id` تکراری (نگه‌داشتن با کلید ترکیبی در برابر حذف) | Task 1.1 |
| تعریف دقیق `delayed` در Task 4.2 | Task 4.2، با بررسی همان ۲ سفارش delivered بدون تاریخ |
| مقدار `prediction_window_days` در Task 4.1 (۳۰/۶۰/۹۰/۱۲۰) | EDA در Task 4.1، با توزیع واقعی فاصله‌ی خرید ۳٬۳۴۵ مشتری تکراری |
| برخورد با ۲ سفارش `delivered` بدون تاریخ و ۶ سفارش `canceled` با تاریخ تحویل | Task 1.1 |
| برخورد با ۳ پرداخت `not_defined` صفر | Task 1.1 |

---

## ۱۲. چه چیزهایی از v3.0 آگاهانه رد شدند، و چرا

| پیشنهاد v3.0 | تصمیم | دلیل |
|---|---|---|
| تغییر نام `*_clean.parquet` به `canonical/*.parquet` | رد شد | نام‌گذاری ساده‌ی `_clean` مستقیم در `data/processed/` به همان اندازه گویاست؛ یک لایه‌ی پوشه‌بندی اضافه برای این مقیاس پروژه سود عملکردی ندارد، فقط ناوبری را پیچیده‌تر می‌کند. |
| `Feature Registry` به‌شکل YAML + Engine اجرایی که Feature را خودکار Reject می‌کند | نسخه‌ی سبک (جدول Markdown مستندسازی) پذیرفته شد | خودِ سند v3.0 هم در بند ۴۳ گفته «Feature Store واقعی ضروری نیست» — ولی این پیشنهادش عملاً یک Feature Store کوچک بود؛ تناقض داخلی. نسخه‌ی مستندسازی همان فایده‌ی اصلی (شفافیت Availability) را بدون هزینه‌ی Engine می‌دهد. |
| پوشه‌ی `config/` با ۳ فایل yaml مجزا | رد شد | `src/utils/config.py` موجود (Path مرکزی) برای این مقیاس کافی است؛ ۳ فایل yaml اضافه صرفاً پیچیدگی ناوبری می‌افزاید. |
| ماژول `logging.py` + `logs/pipeline.log` ساختاریافته | رد شد (فعلاً) | `print()` برای یک پروژه با این مقیاس و بدون اجرای زمان‌بندی‌شده کافی است؛ اگر بعداً پروژه به CI/Scheduled run رسید، اضافه‌کردنش ارزان است. |
| تفکیک `src/ml/` (mechanics) از `src/tasks/` (business logic) | رد شد | برای ۳ مدل predictive، این تفکیک هزینه‌ی پیمایش بین پوشه‌ها را بالا می‌برد بدون فایده‌ی قابل‌لمس؛ ساختار `src/models/` موجود (که هر فایلش خودش mechanics+business دارد) برای این مقیاس مناسب‌تر است. |
| لایه‌ی `marts/` جدا از `data/processed/analytics/` | رد شد | خروجی‌های موجود در `data/processed/` (که مستقیماً برای Power BI هم مصرف می‌شوند) از قبل «BI-ready» هستند؛ یک لایه‌ی کپی اضافه فقط تعداد فایل‌ها را زیاد می‌کند. |
| CI با GitHub Actions | به فاز «اگه وقت اضافه موند» منتقل شد | ارزش واقعی دارد ولی برای رسیدن به یک نسخه‌ی *کامل* از پروژه اولویت پایین‌تری از خودِ Task هایی مثل Segmentation یا Delivery Prediction دارد. |
| `hashing.py` جدا | رد شد | همان منطق در `src/utils/io.py` (که در v2.1 تعریف شده) پوشش داده می‌شود؛ ماژول جدا اضافه نمی‌کند. |

**آنچه از v3.0 واقعاً پذیرفته شد** (چون رایگان یا کم‌هزینه و واقعاً درست بودند): سه قانون سراسری (بخش ۰)، اصلاح Grain مدل Delivery با Seller Aggregation، الزام Denominator صریح برای KPIها، الزام Baseline قبل از Forecasting، متادیتای صریح RFM (Reference Date/Monetary/Eligible Orders)، و نسخه‌ی سبک Grain/Feature Registry.

---

## نتیجه

این نسخه معماری «به‌اندازه‌ی مسئله پیچیده» است، نه بیشتر: هیچ Task جدیدی نسبت به v2.1 اضافه نشد، هیچ زیرساخت سنگین (CI، Logging Framework، Feature Store واقعی، تفکیک ml/tasks) وارد نشد، ولی هر باگ واقعی که در v3.0 درست تشخیص داده شده بود (Grain مبهم Delivery، Denominator نادقیق KPI، RFM بدون متادیتا) اصلاح شد و با یافته‌های اولیه‌ی داده (`review_id` غیریکتا، ۷۷۵ سفارش بی‌آیتم، ۲۶٪ Duplicate در geolocation) تقویت شد — یافته‌هایی که Task 0.2 باید به‌شکل حرفه‌ای و رسمی بازتولید و در `reports/data_profile.md` ثبت کند. این سند از Task 0.1 به بعد مرجع نهایی پروژه است؛ هیچ کاری هنوز اجرا نشده.
