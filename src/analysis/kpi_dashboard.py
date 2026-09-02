"""KPI dashboard with explicit denominators. (Task 2.1)"""

import pandas as pd


def compute_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Compute business KPIs, each with an explicit numerator/denominator.

    Parameters
    ----------
    df : pd.DataFrame
        Output of `attach_review_scores()` — order-level, with
        order_status, delivery_delay_days, is_delayed, order_item_count,
        order_total_value, order_freight_value, review_score.

    Returns
    -------
    pd.DataFrame
        One row per KPI: kpi_name, numerator, denominator, value,
        denominator_definition.
    """
    total_orders = len(df)
    eligible = df.dropna(subset=["delivery_delay_days"])
    n_eligible = len(eligible)
    delayed = eligible[eligible["is_delayed"] == True]  # noqa: E712
    n_delayed = len(delayed)
    with_items = df[df["order_item_count"] > 0]
    delivered_with_review = df[
        (df["order_status"] == "delivered") & df["review_score"].notna()
    ]

    rows = []

    rows.append({
        "kpi_name": "delivery_delay_rate",
        "numerator": n_delayed,
        "denominator": n_eligible,
        "value": n_delayed / n_eligible,
        "denominator_definition": "eligible delivered orders (has delivery_delay_days)",
    })

    on_time = eligible[eligible["delivery_delay_days"] <= 0]
    rows.append({
        "kpi_name": "on_time_delivery_rate",
        "numerator": len(on_time),
        "denominator": n_eligible,
        "value": len(on_time) / n_eligible,
        "denominator_definition": "eligible delivered orders (has delivery_delay_days)",
    })

    rows.append({
        "kpi_name": "avg_delivery_delay_days",
        "numerator": eligible["delivery_delay_days"].sum(),
        "denominator": n_eligible,
        "value": eligible["delivery_delay_days"].mean(),
        "denominator_definition": "eligible delivered orders (has delivery_delay_days)",
    })

    rows.append({
        "kpi_name": "avg_delay_of_late_orders",
        "numerator": delayed["delivery_delay_days"].sum(),
        "denominator": n_delayed,
        "value": delayed["delivery_delay_days"].mean() if n_delayed else float("nan"),
        "denominator_definition": "orders where is_delayed == True",
    })

    n_delivered = (df["order_status"] == "delivered").sum()
    rows.append({
        "kpi_name": "order_completion_rate",
        "numerator": n_delivered,
        "denominator": total_orders,
        "value": n_delivered / total_orders,
        "denominator_definition": "all orders",
    })

    rows.append({
        "kpi_name": "order_with_item_rate",
        "numerator": len(with_items),
        "denominator": total_orders,
        "value": len(with_items) / total_orders,
        "denominator_definition": "all orders",
    })

    n_canceled = (df["order_status"] == "canceled").sum()
    rows.append({
        "kpi_name": "canceled_rate",
        "numerator": n_canceled,
        "denominator": total_orders,
        "value": n_canceled / total_orders,
        "denominator_definition": "all orders",
    })

    freight_sum = with_items["order_freight_value"].sum()
    value_sum = with_items["order_total_value"].sum()
    rows.append({
        "kpi_name": "freight_to_value_ratio",
        "numerator": freight_sum,
        "denominator": value_sum,
        "value": freight_sum / value_sum,
        "denominator_definition": "sum(order_total_value) over orders with items",
    })

    rows.append({
        "kpi_name": "avg_review_score",
        "numerator": delivered_with_review["review_score"].sum(),
        "denominator": len(delivered_with_review),
        "value": delivered_with_review["review_score"].mean(),
        "denominator_definition": "delivered orders with a non-null review_score",
    })

    return pd.DataFrame(rows)

from pathlib import Path

from src.utils.config import PROCESSED_DATA_DIR, REPORTS_DIR
from src.utils.io import write_parquet


def generate_kpi_report(kpis: pd.DataFrame) -> str:
    """Write a human-readable Markdown KPI report. Returns the path."""
    lines = []
    lines.append("# Task 2.1 — KPI Report\n")
    lines.append(
        "Every KPI below states its exact denominator — no rate is "
        "computed over an implicit or ambiguous base.\n"
    )

    display = kpis.copy()
    display["numerator"] = display["numerator"].round(2)
    display["denominator"] = display["denominator"].round(2)
    display["value"] = display["value"].round(4)

    lines.append(display.to_markdown(index=False) + "\n")

    report_path = REPORTS_DIR / "task_2_1_kpi_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    return str(report_path)


if __name__ == "__main__":
    from src.data.pipeline import load_data
    from src.features.common_features import build_common_features
    from src.analysis.eda_business import prepare_eda_data, attach_review_scores

    tables = load_data(rebuild=False)
    features = build_common_features(tables)

    df = prepare_eda_data(tables, features)
    df_reviews = attach_review_scores(df, tables)

    kpis = compute_kpis(df_reviews)

    parquet_path = PROCESSED_DATA_DIR / "kpi_dashboard.parquet"
    write_parquet(kpis, parquet_path)
    print(f"KPI dashboard written to: {parquet_path}")

    report_path = generate_kpi_report(kpis)
    print(f"KPI report written to: {report_path}")