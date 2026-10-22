"""Synthetic tests for fixed Stage 6 metric and masking helpers."""
import numpy as np
import pandas as pd

from run_stage6 import (
    counting_index, fix_pca_sign, mask_known, safe_corr, suppressed,
    top_k_jaccard, weighted_cfg,
)
import bn_v0_1 as bn


def test_rank_metrics_have_known_answers():
    a = pd.Series([1, 2, 3, 4])
    assert safe_corr(a, a, "spearman") == 1.0
    assert safe_corr(a, a.iloc[::-1].reset_index(drop=True), "spearman") == -1.0
    assert safe_corr(a, a, "kendall") == 1.0
    assert safe_corr(a, a.iloc[::-1].reset_index(drop=True), "kendall") == -1.0


def test_top_k_jaccard_known_answer():
    a = [4, 3, 2, 1]
    b = [3, 4, 1, 2]
    assert top_k_jaccard(a, b, .5) == 1.0
    assert top_k_jaccard(a, [1, 4, 3, 2], .5) == 1/3


def test_pca_sign_follows_additive_baseline():
    additive = np.array([0.1, 0.3, 0.5, 0.7])
    oriented, original_corr = fix_pca_sign(-additive, additive)
    assert original_corr < 0
    assert safe_corr(oriented, additive) > 0


def test_counting_index_skips_unknown_indicators_and_rescales_domains():
    mu = pd.DataFrame({"a1": [1.0, np.nan], "a2": [np.nan, np.nan], "b1": [0.0, 1.0]})
    score, n = counting_index(mu, {"domain_a": ["a1", "a2"], "domain_b": ["b1"]}, .5)
    assert score.iloc[0] == .5
    assert score.iloc[1] == 1.0
    assert n.tolist() == [2, 1]


def test_masking_hits_requested_fraction_and_preserves_unknowns():
    frame = pd.DataFrame({"a": [1.0, np.nan, 0.0], "b": [.5, .2, np.nan]})
    masked, n_masked, n_known = mask_known(frame, .5, np.random.default_rng(7))
    assert n_known == 4
    assert n_masked == 2
    assert np.isnan(masked.iloc[1, 0]) and np.isnan(masked.iloc[2, 1])
    assert masked.isna().sum().sum() == frame.isna().sum().sum() + n_masked


def test_min_cell_suppression_boundary():
    assert suppressed(9)
    assert not suppressed(10)


def test_seed_reproducibility_for_masking_and_weight_draws():
    frame = pd.DataFrame(np.arange(40, dtype=float).reshape(10, 4))
    first, _, _ = mask_known(frame, .2, np.random.default_rng(99))
    second, _, _ = mask_known(frame, .2, np.random.default_rng(99))
    pd.testing.assert_frame_equal(first, second)
    cfg = bn.config_v02_interim()
    a = weighted_cfg(cfg, np.random.default_rng(99))
    b = weighted_cfg(cfg, np.random.default_rng(99))
    assert [node.weights for node in a.nodes] == [node.weights for node in b.nodes]
