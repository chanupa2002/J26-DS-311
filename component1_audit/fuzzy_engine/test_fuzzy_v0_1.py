import unittest
import numpy as np
import pandas as pd

import fuzzy_v0_1 as f


def base(**kw):
    row = dict(hhcode="A", fies_raw_score=np.nan, persons_per_bedroom=np.nan,
               dependency_ratio=np.nan, no_working_age_member=0, income_value=np.nan,
               asset_types_owned_n=np.nan, asset_items_valid_n=np.nan,
               tenure_class=None, toilet_service_class=None,
               wall_durability=None, floor_durability=None, roof_durability=None)
    row.update(kw)
    return pd.DataFrame([row])


def refs():
    ref_df = pd.DataFrame({
        "income_value": [10, 20, 30, 40, 50],
        "asset_types_owned_n": [1, 2, 3, 4, 5],
        "dependency_ratio": [0.2, 0.5, 1.0, 1.5, 2.0],
        "no_working_age_member": [0, 0, 0, 0, 0],
    })
    return f.fit_references(ref_df)


class TestRules(unittest.TestCase):
    def test_food_is_score_over_eight(self):
        mu = f.memberships(base(fies_raw_score=4), refs())
        self.assertAlmostEqual(mu.mu_food[0], 0.5)

    def test_unknown_stays_unknown_not_zero(self):
        mu = f.memberships(base(), refs())
        self.assertTrue(mu.isna().all(axis=None))

    def test_crowding_ramp_midpoint_three(self):
        for ppb, expect in [(2, 0.0), (3, 0.5), (4, 1.0), (6, 1.0)]:
            mu = f.memberships(base(persons_per_bedroom=ppb), refs())
            self.assertAlmostEqual(mu.mu_crowding[0], expect)

    def test_no_working_age_member_is_top_coded_not_dropped(self):
        mu = f.memberships(base(no_working_age_member=1), refs())
        self.assertEqual(mu.mu_dependency[0], 1.0)

    def test_income_lower_is_more_deprived(self):
        lo = f.memberships(base(income_value=10), refs()).mu_income[0]
        hi = f.memberships(base(income_value=50), refs()).mu_income[0]
        self.assertGreater(lo, hi)

    def test_frozen_reference_same_score_regardless_of_batch(self):
        r = refs()
        alone = f.memberships(base(income_value=30), r).mu_income[0]
        batch = pd.concat([base(income_value=30), base(income_value=999)], ignore_index=True)
        self.assertAlmostEqual(f.memberships(batch, r).mu_income[0], alone)

    def test_reference_json_roundtrip(self):
        r = f.Reference([1, 2, 3])
        r2 = f.Reference.from_json(r.to_json())
        self.assertEqual(r.cdf([2]).iloc[0], r2.cdf([2]).iloc[0])

    def test_ordinal_maps_and_unrecognised_is_unknown(self):
        mu = f.memberships(base(tenure_class="insecure", toilet_service_class="limited",
                                wall_durability="durable", roof_durability="weird"), refs())
        self.assertEqual(mu.mu_tenure[0], 1.0)
        self.assertAlmostEqual(mu.mu_toilet[0], 1 / 3)
        self.assertEqual(mu.mu_wall[0], 0.0)
        self.assertTrue(np.isnan(mu.mu_roof[0]))

    def test_domain_mean_uses_only_available_inputs(self):
        df = base(tenure_class="insecure", toilet_service_class="basic")
        res = f.score_households(df, refs())
        self.assertAlmostEqual(res.dom_housing[0], 0.5)
        self.assertEqual(res.dom_housing_n_used[0], 2)
        self.assertEqual(res.dom_housing_n_total[0], 6)

    def test_domain_all_unknown_is_nan(self):
        res = f.score_households(base(), refs())
        self.assertTrue(np.isnan(res.dom_food[0]))
        self.assertEqual(res.dom_food_n_used[0], 0)

    def test_soft_levels_sum_to_one(self):
        lv = f.soft_levels(pd.Series([0.0, 0.25, 0.5, 0.75, 1.0]))
        np.testing.assert_allclose(lv.sum(axis=1), 1.0)
        self.assertEqual(lv.loc[0, "low"], 1.0)
        self.assertEqual(lv.loc[4, "high"], 1.0)

    def test_output_is_labelled_research_output(self):
        res = f.score_households(base(), refs())
        self.assertIn("not an eligibility", res.attrs["label"])


if __name__ == "__main__":
    unittest.main()
