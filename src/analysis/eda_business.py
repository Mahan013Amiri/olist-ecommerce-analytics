"""Business EDA on order-level data. (Task 2.1)"""

import pandas as pd


def prepare_eda_data(
    clean_tables: dict[str, pd.DataFrame],
    common_features: pd.DataFrame,
) -> pd.DataFrame:
    """Build the order-level EDA spine.

    Merges the common feature table (order_item_count, order_total_value,
    order_freight_value, delivery_delay_days, is_delayed) with order status/
    timestamp (from `orders`) and customer state (from `customers`), so that
    downstream EDA functions have a single ready-to-use table.

    Parameters
    ----------
    clean_tables : dict[str, pd.DataFrame]
        Output of `load_data()` — must contain "orders" and "customers".
    common_features : pd.DataFrame
        Output of `build_common_features()`. Grain: order_id.

    Returns
    -------
    pd.DataFrame
        Grain: order_id. Columns = common_features columns +
        order_status, order_purchase_timestamp, customer_state.
    """
    orders = clean_tables["orders"][
        ["order_id", "customer_id", "order_status", "order_purchase_timestamp"]
    ]
    customers = clean_tables["customers"][["customer_id", "customer_state"]]

    df = common_features.merge(orders, on="order_id", how="left")
    df = df.merge(customers, on="customer_id", how="left")

    return df

def delivery_delay_distribution(df: pd.DataFrame) -> dict:
    """Distribution stats for delivery_delay_days, eligible orders only.

    Eligible = orders where delivery_delay_days is not null (i.e. status
    == "delivered" with both approved and delivered dates present).
    """
    eligible = df["delivery_delay_days"].dropna()

    return {
        "n_eligible": int(eligible.shape[0]),
        "mean": float(eligible.mean()),
        "std": float(eligible.std()),
        "p10": float(eligible.quantile(0.10)),
        "p25": float(eligible.quantile(0.25)),
        "p50_median": float(eligible.quantile(0.50)),
        "p75": float(eligible.quantile(0.75)),
        "p90": float(eligible.quantile(0.90)),
    }


def monthly_delay_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly trend of delay rate and average delay, eligible orders only.

    Grain: calendar month (from order_purchase_timestamp).
    """
    eligible = df.dropna(subset=["delivery_delay_days"]).copy()
    eligible["purchase_month"] = (
        eligible["order_purchase_timestamp"].dt.to_period("M").astype(str)
    )

    trend = (
        eligible.groupby("purchase_month")
        .agg(
            n_orders=("order_id", "count"),
            delay_rate=("is_delayed", "mean"),
            avg_delay_days=("delivery_delay_days", "mean"),
        )
        .reset_index()
    )

    return trend

def delay_by_state(df: pd.DataFrame) -> pd.DataFrame:
    """Delay rate and average delay by customer_state, eligible orders only.

    Sorted descending by delay_rate so the worst-performing states are
    on top.
    """
    eligible = df.dropna(subset=["delivery_delay_days"])

    by_state = (
        eligible.groupby("customer_state")
        .agg(
            n_orders=("order_id", "count"),
            delay_rate=("is_delayed", "mean"),
            avg_delay_days=("delivery_delay_days", "mean"),
        )
        .sort_values("delay_rate", ascending=False)
        .reset_index()
    )

    return by_state

def order_status_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Order status distribution, with no-item order counts per status.

    Full grain (all 99,441 orders) — no filtering. Highlights which
    statuses concentrate the ~775 orders with order_item_count == 0.
    """
    total = len(df)

    breakdown = (
        df.groupby("order_status")
        .agg(
            n_orders=("order_id", "count"),
            n_no_items=("order_item_count", lambda s: int((s == 0).sum())),
        )
        .reset_index()
    )

    breakdown["pct_of_total"] = (breakdown["n_orders"] / total * 100).round(2)
    breakdown["pct_no_items_within_status"] = (
        breakdown["n_no_items"] / breakdown["n_orders"] * 100
    ).round(2)

    return breakdown.sort_values("n_orders", ascending=False).reset_index(drop=True)

