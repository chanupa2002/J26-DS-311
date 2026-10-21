"""Unit tests for bn_v0_1 (synthetic data only). Run: python -m unittest -v"""
import unittest
import numpy as np
import pandas as pd

import bn_v0_1 as bn

LEAVES = ("housing", "economic", "food", "demographic")


def frame(rows):
    """rows: list of dicts leaf -> (low, med, high, n_used, n_total) or None (unobserved)."""
    recs = []
    for r in rows:
        rec = {"hhcode": f"H{len(recs)}"}
        for leaf in LEAVES:
            spec = r.get(leaf)
            if spec is None:
                rec.update({f"soft_{leaf}_low": np.nan, f"soft_{leaf}_medium": np.nan,
                            f"soft_{leaf}_high": np.nan,
                            f"dom_{leaf}_n_used": 0, f"dom_{leaf}_n_total": 2})
            else:
                lo, me, hi, nu, nt = spec
                rec.update({f"soft_{leaf}_low": lo, f"soft_{leaf}_medium": me,
                            f"soft_{leaf}_high": hi,
                            f"dom_{leaf}_n_used": nu, f"dom_{leaf}_n_total": nt})
        recs.append(rec)
    return pd.DataFrame(recs)


def all_leaves(spec):
    return {leaf: spec for leaf in LEAVES}


LOW = (1.0, 0.0, 0.0, 1, 1)
MED = (0.0, 1.0, 0.0, 1, 1)
HIGH = (0.0, 0.0, 1.0, 1, 1)
UNIFORM = (1 / 3, 1 / 3, 1 / 3, 1, 1)


class TestCPT(unittest.TestCase):
    def test_rows_sum_to_one(self):
        cpt = bn.build_cpt([3, 3, 3], [1, 1, 1], 0.15, 3)
        self.assertTrue(np.allclose(cpt.sum(axis=-1), 1.0))
        cpt5 = bn.build_cpt([3, 3], [1, 1], 0.15, 5)
        self.assertTrue(np.allclose(cpt5.sum(axis=-1), 1.0))

    def test_extremes(self):
        cpt = bn.build_cpt([3, 3, 3], [1, 1, 1], 0.15, 3)
        self.assertEqual(int(np.argmax(cpt[0, 0, 0])), 0)
        self.assertEqual(int(np.argmax(cpt[2, 2, 2])), 2)

    def test_monotone_in_parent(self):
        cpt = bn.build_cpt([3, 3], [1, 1], 0.15, 3)
        mids = bn.state_midpoints(3)
        ev = [float(cpt[s, 0] @ mids) for s in range(3)]
        self.assertTrue(ev[0] < ev[1] < ev[2])

    def test_symmetry(self):
        cpt = bn.build_cpt([3, 3], [1, 1], 0.15, 3)
        self.assertTrue(np.allclose(cpt[0, 0], cpt[2, 2][::-1]))

    def test_sigma_controls_spread(self):
        tight = bn.build_cpt([3], [1], 0.05, 3)
        loose = bn.build_cpt([3], [1], 0.30, 3)
        self.assertGreater(tight[0, 0], loose[0, 0])

    def test_bad_sigma_and_weights(self):
        with self.assertRaises(ValueError):
            bn.ranked_node_row(0.5, 0.0, 3)
        with self.assertRaises(ValueError):
            bn.build_cpt([3], [0.0], 0.15, 3)
        with self.assertRaises(ValueError):
            bn.build_cpt([3, 3], [1, -1], 0.15, 3)

    def test_cpt_table_readable(self):
        t = bn.cpt_table("adaptive_capacity")
        self.assertEqual(len(t), 3)
        self.assertIn("P(high)", t.columns)


