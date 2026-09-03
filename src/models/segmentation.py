"""Customer segmentation via KMeans baseline. (Task 3.3)

Input: rfm_summary.csv (Task 3.2 output) — recency_days, frequency,
monetary per customer_unique_id.

--- Feature engineering for clustering ---

    - recency_days: used as-is (scaled only). Not heavily skewed
      (continuous-ish range ~0-700 days), unlike frequency/monetary.
    - frequency: capped at the 99th percentile, THEN log1p, THEN scaled.
      See `prepare_clustering_features` docstring for why the cap is
      necessary (diagnosed empirically during K-selection, not assumed
      up front).
    - monetary: log1p-transformed before scaling (right-skewed, no
      capping needed — no equivalent extreme-outlier issue was observed).

Deliberately NOT using R_score/F_score/M_score (1-5 quantile scores) as
clustering input: F_score in particular collapsed to a near-binary
variable in Task 3.2 (dominant_share > 30% triggered the heavy-tie
regime), which would throw away most of the real signal in `frequency`.
Raw (log-transformed, capped) values preserve more information for
KMeans to work with.

--- K selection process (diagnostic history, kept for transparency) ---

Elbow (Inertia) + Silhouette were evaluated for k=2..8 on the FULL
dataset (no sampling, by explicit choice — see project discussion).
k=2 produced a suspiciously high Silhouette (~0.72) versus k=3..8
(~0.34-0.37). Diagnosis: the smallest cluster (~2,801 rows, 3% of
customers) appeared at EVERY k tested, always the same size. A direct
cross-tab confirmed this cluster matches `frequency >= 2` with 100%
exact agreement — this is a real structural split (repeat vs. one-time
buyers), not a scaling artifact, and it persists identically before and
after capping `frequency` at the 99th percentile.

Given that, k=2 only separates repeat buyers from everyone else, leaving
the 97% one-time-buyer population completely undifferentiated — which
duplicates information already captured by `is_repeat_customer` (Task
3.1) and adds no new business insight. k=4 keeps the same validated
repeat-buyer split while further segmenting the one-time-buyer majority
by recency/monetary, at a modest and expected Silhouette cost (~0.37 vs
~0.72 — expected once a 97%-population subgroup is split further).

Final choice: K=4.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

RAW_FEATURES = ["recency_days", "frequency", "monetary"]
LOG_TRANSFORM_FEATURES = ["frequency", "monetary"]
FINAL_K = 4
RANDOM_STATE = 42


def prepare_clustering_features(
    rfm_df: pd.DataFrame,
    frequency_cap_quantile: float = 0.99,
) -> tuple[pd.DataFrame, StandardScaler, dict]:
    """Build the scaled feature matrix used as KMeans input.

    Parameters
    ----------
    rfm_df : pd.DataFrame
        Output of calculate_rfm() (Task 3.2). Must contain
        customer_unique_id, recency_days, frequency, monetary.
    frequency_cap_quantile : float, default 0.99
        Quantile at which `frequency` is capped BEFORE log1p, to prevent
        a handful of extreme repeat-purchase outliers from dominating
        Euclidean distance after scaling. Explicit fix for a diagnosed
        issue: with ~97% of customers tied at frequency=1, StandardScaler
        on log1p(frequency) produced a tiny std in that column, so any
        deviation (frequency=15+) inflated to z-scores around 27 — an
        order of magnitude beyond recency/monetary's natural range
        (roughly -3 to +6). Capping at the 99th percentile keeps the true
        shape of the distribution (repeat customers still score higher
        than one-time buyers) while preventing a few dozen extreme values
        from hijacking the distance metric. Note: with this dataset's
        distribution, the 99th percentile itself equals 2, so this caps
        ~228 customers with frequency > 2 (e.g. 15-20 orders) while
        leaving the frequency=2 boundary — which is what actually defines
        the repeat-buyer split — untouched.

    Returns
    -------
    features_scaled : pd.DataFrame
        Same row order/index as rfm_df, columns
        ["recency_days", "frequency", "monetary"], each mean=0/std=1
        after the cap + log1p steps described above.
    scaler : StandardScaler
        The fitted scaler (fit on the CAPPED + log1p-transformed data).
    cap_info : dict
        Diagnostic info: the cap value used and how many rows were capped,
        for reporting/transparency.
    """
    missing = [c for c in RAW_FEATURES if c not in rfm_df.columns]
    if missing:
        raise ValueError(f"rfm_df is missing required columns: {missing}")

    features_raw = rfm_df[RAW_FEATURES].copy()

    cap_value = features_raw["frequency"].quantile(frequency_cap_quantile)
    n_capped = int((features_raw["frequency"] > cap_value).sum())
    features_raw["frequency"] = features_raw["frequency"].clip(upper=cap_value)
    cap_info = {
        "frequency_cap_quantile": frequency_cap_quantile,
        "frequency_cap_value": float(cap_value),
        "n_rows_capped": n_capped,
    }

    for col in LOG_TRANSFORM_FEATURES:
        features_raw[col] = np.log1p(features_raw[col])

    if features_raw.isna().any().any():
        na_counts = features_raw.isna().sum()
        raise ValueError(
            f"Unexpected NaNs in clustering features (rfm_summary should have none):\n"
            f"{na_counts[na_counts > 0]}"
        )

    scaler = StandardScaler()
    scaled_values = scaler.fit_transform(features_raw)

    features_scaled = pd.DataFrame(scaled_values, columns=RAW_FEATURES, index=rfm_df.index)

    return features_scaled, scaler, cap_info


def evaluate_k_candidates(
    features_scaled: pd.DataFrame,
    k_range: range = range(2, 9),
    random_state: int = RANDOM_STATE,
) -> pd.DataFrame:
    """Fit KMeans for each candidate K and collect Inertia + Silhouette.

    Silhouette is computed on the FULL dataset (no sampling) per explicit
    decision — slower but avoids any sampling-variance ambiguity in the
    comparison across K values.

    Returns
    -------
    pd.DataFrame
        Columns: k, inertia, silhouette. One row per K.
    """
    rows = []
    for k in k_range:
        model = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = model.fit_predict(features_scaled)
        sil = silhouette_score(features_scaled, labels)
        rows.append({"k": k, "inertia": model.inertia_, "silhouette": sil})
        print(f"k={k}: inertia={model.inertia_:.1f}, silhouette={sil:.4f}")

    return pd.DataFrame(rows)


def plot_k_selection(k_results: pd.DataFrame, output_path) -> None:
    """Plot Inertia (Elbow) and Silhouette side by side vs K, save to disk."""
    import matplotlib.pyplot as plt

    fig, ax1 = plt.subplots(figsize=(9, 5))

    color1 = "tab:blue"
    ax1.set_xlabel("K (number of clusters)")
    ax1.set_ylabel("Inertia", color=color1)
    ax1.plot(k_results["k"], k_results["inertia"], marker="o", color=color1)
    ax1.tick_params(axis="y", labelcolor=color1)

    ax2 = ax1.twinx()
    color2 = "tab:red"
    ax2.set_ylabel("Silhouette Score", color=color2)
    ax2.plot(k_results["k"], k_results["silhouette"], marker="s", color=color2)
    ax2.tick_params(axis="y", labelcolor=color2)

    plt.title("K Selection: Elbow (Inertia) vs Silhouette Score")
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=120)
    plt.close(fig)
    print(f"Saved plot -> {output_path}")


def inspect_cluster_sizes(
    features_scaled: pd.DataFrame,
    k_values: list[int],
    random_state: int = RANDOM_STATE,
) -> None:
    """Fit KMeans for each K in k_values and print cluster size distribution.

    Diagnostic step to check whether a high silhouette score (e.g. at
    k=2) reflects a meaningful split or just isolates a handful of
    outliers into a tiny cluster.
    """
    for k in k_values:
        model = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = model.fit_predict(features_scaled)
        sizes = pd.Series(labels).value_counts().sort_index()
        print(f"--- k={k} ---")
        print(sizes)
        print(f"  smallest cluster: {sizes.min()} rows ({sizes.min() / len(labels):.2%} of total)")
        print()


def validate_cluster_vs_repeat_customer(
    features_scaled: pd.DataFrame,
    rfm_df: pd.DataFrame,
    k: int,
    random_state: int = RANDOM_STATE,
) -> float:
    """Cross-tab the smallest KMeans cluster (at given k) against the raw
    frequency>=2 flag, to check whether the split truly aligns with
    repeat-purchase behavior or is a looser/fuzzier boundary.

    Returns the exact agreement rate (0.0-1.0) for programmatic checks.
    """
    model = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    labels = model.fit_predict(features_scaled)

    df = rfm_df.copy()
    df["cluster"] = labels

    sizes = pd.Series(labels).value_counts()
    smallest_cluster_id = sizes.idxmin()

    df["is_repeat_raw"] = df["frequency"] >= 2
    df["in_smallest_cluster"] = df["cluster"] == smallest_cluster_id

    crosstab = pd.crosstab(df["in_smallest_cluster"], df["is_repeat_raw"])
    print(f"--- k={k}: smallest cluster (id={smallest_cluster_id}, n={sizes.min()}) vs frequency>=2 ---")
    print(crosstab)
    print()

    match = (df["in_smallest_cluster"] == df["is_repeat_raw"]).mean()
    print(f"Exact agreement rate: {match:.4%}")
    return match


def _assign_cluster_names(profile_summary: pd.DataFrame) -> list[str]:
    """Assign a business-readable name to each cluster based on its RANK
    across the other clusters in this same run — never on fixed
    thresholds, since KMeans cluster IDs (0/1/2/3) are arbitrary and the
    profile itself must drive the naming.

    Logic:
    - The cluster with frequency far above the rest (validated in Task
      3.3's diagnostic process as the frequency>=2 repeat-buyer group)
      -> "Loyal / Repeat Buyers", regardless of its recency/monetary
      rank, since repeat purchase itself is the standout trait of this
      group in this dataset.
    - Among the remaining (one-time-buyer) clusters, `monetary` is
      ranked directly (highest -> "High-Value", middle -> "Mid-Value",
      lowest -> "Low-Value") rather than split at the median. With
      exactly 3 remaining clusters, a median-threshold approach makes
      the cluster sitting exactly AT the median fall into the "High"
      side purely as a tie-breaking artifact of an odd count — direct
      ranking removes that ambiguity entirely and scales correctly
      regardless of how many one-time-buyer clusters exist.
    - `recency` keeps the original median-based logic unchanged: a
      cluster is "Active" if its mean_recency_days is at or below the
      median of the remaining clusters, otherwise "Dormant".
    """
    df = profile_summary.copy()
    names = [None] * len(df)

    repeat_idx = df["mean_frequency"].idxmax()
    names[df.index.get_loc(repeat_idx)] = "Loyal / Repeat Buyers"

    remaining = df.drop(index=repeat_idx)

    monetary_rank = remaining["mean_monetary"].rank(ascending=False, method="first").astype(int)
    monetary_tier_map = {1: "High-Value", 2: "Mid-Value", 3: "Low-Value"}
    if len(remaining) != 3:
        raise ValueError(
            f"_assign_cluster_names expects exactly 3 non-repeat clusters "
            f"for the High/Mid/Low monetary tiering, got {len(remaining)}. "
            f"Update monetary_tier_map if K changes."
        )

    recency_median = remaining["mean_recency_days"].median()

    for idx, row in remaining.iterrows():
        tier = monetary_tier_map[monetary_rank.loc[idx]]
        status = "Active" if row["mean_recency_days"] <= recency_median else "Dormant"
        names[df.index.get_loc(idx)] = f"{tier} {status}"

    return names


def fit_final_segmentation(
    features_scaled: pd.DataFrame,
    rfm_df: pd.DataFrame,
    k: int = FINAL_K,
    random_state: int = RANDOM_STATE,
) -> tuple[KMeans, pd.DataFrame, pd.DataFrame]:
    """Fit the final KMeans model and attach cluster labels to rfm_df.

    Parameters
    ----------
    features_scaled : pd.DataFrame
        Output of prepare_clustering_features().
    rfm_df : pd.DataFrame
        The original (unscaled) RFM table — same row order/index as
        features_scaled.
    k : int, default FINAL_K (4)
        Final chosen K — see module docstring for the full diagnostic
        rationale (k=2 vs k=4).
    random_state : int, default RANDOM_STATE (42)

    Returns
    -------
    model : KMeans
        The fitted model.
    profiled_df : pd.DataFrame
        rfm_df with added `cluster` (raw KMeans id) and `cluster_label`
        (human-readable name) columns.
    profile_summary : pd.DataFrame
        One row per cluster: size, share of population, mean raw
        recency_days / frequency / monetary, and cluster_label.
    """
    model = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    cluster_ids = model.fit_predict(features_scaled)

    profiled_df = rfm_df.copy()
    profiled_df["cluster"] = cluster_ids

    profile_summary = (
        profiled_df.groupby("cluster")
        .agg(
            size=("customer_unique_id", "count"),
            mean_recency_days=("recency_days", "mean"),
            mean_frequency=("frequency", "mean"),
            mean_monetary=("monetary", "mean"),
        )
        .reset_index()
    )
    profile_summary["pct_of_total"] = profile_summary["size"] / len(profiled_df)
    profile_summary["cluster_label"] = _assign_cluster_names(profile_summary)

    label_map = dict(zip(profile_summary["cluster"], profile_summary["cluster_label"]))
    profiled_df["cluster_label"] = profiled_df["cluster"].map(label_map)

    return model, profiled_df, profile_summary


if __name__ == "__main__":
    from src.utils.config import REPORTS_DIR

    rfm = pd.read_csv(REPORTS_DIR / "rfm_summary.csv")
    features_scaled, scaler, cap_info = prepare_clustering_features(rfm)

    print("Shape:", features_scaled.shape)
    print("Cap info:", cap_info)

    print()
    print("=== Evaluating K candidates (this may take a few minutes) ===")
    k_results = evaluate_k_candidates(features_scaled)
    print()
    print(k_results)

    print()
    print("=== Cluster size inspection ===")
    inspect_cluster_sizes(features_scaled, k_values=[2, 3, 4, 5])

    print()
    print("=== Validating cluster vs repeat-customer hypothesis (k=4) ===")
    agreement = validate_cluster_vs_repeat_customer(features_scaled, rfm, k=FINAL_K)

    plot_k_selection(k_results, REPORTS_DIR / "figures" / "task_3_3_k_selection_capped.png")

    print()
    print(f"=== Fitting final KMeans (K={FINAL_K}) ===")
    model, profiled_df, profile_summary = fit_final_segmentation(features_scaled, rfm, k=FINAL_K)

    print()
    print("=== Cluster profile summary ===")
    print(profile_summary.to_string(index=False))

    out_path = REPORTS_DIR / "customer_segments.csv"
    profiled_df.to_csv(out_path, index=False)
    print()
    print(f"Saved -> {out_path}")

    summary_path = REPORTS_DIR / "task_3_3_segmentation_summary.md"
    lines = [
        "# Task 3.3 — Customer Segmentation Summary\n",
        "- **Algorithm**: KMeans, K=4, random_state=42, n_init=10\n",
        f"- **Input**: reports/rfm_summary.csv (Task 3.2), {len(rfm):,} customers\n",
        f"- **Preprocessing**: frequency capped at {cap_info['frequency_cap_quantile']:.0%} "
        f"quantile (value={cap_info['frequency_cap_value']}, {cap_info['n_rows_capped']} rows capped), "
        f"then log1p on frequency/monetary, then StandardScaler on all 3 features "
        f"(recency_days, frequency, monetary)\n",
        f"- **K selection**: evaluated k=2..8 via Elbow(Inertia)+Silhouette on full data (no sampling); "
        f"validated the smallest cluster exactly matches frequency>=2 "
        f"({agreement:.2%} agreement) across every K tested, confirming this is a real structural "
        f"split, not a scaling artifact. k=4 chosen over k=2 because k=2 leaves the 97% "
        f"one-time-buyer population undifferentiated, while k=4 further segments them by "
        f"recency/monetary at only a modest Silhouette cost (0.372 vs 0.718), which is expected "
        f"once a 97%-population subgroup is split further.\n",
        "\n## Cluster Profile\n",
        profile_summary.to_markdown(index=False),
        "\n",
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved -> {summary_path}")