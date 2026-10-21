"""Research output - not an eligibility determination. Stage 4b helper tests."""
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_stage4b import (complete_fies_score, rank_biserial_l1_vs_l2,
    asset_valid_mask, economic_from_memberships, asset_share)

class Stage4bTests(unittest.TestCase):
    def test_complete_fies_score_requires_eight_valid_answers(self):
        self.assertEqual(complete_fies_score([1,2,1,2,1,2,1,2]),4)
        self.assertTrue(np.isnan(complete_fies_score([1,2,1,2,1,2,1,np.nan])))
        self.assertTrue(np.isnan(complete_fies_score([1,2,1,2,1,2,1,3])))

    def test_rank_biserial_direction_and_counts(self):
        u,r,n1,n2=rank_biserial_l1_vs_l2([5,6,7],[0,1,2])
        self.assertEqual((n1,n2),(3,3))
        self.assertEqual(u,9.0)
        self.assertEqual(r,1.0)

    def test_rank_biserial_empty_group(self):
        u,r,n1,n2=rank_biserial_l1_vs_l2([], [1,2])
        self.assertTrue(np.isnan(u)); self.assertTrue(np.isnan(r))
        self.assertEqual((n1,n2),(0,2))

    def test_asset_completeness_threshold_preserves_unknown(self):
        result=asset_valid_mask([18,17,None],18)
        self.assertEqual(result.tolist(),[True,False,False])

    def test_economic_domain_mean_uses_available_inputs_only(self):
        degree,n_used=economic_from_memberships([.2,np.nan,np.nan],[.4,.3,np.nan])
        self.assertAlmostEqual(degree.iloc[0],.3)
        self.assertAlmostEqual(degree.iloc[1],.3)
        self.assertTrue(np.isnan(degree.iloc[2]))
        self.assertEqual(n_used.tolist(),[2,1,0])

    def test_asset_share_requires_valid_positive_denominator(self):
        share=asset_share([1,0,2],[2,0,None])
        self.assertEqual(share.iloc[0],.5)
        self.assertTrue(np.isnan(share.iloc[1]))
        self.assertTrue(np.isnan(share.iloc[2]))

if __name__=='__main__': unittest.main()