class TestScoring(unittest.TestCase):
    def test_output_basics(self):
        out = bn.score(frame([all_leaves(MED)]))
        self.assertEqual(out["research_label"].iloc[0], bn.RESEARCH_LABEL)
        v = out[["bn_vulnerability_low", "bn_vulnerability_medium", "bn_vulnerability_high"]].iloc[0]
        self.assertAlmostEqual(float(v.sum()), 1.0, places=9)
        self.assertTrue(0 <= out["bn_uncertainty_entropy"].iloc[0] <= 1.0)
        self.assertEqual(out["hhcode"].iloc[0], "H0")

    def test_high_evidence_beats_low(self):
        out = bn.score(frame([all_leaves(LOW), all_leaves(HIGH)]))
        self.assertLess(out["bn_p_high"].iloc[0], out["bn_p_high"].iloc[1])
        self.assertLess(out["bn_expected_vulnerability"].iloc[0],
                        out["bn_expected_vulnerability"].iloc[1])

    def test_no_evidence_is_symmetric_and_max_uncertain_at_leaves(self):
        out = bn.score(frame([{}]))
        self.assertAlmostEqual(out["bn_vulnerability_low"].iloc[0],
                               out["bn_vulnerability_high"].iloc[0], places=9)
        self.assertEqual(int(out["bn_leaves_observed"].iloc[0]), 0)
        uniform = bn.score(frame([all_leaves(UNIFORM)]))
        self.assertAlmostEqual(out["bn_p_high"].iloc[0], uniform["bn_p_high"].iloc[0], places=9)

    def test_n_used_zero_equals_nan(self):
        a = bn.score(frame([{"housing": (0.0, 0.0, 1.0, 0, 6), "food": HIGH}]))
        b = bn.score(frame([{"food": HIGH}]))
        self.assertAlmostEqual(a["bn_p_high"].iloc[0], b["bn_p_high"].iloc[0], places=9)

    def test_partial_coverage_blends_toward_uniform(self):
        full = bn.score(frame([all_leaves((0.0, 0.0, 1.0, 2, 2))]))
        half = bn.score(frame([all_leaves((0.0, 0.0, 1.0, 1, 2))]))
        none = bn.score(frame([{}]))
        self.assertLess(half["bn_p_high"].iloc[0], full["bn_p_high"].iloc[0])
        self.assertGreater(half["bn_p_high"].iloc[0], none["bn_p_high"].iloc[0])

    def test_blend_none_ignores_coverage(self):
        cfg = bn.BNConfig(blend="none")
        a = bn.score(frame([all_leaves((0.0, 0.0, 1.0, 1, 6))]), cfg)
        b = bn.score(frame([all_leaves((0.0, 0.0, 1.0, 6, 6))]), cfg)
        self.assertAlmostEqual(a["bn_p_high"].iloc[0], b["bn_p_high"].iloc[0], places=9)
        # but an unobserved domain (n_used = 0) still contributes nothing
        c = bn.score(frame([{"food": HIGH}]), cfg)
        d = bn.score(frame([{"food": HIGH, "housing": (0.0, 0.0, 1.0, 0, 6)}]), cfg)
        self.assertAlmostEqual(c["bn_p_high"].iloc[0], d["bn_p_high"].iloc[0], places=9)

    def test_min_coverage_threshold(self):
        cfg = bn.BNConfig(blend="min_coverage", min_coverage=0.5)
        below = bn.score(frame([all_leaves((0.0, 0.0, 1.0, 2, 6))]), cfg)
        above = bn.score(frame([all_leaves((0.0, 0.0, 1.0, 4, 6))]), cfg)
        empty = bn.score(frame([{}]), cfg)
        self.assertAlmostEqual(below["bn_p_high"].iloc[0], empty["bn_p_high"].iloc[0], places=9)
        self.assertGreater(above["bn_p_high"].iloc[0], below["bn_p_high"].iloc[0])

    def test_batch_equals_single(self):
        rows = [all_leaves(LOW), all_leaves(HIGH), {"food": HIGH, "housing": LOW},
                {"economic": (0.0, 0.3, 0.7, 1, 2)}]
        batch = bn.score(frame(rows))
        for i, r in enumerate(rows):
            single = bn.score(frame([r]))
            self.assertAlmostEqual(batch["bn_p_high"].iloc[i], single["bn_p_high"].iloc[0], places=12)

    def test_weights_change_influence(self):
        row = {"housing": HIGH, "food": LOW, "demographic": LOW, "economic": MED}
        equal = bn.score(frame([row]))
        nodes = (bn.NodeSpec("sensitivity", ["housing", "food", "demographic"],
                             {"housing": 3.0, "food": 1.0, "demographic": 1.0}),
                 bn.NodeSpec("adaptive_capacity", ["economic"]),
                 bn.NodeSpec("vulnerability", ["sensitivity", "adaptive_capacity"]))
        heavy = bn.score(frame([row]), bn.BNConfig(nodes=nodes))
        self.assertGreater(heavy["bn_sensitivity_high"].iloc[0], equal["bn_sensitivity_high"].iloc[0])

    def test_more_domains_missing_raises_uncertainty(self):
        full = bn.score(frame([all_leaves(HIGH)]))
        partial = bn.score(frame([{"food": HIGH}]))
        self.assertGreater(partial["bn_uncertainty_entropy"].iloc[0],
                           full["bn_uncertainty_entropy"].iloc[0])

    def test_five_state_internal_nodes(self):
        out = bn.score(frame([all_leaves(HIGH)]), bn.BNConfig(n_states=5))
        cols = [c for c in out.columns if c.startswith("bn_vulnerability_")]
        self.assertEqual(len(cols), 5)
        self.assertAlmostEqual(float(out[cols].iloc[0].sum()), 1.0, places=9)
        self.assertTrue(0 <= out["bn_p_high"].iloc[0] <= 1)

    def test_empirical_prior_shifts_unobserved_domain(self):
        base = bn.score(frame([{}]))
        cfg = bn.BNConfig(priors={leaf: (0.1, 0.2, 0.7) for leaf in LEAVES})
        shifted = bn.score(frame([{}]), cfg)
        self.assertGreater(shifted["bn_p_high"].iloc[0], base["bn_p_high"].iloc[0])

    def test_adaptive_capacity_effect(self):
        row_low_cap = {"housing": LOW, "food": LOW, "demographic": LOW, "economic": HIGH}
        row_high_cap = {"housing": LOW, "food": LOW, "demographic": LOW, "economic": LOW}
        out = bn.score(frame([row_low_cap, row_high_cap]))
        self.assertGreater(out["bn_p_high"].iloc[0], out["bn_p_high"].iloc[1])


