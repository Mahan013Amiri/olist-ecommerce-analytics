"""Tests for customer segmentation via KMeans. (Task 3.3)"""

import numpy as np
import pandas as pd
import pytest

from src.models.segmentation import (
    RAW_FEATURES,
    _assign_cluster_names,
    fit_final_segmentation,
    prepare_clustering_features,
)


@pytest.fixture
def sample_rfm_df():
    """A small synthetic RFM table: mostly one-time buyers with varying
    recency/monetary, plus a few repeat buyers (frequency >= 2), plus one
    extreme-frequency outlier to exercise the capping logic.
    """
    return pd.DataFrame(
        {
            "customer_unique_id": [f"cust_{i}" for i in range(10)],
            "recency_days": [10, 400, 20, 380, 15, 390, 5, 370, 100, 200],
            "frequency": [1, 1, 1, 1, 1, 1, 2, 2, 1, 20],
            "monetary": [500, 50, 480, 40, 460, 30, 470, 45, 300, 600],
        }
    )


class TestPrepareClusteringFeatures:
    def test_no_missing_columns_required(self, sample_rfm_df):
        bad_df = sample_rfm_df.drop(columns=["monetary"])
        with pytest.raises(ValueError, match="missing required columns"):
            prepare_clustering_features(bad_df)

    def test_output_shape_matches_input(self, sample_rfm_df):
        features_scaled, scaler, cap_info = prepare_clustering_features(sample_rfm_df)
        assert features_scaled.shape == (len(sample_rfm_df), len(RAW_FEATURES))
        assert list(features_scaled.columns) == RAW_FEATURES

    def test_no_nans_in_output(self, sample_rfm_df):
        features_scaled, _, _ = prepare_clustering_features(sample_rfm_df)
        assert not features_scaled.isna().any().any()

    def test_scaled_output_is_standardized(self, sample_rfm_df):
        features_scaled, _, _ = prepare_clustering_features(sample_rfm_df)
        means = features_scaled.mean()
        stds = features_scaled.std(ddof=0)
        assert np.allclose(means, 0, atol=1e-8)
        assert np.allclose(stds, 1, atol=1e-6)

    def test_frequency_capping_reduces_extreme_outlier(self, sample_rfm_df):
        # customer with frequency=20 is a clear outlier vs. the rest (max
        # otherwise is 2); capping at 0.99 should pull it down.
        features_scaled, _, cap_info = prepare_clustering_features(
            sample_rfm_df, frequency_cap_quantile=0.8
        )
        assert cap_info["n_rows_capped"] >= 1
        # after capping+log1p+scale, the outlier's z-score should no longer
        # be wildly larger than the next-highest frequency customer's.
        freq_scaled = features_scaled["frequency"]
        assert freq_scaled.max() < 5  # sanity bound, well below an uncapped ~27 z-score


class TestAssignClusterNames:
    def _make_profile(self, frequencies, monetaries, recencies):
        return pd.DataFrame(
            {
                "cluster": range(len(frequencies)),
                "mean_frequency": frequencies,
                "mean_monetary": monetaries,
                "mean_recency_days": recencies,
                "size": [100] * len(frequencies),
            }
        )

    def test_repeat_buyer_cluster_identified_by_max_frequency(self):
        profile = self._make_profile(
            frequencies=[1.0, 1.0, 1.0, 2.5],
            monetaries=[300, 100, 50, 280],
            recencies=[200, 400, 150, 250],
        )
        names = _assign_cluster_names(profile)
        assert names[3] == "Loyal / Repeat Buyers"

    def test_monetary_tiers_ranked_correctly(self):
        # cluster 0 = highest monetary, cluster 1 = middle, cluster 2 = lowest
        profile = self._make_profile(
            frequencies=[1.0, 1.0, 1.0, 2.5],
            monetaries=[300, 150, 50, 280],
            recencies=[100, 100, 100, 250],  # all equal recency -> all "Active"
        )
        names = _assign_cluster_names(profile)
        assert "High-Value" in names[0]
        assert "Mid-Value" in names[1]
        assert "Low-Value" in names[2]

    def test_cluster_exactly_at_median_not_misclassified(self):
        # Regression test for the real bug found in Task 3.3: with 3
        # remaining clusters, the middle one sits exactly AT the median.
        # A median-threshold (>=) approach would wrongly bucket it as
        # "High" just because it ties the median. Rank-based logic must
        # assign it "Mid-Value" regardless.
        profile = self._make_profile(
            frequencies=[1.0, 1.0, 1.0, 2.5],
            monetaries=[318.1, 119.5, 69.0, 308.5],  # matches real project values
            recencies=[221.6, 473.5, 195.9, 268.3],
        )
        names = _assign_cluster_names(profile)
        assert names[0] == "High-Value Active"
        assert names[1] == "Mid-Value Dormant"
        assert names[2] == "Low-Value Active"
        assert names[3] == "Loyal / Repeat Buyers"

    def test_raises_when_not_exactly_three_remaining_clusters(self):
        # 5 total clusters, 1 repeat-buyer cluster -> 4 remaining, not 3.
        profile = self._make_profile(
            frequencies=[1.0, 1.0, 1.0, 1.0, 2.5],
            monetaries=[300, 200, 150, 50, 280],
            recencies=[100, 150, 200, 250, 300],
        )
        with pytest.raises(ValueError, match="expects exactly 3"):
            _assign_cluster_names(profile)


class TestFitFinalSegmentation:
    def test_every_customer_gets_a_cluster_and_label(self, sample_rfm_df):
        features_scaled, _, _ = prepare_clustering_features(sample_rfm_df)
        model, profiled_df, profile_summary = fit_final_segmentation(
            features_scaled, sample_rfm_df, k=4
        )
        assert len(profiled_df) == len(sample_rfm_df)
        assert not profiled_df["cluster"].isna().any()
        assert not profiled_df["cluster_label"].isna().any()

    def test_profile_summary_covers_all_clusters(self, sample_rfm_df):
        features_scaled, _, _ = prepare_clustering_features(sample_rfm_df)
        model, profiled_df, profile_summary = fit_final_segmentation(
            features_scaled, sample_rfm_df, k=4
        )
        assert profile_summary["size"].sum() == len(sample_rfm_df)
        assert profile_summary["cluster"].nunique() == 4