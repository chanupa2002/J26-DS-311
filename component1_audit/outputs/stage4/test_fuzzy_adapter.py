"""Research output - not an eligibility determination. Adapter unit tests."""
import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fuzzy_adapter import adapt


class AdapterTests(unittest.TestCase):
    def sample(self):
        return pd.DataFrame({
            "hhcode": ["a", "b"], "fies_raw_score": [3, np.nan],
            "persons_per_bedroom": [2.5, np.nan], "dependency_ratio": [1.0, np.nan],
            "no_working_age_member": [0, 1], "h1_17_raw_household_value": [100, 200],
            "h1_17_consistency_status": ["consistent_repeated_value", "conflict"],
            "asset_types_owned_n": [4, 2], "asset_items_valid_n": [13, 8],
            "tenure_class": ["secure", "unknown"], "toilet_service_class": ["basic", "unknown"],
            "c1_04_durability_class": ["unknown", "durable"],
            "c1_05_durability_class": ["non_durable", "unknown"],
            "c1_06_durability_class": ["unknown", "unknown"],
            "d_12_owned": [np.nan, 0], "d_13_owned": [1, np.nan],
            "d_14_owned": [np.nan, np.nan], "d_15_owned": [0, 1], "d_16_owned": [np.nan, 1],
        })

    def test_maps_contract_fields_without_recalculating(self):
        out, coverage = adapt(self.sample())
        self.assertEqual(list(out.columns), ["hhcode", "fies_raw_score", "persons_per_bedroom", "dependency_ratio",
            "no_working_age_member", "income_value", "asset_types_owned_n", "asset_items_valid_n", "tenure_class",
            "toilet_service_class", "wall_durability", "floor_durability", "roof_durability"])
        self.assertEqual(out.loc[0, "income_value"], 100)
        self.assertTrue(np.isnan(out.loc[1, "income_value"]))
        self.assertTrue(np.isnan(out.loc[0, "wall_durability"]))
        self.assertEqual(out.loc[1, "wall_durability"], "durable")
        self.assertTrue(np.isnan(out.loc[1, "tenure_class"]))
        self.assertEqual(out.loc[0, "toilet_service_class"], "basic")
        self.assertTrue(np.isnan(out.loc[1, "toilet_service_class"]))
        self.assertEqual(out.loc[0, "asset_types_owned_n"], 4)
        self.assertTrue({f"d_{i:02d}_owned" for i in range(12, 17)}.issubset(set(coverage.engine_input)))

    def test_missing_stage3_fields_stay_unknown_and_are_reported(self):
        out, coverage = adapt(pd.DataFrame({"hhcode": ["a"]}))
        self.assertTrue(out.drop(columns="hhcode").isna().all(axis=None))
        self.assertTrue((coverage.unknown_n == 1).all())

    def test_unrecognized_categories_stay_unknown(self):
        df = self.sample()
        df.loc[0, "tenure_class"] = "new_code"
        df.loc[0, "toilet_service_class"] = "unmapped"
        out, _ = adapt(df)
        self.assertTrue(pd.isna(out.loc[0, "tenure_class"]))
        self.assertTrue(pd.isna(out.loc[0, "toilet_service_class"]))

    def test_proxy_fields_are_rejected(self):
        df = self.sample()
        df["pc_cons"] = 1
        with self.assertRaises(ValueError):
            adapt(df)


if __name__ == "__main__":
    unittest.main()
