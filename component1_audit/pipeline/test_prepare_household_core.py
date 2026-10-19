"""Unit checks for the definitions implemented in prepare_household_core."""

import unittest
import tempfile
from pathlib import Path

import pandas as pd

from prepare_household_core import (
    build_fies_item_extract,
    build_d1_source_candidates,
    build_d3_person_items,
    build_household_core,
    build_proxy_reference,
    read_required,
)


class HouseholdCoreTests(unittest.TestCase):
    def setUp(self):
        self.master = pd.DataFrame({"hhcode": pd.Series(["h1", "h2", "h3"], dtype="string")})
        self.roster = pd.DataFrame({
            "hhcode": pd.Series(["h1", "h1", "h2"], dtype="string"),
            "pid": pd.Series(["p1", "p2", "p1"], dtype="string"),
        })

    def test_unique_person_aggregation_preserves_master_rows(self):
        out = build_household_core(self.master, self.roster)
        self.assertEqual(out.hhcode.tolist(), ["h1", "h2", "h3"])
        self.assertEqual(out.roster_member_count.iloc[:2].tolist(), [2, 1])
        self.assertTrue(pd.isna(out.roster_member_count.iloc[2]))

    def test_duplicate_roster_key_fails(self):
        duplicated = pd.concat([self.roster, self.roster.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_household_core(self.master, duplicated)

    def test_duplicate_or_missing_master_key_fails(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            build_household_core(pd.DataFrame({"hhcode": ["h1", "h1"]}), self.roster)
        with self.assertRaisesRegex(ValueError, "nonmissing"):
            build_household_core(pd.DataFrame({"hhcode": [None]}), self.roster)

    def test_roster_outside_master_fails(self):
        extra = pd.DataFrame({"hhcode": ["outside"], "pid": ["p1"]})
        with self.assertRaisesRegex(ValueError, "absent from the declared master"):
            build_household_core(self.master, pd.concat([self.roster, extra], ignore_index=True))

    def test_deterministic_output(self):
        first = build_household_core(self.master, self.roster)
        second = build_household_core(self.master.copy(), self.roster.copy())
        pd.testing.assert_frame_equal(first, second)

    def test_required_columns_fail_clearly(self):
        with self.assertRaisesRegex(FileNotFoundError, "Required BRIGHT input is missing"):
            read_required(Path("not-read.csv"), {"hhcode"})
        # The missing-file branch is intentionally checked separately from schema validation.
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "present.csv"
            pd.DataFrame({"wrong": [1]}).to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "missing required columns"):
                read_required(path, {"hhcode"})

    def test_fies_forms_remain_separate_and_preserve_codes(self):
        l1 = pd.DataFrame({"hhcode": ["h1", "h2"], "l1_answered": [1, 0],
                           **{f"l1_{i:02d}": [1, None] for i in range(1, 9)}})
        l2 = pd.DataFrame({"hhcode": ["h1", "h2"], "l2_answered": [0, 1],
                           **{f"l2_{i:02d}": [2, 3] for i in range(1, 9)}})
        out = build_fies_item_extract(self.master, l1, l2)
        self.assertEqual(out.hhcode.tolist(), self.master.hhcode.tolist())
        self.assertEqual(out.loc[0, "l1_01"], 1)
        self.assertEqual(out.loc[0, "l2_01"], 2)
        self.assertEqual(out.loc[1, "l2_01"], 3)
        self.assertTrue(pd.isna(out.loc[1, "l1_01"]))
        self.assertNotIn("d2_fies_raw", out.columns)

    def test_proxy_isolated_and_keeps_source_values(self):
        context = pd.DataFrame({"hhcode": ["h1", "h2"], "pc_cons": [100.0, 200.0],
                                "label_high_vuln": [1, 0], "irrelevant": [5, 6]})
        out = build_proxy_reference(self.master, context)
        self.assertEqual(len(out), len(self.master))
        self.assertEqual(out.loc[0, "pc_cons_prepared_unvalidated"], 100.0)
        self.assertEqual(out.loc[0, "label_high_vuln_prepared_unvalidated"], 1)
        self.assertTrue(pd.isna(out.loc[2, "label_high_vuln_prepared_unvalidated"]))
        self.assertNotIn("irrelevant", out.columns)

    def test_d1_raw_items_and_household_income_repetition(self):
        from prepare_household_core import ASSET_ITEMS

        housing = pd.DataFrame({"hhcode": self.master.hhcode,
                                "c1_04": ["1", "2", "3"], "c1_05": ["4", "5", "6"],
                                "c1_06": ["7", "1", "2"], "c1_07": ["999", "4", "1"],
                                "c1_08": ["999", "14", "2"]})
        assets = pd.DataFrame({"hhcode": self.master.hhcode,
                               **{item: ["0", "1", "2"] for item in ASSET_ITEMS}})
        h1 = pd.DataFrame({"hhcode": ["h1", "h1", "h2", "h3", "h3"],
                           "hhmember": ["p1", "p2", "p1", "p1", "p2"],
                           "h1_17": ["999", "999", None, "1000", "2000"]})
        out = build_d1_source_candidates(self.master, housing, assets, h1)
        self.assertEqual(len(out), 3)
        self.assertTrue(out.hhcode.is_unique)
        self.assertEqual(out.loc[0, "c1_05"], "4")
        self.assertEqual(out.loc[0, "c1_06"], "7")
        self.assertEqual(out.loc[0, "h1_17_raw_household_value"], "999")
        self.assertEqual(out.loc[0, "h1_17_consistency_status"], "consistent_repeated_value")
        self.assertEqual(out.loc[0, "h1_17_nonmissing_record_count"], 2)
        self.assertEqual(out.loc[2, "h1_17_consistency_status"], "conflicting_values")
        self.assertTrue(pd.isna(out.loc[2, "h1_17_raw_household_value"]))
        self.assertEqual(out.loc[2, "h1_17_distinct_nonmissing_value_count"], 2)
        self.assertEqual(out.loc[1, "h1_17_consistency_status"], "no_nonmissing_record_value")

    def test_d3_person_join_preserves_roster_and_skips(self):
        roster = pd.DataFrame({"hhcode": ["h1", "h1", "h2"], "pid": ["p1", "p2", "p1"],
                               "b0_04_years": ["0", "20", "101"],
                               "b0_04_months": ["6", None, None]})
        b3 = pd.DataFrame({"hhcode": ["h1", "h2"], "pid": ["p1", "p1"],
                           "b3_01": ["1", "0"], "b3_02": ["2 3", None],
                           "b3_03": ["7", None]})
        out = build_d3_person_items(roster, b3)
        self.assertEqual(len(out), len(roster))
        self.assertEqual(out[["hhcode", "pid"]].values.tolist(), roster[["hhcode", "pid"]].values.tolist())
        self.assertEqual(out.b3_module_record_present.tolist(), [True, False, True])
        self.assertEqual(out.loc[0, "b3_01"], "1")
        self.assertEqual(out.loc[0, "b3_02"], "2 3")
        self.assertEqual(out.loc[0, "b3_03"], "7")
        self.assertTrue(pd.isna(out.loc[1, "b3_01"]))

    def test_d3_person_join_rejects_duplicate_and_unmatched_keys(self):
        roster = pd.DataFrame({"hhcode": ["h1"], "pid": ["p1"], "b0_04_years": ["20"], "b0_04_months": [None]})
        b3 = pd.DataFrame({"hhcode": ["h1"], "pid": ["p1"], "b3_01": ["1"], "b3_02": ["2"], "b3_03": ["1"]})
        duplicated = pd.concat([b3, b3], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "complete and unique"):
            build_d3_person_items(roster, duplicated)
        unmatched = b3.assign(hhcode="outside")
        with self.assertRaisesRegex(ValueError, "absent from the B0 roster"):
            build_d3_person_items(roster, unmatched)


if __name__ == "__main__":
    unittest.main()
