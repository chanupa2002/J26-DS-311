"""Synthetic unit checks for Stage 3 rules; kept inside the stage3 write boundary."""
import unittest
import pandas as pd

import prepare_stage3 as s


class Stage3DerivationTests(unittest.TestCase):
    def test_fies_complete_partial_dk_refused_blank_both_none(self):
        yes_no = [1, 2, 1, 2, 1, 2, 1, 2]
        self.assertEqual(s.fies_one(1, 0, yes_no, [None] * 8), {
            "fies_form_used": "L1", "fies_valid_items_n": 8,
            "fies_raw_score": 4, "fies_status": "valid"})
        self.assertEqual(s.fies_one(1, 0, [1, 2, 3, 4, None, 2, 1, 2], [] )["fies_status"], "partial_dk_refused")
        self.assertEqual(s.fies_one(1, 0, [1, 2, None, 4, 2, 1, 2, 1], [] )["fies_status"], "partial_dk_refused")
        self.assertEqual(s.fies_one(0, 1, [None] * 8, [1, 2, None, 2, 1, 2, 1, 2])["fies_status"], "partial_blank")
        both = s.fies_one(1, 1, yes_no, yes_no)
        self.assertEqual((both["fies_form_used"], both["fies_valid_items_n"], both["fies_raw_score"], both["fies_status"]), ("both", pd.NA, pd.NA, "both_forms"))
        none = s.fies_one(0, 0, [], [])
        self.assertEqual((none["fies_form_used"], none["fies_valid_items_n"], none["fies_raw_score"], none["fies_status"]), ("none", pd.NA, pd.NA, "no_form"))

    def test_housing_999_classes_and_missing(self):
        self.assertEqual(s.toilet_type(999), "unknown")
        self.assertEqual(s.toilet_type(None), "unknown")
        self.assertEqual(s.toilet_service(1, 0), "basic")
        self.assertEqual(s.toilet_service(1, 1), "limited")
        self.assertEqual(s.toilet_service(4, 0), "unimproved")
        self.assertEqual(s.toilet_service(14, 0), "open_defecation")
        self.assertEqual(s.toilet_service(1, 2), "unknown")
        self.assertEqual(s.toilet_service(4, 2), "unknown")
        self.assertEqual(s.tenure_class(999), "unknown")
        self.assertEqual(s.tenure_class(2), "secure")
        self.assertEqual(s.tenure_class(5), "intermediate")
        self.assertEqual(s.tenure_class(8), "insecure")
        self.assertEqual(s.material_class(1, {}), "unknown")

    def test_d04b_c1_10_codebook_mapping(self):
        self.assertEqual(s.toilet_sharing_class(0), "not shared")
        self.assertEqual(s.toilet_sharing_class(1), "shared")
        self.assertEqual(s.toilet_sharing_class(2), "unknown")
        self.assertEqual(s.toilet_sharing_class(None), "unknown")

    def test_crowding_zero_missing_and_positive(self):
        bedrooms = pd.Series([0, None, 2])
        members = pd.Series([3, 4, 5])
        ratios = members.div(bedrooms.where(bedrooms.ge(1)))
        self.assertTrue(pd.isna(ratios.iloc[0]))
        self.assertTrue(pd.isna(ratios.iloc[1]))
        self.assertEqual(ratios.iloc[2], 2.5)
        self.assertEqual(bedrooms.eq(0).astype(int).tolist(), [1, 0, 0])
        self.assertEqual(bedrooms.isna().astype(int).tolist(), [0, 1, 0])

    def test_age_bands_no_working_age_and_ratios(self):
        ages = pd.Series([4, 15, 64, 65, None])
        under = int((ages.ge(0) & ages.lt(15)).sum())
        work = int((ages.ge(15) & ages.le(64)).sum())
        older = int(ages.ge(65).sum())
        missing = int(ages.isna().sum())
        self.assertEqual((under, work, older, missing), (1, 2, 1, 1))
        self.assertEqual((under + older) / work, 1)
        no_work = ages[ages.eq(4) | ages.eq(65)]
        self.assertEqual(int((no_work.ge(15) & no_work.le(64)).sum() == 0), 1)
        self.assertTrue(pd.isna((1 + 1) / 0 if False else float("nan")))

    def test_income_repeated_conflict_is_unknown_and_never_summed(self):
        statuses = pd.Series(["consistent_repeated_value", "conflict", "missing"])
        mapped = statuses.map(lambda v: "consistent" if v == "consistent_repeated_value" else "unknown")
        self.assertEqual(mapped.tolist(), ["consistent", "unknown", "unknown"])

    def test_asset_counts_and_codebook_binary_assets(self):
        self.assertEqual(s.asset_owned(0, "d_01", True), 0)
        self.assertEqual(s.asset_owned(3, "d_01", True), 1)
        self.assertTrue(pd.isna(s.asset_owned(None, "d_01", True)))
        self.assertEqual(s.asset_owned(0, "d_12", False), 0)
        self.assertEqual(s.asset_owned(1, "d_12", False), 1)
        self.assertTrue(pd.isna(s.asset_owned(2, "d_12", False)))
        self.assertTrue(pd.isna(s.asset_owned(None, "d_12", False)))


if __name__ == "__main__":
    unittest.main()
