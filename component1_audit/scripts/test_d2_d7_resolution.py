"""Focused, aggregate-only regression checks for the D2-D7 resolution audit."""
from pathlib import Path
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "Data" / "processed" / "clean"
PREP = ROOT / "Data" / "processed" / "hh_indicators.csv"


def read(path, cols):
    return pd.read_csv(path, usecols=cols, low_memory=False,
                       dtype={"hhcode": "string", "pid": "string", "hhmember": "string"})


class ResolutionAuditChecks(unittest.TestCase):
    def test_d2_missing_and_fractional_score_diagnostics(self):
        d = read(PREP, ["hhcode", "d2_fies_raw"])
        self.assertTrue(d.hhcode.is_unique)
        self.assertEqual(int(d.d2_fies_raw.isna().sum()), 39)
        frac = d.d2_fies_raw.notna() & d.d2_fies_raw.mod(1).ne(0)
        self.assertEqual(int(frac.sum()), 3)
        self.assertEqual(d.loc[frac, "d2_fies_raw"].value_counts().sort_index().to_dict(),
                         {0.5: 1, 1.5: 1, 2.5: 1})

    def test_d7_status_missing_amounts_and_prepared_zero_are_key_aligned(self):
        n1 = read(CLEAN / "mod_n1_debt.csv", ["hhcode", "n1_0", *[f"n1_03_{i}" for i in list(range(1, 13)) + [999]]])
        prep = read(PREP, ["hhcode", "d7_total_debt"])
        self.assertTrue(n1.hhcode.is_unique)
        self.assertTrue(prep.hhcode.is_unique)
        self.assertEqual(set(n1.hhcode), set(prep.hhcode))
        x = n1.merge(prep, on="hhcode", validate="one_to_one")
        status = pd.to_numeric(x.n1_0, errors="coerce").eq(1)
        amounts = x[[f"n1_03_{i}" for i in list(range(1, 13)) + [999]]]
        self.assertEqual(int(status.sum()), 2947)
        self.assertEqual(int((status & amounts.isna().all(axis=1)).sum()), 11)
        self.assertEqual(int((status & ~amounts.gt(0).any(axis=1)).sum()), 12)
        self.assertEqual(int((status & x.d7_total_debt.eq(0)).sum()), 31)

    def test_d3_b3_coverage_and_d4_income_missingness(self):
        b0 = read(CLEAN / "mod_b0_roster_long.csv", ["hhcode", "pid"])
        b3 = read(CLEAN / "mod_b3_roster_long.csv", ["hhcode", "pid"])
        self.assertTrue(b0.drop_duplicates(["hhcode", "pid"]).shape[0] == len(b0))
        self.assertTrue(b3.drop_duplicates(["hhcode", "pid"]).shape[0] == len(b3))
        b3keys = b3.merge(b0, on=["hhcode", "pid"], how="left", indicator=True, validate="one_to_one")
        self.assertEqual(int(b3keys._merge.ne("both").sum()), 0)
        self.assertEqual(len(b0) - int(b0.merge(b3, on=["hhcode", "pid"], how="inner", validate="one_to_one").shape[0]), 854)

        h1 = read(CLEAN / "mod_h1_primary_employment_long.csv", ["hhcode", "hhmember", "h1_17"])
        hcount = h1.groupby("hhcode").size()
        self.assertEqual(int((hcount > 1).sum()), 6663)
        has_income = h1.dropna(subset=["h1_17"]).groupby("hhcode").h1_17.nunique()
        self.assertEqual(int((has_income == 1).sum()), 5328)
        self.assertEqual(int((~h1.hhcode.drop_duplicates().isin(has_income.index)).sum()), 1519)


if __name__ == "__main__":
    unittest.main(verbosity=2)