class TestGuards(unittest.TestCase):
    def test_refuses_proxy_columns(self):
        for bad in ("label_high_vuln", "pc_cons"):
            with self.assertRaises(ValueError):
                bn.BNConfig(leaves=(bad, "food")).validate()

    def test_proxy_columns_in_frame_are_ignored(self):
        df = frame([all_leaves(MED)])
        a = bn.score(df)
        df["label_high_vuln"] = 1
        df["pc_cons"] = 12345.0
        b = bn.score(df)
        self.assertAlmostEqual(a["bn_p_high"].iloc[0], b["bn_p_high"].iloc[0], places=12)

    def test_bad_soft_memberships(self):
        df = frame([all_leaves(MED)])
        df["soft_food_high"] = 0.5
        with self.assertRaises(ValueError):
            bn.score(df)

    def test_missing_columns(self):
        df = frame([all_leaves(MED)]).drop(columns=["soft_food_low"])
        with self.assertRaises(KeyError):
            bn.score(df)

    def test_bad_structure(self):
        with self.assertRaises(ValueError):
            bn.BNConfig(nodes=(bn.NodeSpec("vulnerability", ["nope"]),)).validate()
        with self.assertRaises(ValueError):
            bn.BNConfig(nodes=(bn.NodeSpec("sensitivity", ["food"]),)).validate()
        with self.assertRaises(ValueError):
            bn.BNConfig(sigma=0).validate()
        with self.assertRaises(ValueError):
            bn.BNConfig(blend="bogus").validate()

    def test_structure_v02_is_valid(self):
        leaves, nodes = bn.structure_v02()
        bn.BNConfig(leaves=leaves, nodes=nodes).validate()

    def test_rank_agreement(self):
        s = pd.Series([1, 2, 3, 4.0])
        self.assertAlmostEqual(bn.rank_agreement(s, s * 2), 1.0)