def attach_review_scores(
    df: pd.DataFrame, clean_tables: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Attach average review_score per order_id to the EDA spine.

    A single order can have multiple review rows (grain: review_id,
    order_id per the Grain Registry), so scores are averaged per order
    for this order-level analysis.
    """
    reviews = clean_tables["reviews"][["order_id", "review_score"]]
    avg_review = reviews.groupby("order_id", as_index=False)["review_score"].mean()

    return df.merge(avg_review, on="order_id", how="left")


def review_score_delay_correlation(df_with_reviews: pd.DataFrame) -> dict:
    """Pearson correlation between delivery_delay_days and review_score.

    Only orders with both a non-null delivery_delay_days and a non-null
    review_score are included.
    """
    subset = df_with_reviews.dropna(subset=["delivery_delay_days", "review_score"])

    correlation = subset["delivery_delay_days"].corr(subset["review_score"])

    return {
        "n_orders": int(subset.shape[0]),
        "pearson_corr": float(correlation),
    }

import matplotlib.pyplot as plt

from src.utils.config import REPORTS_DIR

FIGURES_DIR = REPORTS_DIR / "figures"


def _ensure_figures_dir() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def plot_delay_distribution(df: pd.DataFrame) -> str:
    """Histogram of delivery_delay_days for eligible orders. Returns path."""
    _ensure_figures_dir()
    eligible = df["delivery_delay_days"].dropna()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(eligible, bins=60, color="steelblue", edgecolor="white")
    ax.axvline(0, color="red", linestyle="--", linewidth=1, label="On-time (0 days)")
    ax.set_xlabel("Delivery delay (days): actual - estimated")
    ax.set_ylabel("Number of orders")
    ax.set_title("Distribution of Delivery Delay (eligible delivered orders)")
    ax.legend()

    path = FIGURES_DIR / "delay_distribution.png"
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def plot_monthly_delay_trend(trend: pd.DataFrame) -> str:
    """Line chart of monthly delay_rate over time. Returns path."""
    _ensure_figures_dir()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(trend["purchase_month"], trend["delay_rate"], marker="o", color="darkorange")
    ax.set_xlabel("Purchase month")
    ax.set_ylabel("Delay rate")
    ax.set_title("Monthly Delivery Delay Rate")
    ax.tick_params(axis="x", rotation=90)

    path = FIGURES_DIR / "monthly_delay_trend.png"
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def plot_delay_by_state(by_state: pd.DataFrame) -> str:
    """Bar chart of delay_rate by customer_state. Returns path."""
    _ensure_figures_dir()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(by_state["customer_state"], by_state["delay_rate"], color="firebrick")
    ax.set_xlabel("Customer state")
    ax.set_ylabel("Delay rate")
    ax.set_title("Delivery Delay Rate by Customer State")
    ax.tick_params(axis="x", rotation=90)

    path = FIGURES_DIR / "delay_by_state.png"
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def plot_order_status_breakdown(status_breakdown: pd.DataFrame) -> str:
    """Bar chart of order count by order_status. Returns path."""
    _ensure_figures_dir()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(status_breakdown["order_status"], status_breakdown["n_orders"], color="seagreen")
    ax.set_xlabel("Order status")
    ax.set_ylabel("Number of orders")
    ax.set_title("Order Status Breakdown")
    ax.tick_params(axis="x", rotation=45)

    path = FIGURES_DIR / "order_status_breakdown.png"
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return str(path)

def generate_eda_report(
    clean_tables: dict[str, pd.DataFrame],
    common_features: pd.DataFrame,
) -> str:
    """Run the full Task 2.1 EDA pipeline and write reports/task_2_1_eda.md.

    Calls every EDA function in sequence, generates the four figures,
    and writes a Markdown report summarizing the findings. Returns the
    path to the written report.
    """
    df = prepare_eda_data(clean_tables, common_features)
    dist = delivery_delay_distribution(df)
    trend = monthly_delay_trend(df)
    by_state = delay_by_state(df)
    status_breakdown = order_status_breakdown(df)
    df_reviews = attach_review_scores(df, clean_tables)
    corr = review_score_delay_correlation(df_reviews)

    plot_delay_distribution(df)
    plot_monthly_delay_trend(trend)
    plot_delay_by_state(by_state)
    plot_order_status_breakdown(status_breakdown)

    low_n_states = by_state[by_state["n_orders"] < 100]["customer_state"].tolist()
    low_n_months = trend[trend["n_orders"] < 50]["purchase_month"].tolist()

    lines = []
    lines.append("# Task 2.1 — Business EDA Report\n")
    lines.append(
        f"Grain: `order_id`. Eligible orders for delay analysis "
        f"(delivered with both approved/delivered dates): "
        f"**{dist['n_eligible']:,}** out of {len(df):,} total orders.\n"
    )

    lines.append("## 1. Delivery Delay Distribution\n")
    lines.append(
        f"- Mean: {dist['mean']:.2f} days | Std: {dist['std']:.2f}\n"
        f"- P10: {dist['p10']:.1f} | P25: {dist['p25']:.1f} | "
        f"P50 (median): {dist['p50_median']:.1f} | "
        f"P75: {dist['p75']:.1f} | P90: {dist['p90']:.1f}\n"
        f"- Negative values mean orders arrived *earlier* than the "
        f"estimated delivery date.\n"
    )
    lines.append("![Delivery Delay Distribution](figures/delay_distribution.png)\n")

    lines.append("## 2. Monthly Delay Trend\n")
    if low_n_months:
        lines.append(
            f"⚠️ Months with very low order volume (n < 50), treat as "
            f"statistically unreliable: {', '.join(low_n_months)}.\n"
        )
    lines.append("![Monthly Delay Trend](figures/monthly_delay_trend.png)\n")

    lines.append("## 3. Delay Rate by Customer State\n")
    lines.append("Top 5 worst delay rates:\n")
    lines.append(by_state.head(5).to_markdown(index=False) + "\n")
    if low_n_states:
        lines.append(
            f"\n⚠️ States with very low order volume (n < 100), treat "
            f"delay rate as statistically unreliable: "
            f"{', '.join(low_n_states)}.\n"
        )
    lines.append("![Delay Rate by State](figures/delay_by_state.png)\n")

    lines.append("## 4. Order Status Breakdown\n")
    lines.append(status_breakdown.to_markdown(index=False) + "\n")
    lines.append(
        f"\nTotal orders with zero items: **{status_breakdown['n_no_items'].sum()}**. "
        f"Concentrated mostly in `unavailable` and `canceled`, as expected. "
        f"Note: `shipped` (1) and `invoiced` (2) with zero items are "
        f"data-quality anomalies worth flagging.\n"
    )
    lines.append("![Order Status Breakdown](figures/order_status_breakdown.png)\n")

    lines.append("## 5. Review Score vs Delivery Delay\n")
    lines.append(
        f"- Orders with both a review and a valid delay: "
        f"**{corr['n_orders']:,}**\n"
        f"- Pearson correlation (delay vs review_score): "
        f"**{corr['pearson_corr']:.3f}**\n"
        f"- Interpretation: longer delays are associated with lower "
        f"review scores (moderate negative correlation).\n"
    )

    report_text = "\n".join(lines)

    report_path = REPORTS_DIR / "task_2_1_eda.md"
    report_path.write_text(report_text, encoding="utf-8")

    return str(report_path)


if __name__ == "__main__":
    from src.data.pipeline import load_data
    from src.features.common_features import build_common_features

    tables = load_data(rebuild=False)
    features = build_common_features(tables)

    output_path = generate_eda_report(tables, features)
    print(f"EDA report written to: {output_path}")