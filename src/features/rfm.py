"""RFM (Recency, Frequency, Monetary) analysis and scoring. (Task 3.2)

Input: customer_features (Task 3.1 output) — full order history per
customer_unique_id. No clean_tables needed; everything required already
lives in that table.

--- Explicit RFM decisions (per architecture.md, Task 3.2 requirements) ---

Reference Date:
    Defaults to max(last_purchase_date) across all customers — i.e. the
    latest order date in the whole dataset. Fixed and reproducible, since
    this is closed historical data (2016-2018); datetime.now() would be
    meaningless here. Can be overridden via the `reference_date` parameter.

Frequency & Monetary — eligible orders:
    Both are built from total_orders_delivered / total_spend / total_freight,
    which Task 3.1 already restricts to order_status == "delivered". This
    "delivered only" decision is therefore locked in at Task 3.1, not here —
    there is no eligible_statuses parameter in this function, because
    customer_features does not carry per-status monetary breakdowns to make
    such a parameter actually effective. Passing one here would be a
    misleading API.

Recency:
    Based on last_purchase_date, which reflects ALL orders (any status),
    not just delivered ones. Recency should capture "how recently did this
    customer engage", not "how recently did a delivered order happen" — a
    customer who ordered last week (not yet delivered) is still recently
    active.

Monetary definition:
    "price+freight" (default) = total_spend + total_freight.
    "price" = total_spend only.
    Both are computed exclusively from delivered orders (see above).

Customers with NO delivered order (total_orders_delivered == 0):
    Excluded from the RFM table entirely. total_spend/total_freight are NaN
    for these customers (per Task 3.1's "no data != zero" convention) — we
    cannot say they are "low value" (Monetary=0); we simply have no
    fulfilled-purchase data to judge them on. As of Task 3.1 there were
    2,738 such customers; the exact count excluded is logged at build time
    and written into the metadata report.

Scoring:
    Quantile-based (up to 5 levels), with an automatic dual-regime
    strategy — see _quantile_score for full rationale. Columns without a
    dominant tied value (Recency, Monetary here) get standard
    population-balanced (~20% each) quintiles. Columns with a heavily
    dominant tied value (Frequency here, ~97% tied at 1 order) fall back
    to distinct-value-based binning, which sacrifices population balance
    but preserves tail discrimination that population-weighted binning
    would otherwise destroy.
"""

from datetime import datetime

import pandas as pd


def _quantile_score(series: pd.Series, ascending: bool, dominant_share_threshold: float = 0.30) -> pd.Series:
    """Assign quantile-based scores (up to 5 levels): tie-safe, tail-safe,
    AND population-balanced whenever the data allows it.

    Two binning regimes, chosen automatically per column:

    1. STANDARD regime (no single value dominates > dominant_share_threshold
       of rows) — e.g. Recency, Monetary here. Uses rank(method="average")
       so tied raw values get an identical (averaged) rank, then qcut on
       that rank. This produces genuinely population-balanced ~20% bins
       (the standard RFM expectation) while still being tie-safe: unlike
       rank(method="first"), identical raw values can never land in
       different bins.

    2. HEAVY-TIE regime (one value covers > dominant_share_threshold of
       rows) — e.g. Frequency here, ~97% of eligible customers tied at
       value=1. In this regime, population-weighted quantiles are
       meaningless: the dominant value alone exceeds every quantile
       threshold, so qcut's duplicates="drop" collapses ALL bin edges into
       one, losing every distinction — including in the tail (a customer
       with 20 orders would score identically to a one-time buyer). To
       avoid this, bin edges are instead computed over the space of
       DISTINCT values (unweighted by row count): the dominant value still
       gets a single, uniform score (tie-safe), but rarer values in the
       tail (2, 3, ..., 20+ orders) remain separable into higher bins
       (tail-safe). This intentionally does NOT produce ~20% population
       bins — with 97% of rows sharing one value, no method can.

    ascending=True  -> higher raw value = higher score (Frequency, Monetary)
    ascending=False -> lower raw value = higher score (Recency: fewer days
                        since last purchase is "better")
    """
    direction = series if ascending else -series

    dominant_share = direction.value_counts(normalize=True, dropna=False).iloc[0]

    if dominant_share > dominant_share_threshold:
        unique_sorted = pd.Series(direction.unique()).sort_values().reset_index(drop=True)
        n_unique = len(unique_sorted)
        if n_unique == 1:
            return pd.Series(3, index=series.index, dtype=int)
        n_bins = min(5, n_unique)
        value_bins = pd.qcut(unique_sorted, n_bins, labels=False, duplicates="drop")
        value_to_score = dict(zip(unique_sorted, value_bins + 1))
        return direction.map(value_to_score).astype(int)

    ranks = direction.rank(method="average")
    scores = pd.qcut(ranks, 5, labels=False, duplicates="drop")
    return (scores + 1).astype(int)