class TestInterimV02(unittest.TestCase):
    LEAVES2 = ("shelter_quality", "sanitation", "crowding_tenure", "food", "demographic",
               "health", "economic", "financial_resilience", "exposure")

    def frame2(self, spec_by_leaf):
        rec = {"hhcode": "X"}
        for leaf in self.LEAVES2:
            spec = spec_by_leaf.get(leaf)
            if spec is None:
                rec.update({f"soft_{leaf}_low": np.nan, f"soft_{leaf}_medium": np.nan,
                            f"soft_{leaf}_high": np.nan,
                            f"dom_{leaf}_n_used": 0, f"dom_{leaf}_n_total": 1})
            else:
                lo, me, hi, nu, nt = spec
                rec.update({f"soft_{leaf}_low": lo, f"soft_{leaf}_medium": me,
                            f"soft_{leaf}_high": hi,
                            f"dom_{leaf}_n_used": nu, f"dom_{leaf}_n_total": nt})
        return pd.DataFrame([rec])

    def test_valid_and_scores(self):
        cfg = bn.config_v02_interim()
        cfg.validate()
        hi = self.frame2({l: HIGH for l in self.LEAVES2})
        lo = self.frame2({l: LOW for l in self.LEAVES2})
        a, b = bn.score(lo, cfg), bn.score(hi, cfg)
        self.assertLess(a["bn_p_high"].iloc[0], b["bn_p_high"].iloc[0])
        self.assertIn("bn_living_conditions_high", b.columns)
        self.assertEqual(int(b["bn_leaves_total"].iloc[0]), 8)

    def test_housing_weight_is_about_one_domain(self):
        """Nested: three housing leaves all high move sensitivity about as much as one domain
        (slightly less, because they pass through an extra smoothing node). Flat: far more."""
        housing = {l: HIGH for l in ("shelter_quality", "sanitation", "crowding_tenure")}
        nested = bn.config_v02_interim()
        leaves, _ = bn.structure_v02_interim()
        flat = bn.BNConfig(leaves=leaves, nodes=(
            bn.NodeSpec("sensitivity", ["shelter_quality", "sanitation", "crowding_tenure",
                                        "food", "demographic", "health"]),
            bn.NodeSpec("adaptive_capacity", ["economic", "financial_resilience"]),
            bn.NodeSpec("vulnerability", ["sensitivity", "adaptive_capacity"])))
        h_n = bn.score(self.frame2(housing), nested)["bn_sensitivity_high"].iloc[0]
        f_n = bn.score(self.frame2({"food": HIGH}), nested)["bn_sensitivity_high"].iloc[0]
        h_f = bn.score(self.frame2(housing), flat)["bn_sensitivity_high"].iloc[0]
        f_f = bn.score(self.frame2({"food": HIGH}), flat)["bn_sensitivity_high"].iloc[0]
        self.assertLessEqual(h_n, f_n)
        self.assertGreater(h_n, 0.9 * f_n)
        self.assertGreater(h_f, 1.5 * f_f)

    def test_cpt_sizes(self):
        cpts = bn.build_cpts(bn.config_v02_interim())
        self.assertEqual(cpts["sensitivity"].shape, (3, 3, 3, 3, 3))
        self.assertEqual(cpts["adaptive_capacity"].shape, (3, 3, 3))

    def test_exposure_is_off_by_default_and_ignored(self):
        cfg = bn.config_v02_interim()
        self.assertNotIn("exposure", cfg.leaves)
        a = bn.score(self.frame2({"food": HIGH}), cfg)
        b = bn.score(self.frame2({"food": HIGH, "exposure": HIGH}), cfg)
        self.assertAlmostEqual(a["bn_p_high"].iloc[0], b["bn_p_high"].iloc[0], places=12)

    def test_exposure_sensitivity_run(self):
        cfg = bn.config_v02_interim(include_exposure=True)
        cfg.validate()
        lo = bn.score(self.frame2({"exposure": LOW}), cfg)
        hi = bn.score(self.frame2({"exposure": HIGH}), cfg)
        self.assertLess(lo["bn_p_high"].iloc[0], hi["bn_p_high"].iloc[0])
        self.assertIn("bn_exposure_group_high", hi.columns)

    def test_drop_leaf(self):
        cfg = bn.drop_leaf(bn.config_v02_interim(), "health")
        cfg.validate()
        self.assertNotIn("health", cfg.leaves)
        a = bn.score(self.frame2({"health": HIGH, "food": LOW}), cfg)
        b = bn.score(self.frame2({"food": LOW}), cfg)
        self.assertAlmostEqual(a["bn_p_high"].iloc[0], b["bn_p_high"].iloc[0], places=12)
        # dropping both economic leaves removes the adaptive_capacity node entirely
        cfg2 = bn.drop_leaf(bn.drop_leaf(bn.config_v02_interim(), "economic"), "financial_resilience")
        cfg2.validate()
        self.assertNotIn("adaptive_capacity", [n.name for n in cfg2.nodes])


if __name__ == "__main__":
    unittest.main()
