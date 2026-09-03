# Olist Brazilian E-Commerce Analytics

End-to-end analytics and predictive modeling project on the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

Architecture reference: [`docs/architecture.md`](docs/architecture.md) (v3.1)

## Project Structure

```
olist-ecommerce-analytics/
├── data/
│   ├── raw/          # Original CSV files (not committed)
│   ├── interim/      # Type-cast parquet (Task 0.2)
│   └── processed/    # Cleaned tables + feature datasets
├── src/
│   ├── data/         # ingest, clean, validate, pipeline
│   ├── features/     # feature engineering
│   ├── models/       # ML models
│   ├── evaluation/   # metrics
│   └── utils/        # config, io
├── notebooks/        # Exploratory analysis
├── models/           # Saved trained models
├── reports/          # Generated reports
├── dashboard/        # Power BI files
├── tests/
└── docs/
```

## Setup

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd olist-ecommerce-analytics
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Download raw data

Download the 9 CSV files from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place them in `data/raw/`:

| File |
|---|
| `olist_customers_dataset.csv` |
| `olist_orders_dataset.csv` |
| `olist_order_items_dataset.csv` |
| `olist_order_payments_dataset.csv` |
| `olist_order_reviews_dataset.csv` |
| `olist_products_dataset.csv` |
| `olist_sellers_dataset.csv` |
| `olist_geolocation_dataset.csv` |
| `product_category_name_translation.csv` |

### 4. Verify setup

```bash
python -c "from src.utils.config import PROJECT_ROOT; print(PROJECT_ROOT)"
pytest
```
## Running the Pipeline So Far

```bash
python -m src.data.ingest    # loads 9 raw CSVs, casts types, saves to data/interim/
python -m src.data.profile   # profiles the interim tables, saves reports/data_profile.md
python -m src.data.validate  # runs schema + business validation, saves reports/validation_report.md
```

See [`reports/data_profile.md`](reports/data_profile.md) for the latest profiling results (schema, missing values, duplicates, and known findings verification).

## Architecture Principles

1. **Grain First** — know what each row represents before any join
2. **Time First** — features must be available at prediction time
3. **Business First** — every metric supports a business decision

## Task Progress

| Phase | Task | Status |
|---|---|---|
| 0 | 0.1 Project Setup | Done |
| 0 | 0.2 Ingestion & Profiling | Done |
| 1 | 1.1 Per-Table Cleaning | Done |
| 1 | 1.2 Validation | Done |
| 1 | 1.3 Caching Pipeline | Done |
| 1 | 1.4 Common Features | Done |
| 2 | 2.1 Business EDA & KPI Dashboard | Done |
| 3 | 3.1 Customer Feature Table | Done |
| 3 | 3.2 RFM Analysis & Scoring | Done |

For a detailed breakdown of what was done and found in each task, see [`docs/progress_log.md`](docs/progress_log.md).
See [`docs/architecture.md`](docs/architecture.md) for the full roadmap.

## Convention

Throughout this project, **"customer"** always means `customer_unique_id`, not `customer_id`.