def calculate_rfm(
    customer_features: pd.DataFrame,
    reference_date: pd.Timestamp | None = None,
    monetary_definition: str = "price+freight",
) -> pd.DataFrame:
    """Build the RFM table from Task 3.1's customer_features.

    Parameters
    ----------
    customer_features : pd.DataFrame
        Output of build_customer_features() (Task 3.1). Must contain:
        customer_unique_id, last_purchase_date, total_orders_delivered,
        total_spend, total_freight.
    reference_date : pd.Timestamp, optional
        Recency anchor date. Defaults to the max last_purchase_date across
        all customers (see module docstring).
    monetary_definition : {"price+freight", "price"}, default "price+freight"
        Whether Monetary includes freight or not. Both variants are
        computed exclusively from delivered orders (locked in at Task 3.1).

    Returns
    -------
    pd.DataFrame
        One row per customer_unique_id (only customers with
        total_orders_delivered > 0), with columns:
        - recency_days, frequency, monetary
        - R_score, F_score, M_score (up to 5 levels; may be fewer distinct
          levels for columns with few distinct raw values — see
          _quantile_score)
        - rfm_segment (str, e.g. "455")
        - rfm_score_sum (int)
    """
    if monetary_definition not in ("price+freight", "price"):
        raise ValueError(
            f"monetary_definition must be 'price+freight' or 'price', got {monetary_definition!r}"
        )

    eligible = customer_features[customer_features["total_orders_delivered"] > 0].copy()

    if reference_date is None:
        reference_date = customer_features["last_purchase_date"].max()

    eligible["recency_days"] = (reference_date - eligible["last_purchase_date"]).dt.days
    eligible["frequency"] = eligible["total_orders_delivered"]

    if monetary_definition == "price+freight":
        eligible["monetary"] = eligible["total_spend"] + eligible["total_freight"]
    else:
        eligible["monetary"] = eligible["total_spend"]

    eligible["R_score"] = _quantile_score(eligible["recency_days"], ascending=False)
    eligible["F_score"] = _quantile_score(eligible["frequency"], ascending=True)
    eligible["M_score"] = _quantile_score(eligible["monetary"], ascending=True)

    eligible["rfm_segment"] = (
        eligible["R_score"].astype(str)
        + eligible["F_score"].astype(str)
        + eligible["M_score"].astype(str)
    )
    eligible["rfm_score_sum"] = eligible["R_score"] + eligible["F_score"] + eligible["M_score"]

    result_cols = [
        "customer_unique_id",
        "recency_days",
        "frequency",
        "monetary",
        "R_score",
        "F_score",
        "M_score",
        "rfm_segment",
        "rfm_score_sum",
    ]
    return eligible[result_cols].reset_index(drop=True)


if __name__ == "__main__":
    from src.data.pipeline import load_data
    from src.features.common_features import build_common_features
    from src.features.customer_features import build_customer_features
    from src.utils.config import PROCESSED_DATA_DIR, REPORTS_DIR

    clean_tables = load_data(rebuild=False)
    common_features = build_common_features(clean_tables)
    customer_features = build_customer_features(clean_tables, common_features)

    reference_date = customer_features["last_purchase_date"].max()
    monetary_definition = "price+freight"

    total_customers = len(customer_features)
    excluded = int((customer_features["total_orders_delivered"] == 0).sum())

    rfm = calculate_rfm(
        customer_features,
        reference_date=reference_date,
        monetary_definition=monetary_definition,
    )

    r_levels = rfm["R_score"].nunique()
    f_levels = rfm["F_score"].nunique()
    m_levels = rfm["M_score"].nunique()

    csv_path = REPORTS_DIR / "rfm_summary.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    rfm.to_csv(csv_path, index=False)

    meta_path = REPORTS_DIR / "rfm_metadata.md"
    meta_path.write_text(
        "# RFM Metadata (Task 3.2)\n\n"
        f"- **Reference Date**: {reference_date}\n"
        f"- **Monetary Definition**: {monetary_definition}\n"
        f"- **Eligible Orders**: order_status == 'delivered' (locked in at Task 3.1)\n"
        f"- **Total customers (customer_features)**: {total_customers:,}\n"
        f"- **Excluded (0 delivered orders)**: {excluded:,}\n"
        f"- **Included in RFM**: {len(rfm):,}\n"
        f"- **R_score distinct levels**: {r_levels} (of max 5)\n"
        f"- **F_score distinct levels**: {f_levels} (of max 5) — expected low-ish; "
        f"~97% of eligible customers are tied at frequency=1\n"
        f"- **M_score distinct levels**: {m_levels} (of max 5)\n"
        f"- **Generated at**: {datetime.now().isoformat(timespec='seconds')}\n",
        encoding="utf-8",
    )

    print(f"OK: {len(rfm):,} rows -> {csv_path}")
    print(f"Metadata -> {meta_path}")
    print(f"Distinct levels — R:{r_levels} F:{f_levels} M:{m_levels}")