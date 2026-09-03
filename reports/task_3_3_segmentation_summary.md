# Task 3.3 — Customer Segmentation Summary

- **Algorithm**: KMeans, K=4, random_state=42, n_init=10

- **Input**: reports/rfm_summary.csv (Task 3.2), 93,358 customers

- **Preprocessing**: frequency capped at 99% quantile (value=2.0, 228 rows capped), then log1p on frequency/monetary, then StandardScaler on all 3 features (recency_days, frequency, monetary)

- **K selection**: evaluated k=2..8 via Elbow(Inertia)+Silhouette on full data (no sampling); validated the smallest cluster exactly matches frequency>=2 (100.00% agreement) across every K tested, confirming this is a real structural split, not a scaling artifact. k=4 chosen over k=2 because k=2 leaves the 97% one-time-buyer population undifferentiated, while k=4 further segments them by recency/monetary at only a modest Silhouette cost (0.372 vs 0.718), which is expected once a 97%-population subgroup is split further.


## Cluster Profile

|   cluster |   size |   mean_recency_days |   mean_frequency |   mean_monetary |   pct_of_total | cluster_label         |
|----------:|-------:|--------------------:|-----------------:|----------------:|---------------:|:----------------------|
|         0 |  27872 |             221.588 |          1       |        318.103  |      0.29855   | High-Value Active     |
|         1 |  27001 |             473.489 |          1       |        119.507  |      0.28922   | Mid-Value Dormant     |
|         2 |  35684 |             195.945 |          1       |         69.0113 |      0.382228  | Low-Value Active      |
|         3 |   2801 |             268.317 |          2.11389 |        308.528  |      0.0300028 | Loyal / Repeat Buyers |

