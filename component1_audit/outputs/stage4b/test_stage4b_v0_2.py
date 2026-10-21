"""Research output - not an eligibility determination. v0.2 fuzzy helper tests."""
import sys, unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_stage4b_v0_2 import domain_mean, domain_max, deprivation_binary

class Stage4bV02Tests(unittest.TestCase):
    def test_mean_uses_available_only_and_preserves_all_unknown(self):
        frame=pd.DataFrame({'a':[0.2,np.nan,np.nan],'b':[0.4,0.3,np.nan]})
        degree,n=domain_mean(frame,['a','b'])
        self.assertAlmostEqual(degree.iloc[0],0.3)
        self.assertAlmostEqual(degree.iloc[1],0.3)
        self.assertTrue(np.isnan(degree.iloc[2]))
        self.assertEqual(n.tolist(),[2,1,0])

    def test_max_keeps_unknowns_unknown(self):
        degree,n=domain_max(pd.DataFrame({'a':[.2,np.nan],'b':[.8,np.nan]}),['a','b'])
        self.assertEqual(degree.iloc[0],.8)
        self.assertTrue(np.isnan(degree.iloc[1]))
        self.assertEqual(n.tolist(),[2,0])

    def test_approved_binary_directions_and_invalids(self):
        bank=deprivation_binary([0,1,None,2],0)
        debt=deprivation_binary([0,1,None,2],1)
        self.assertEqual(bank.iloc[:2].tolist(),[1.0,0.0])
        self.assertEqual(debt.iloc[:2].tolist(),[0.0,1.0])
        self.assertTrue(np.isnan(bank.iloc[2:]).all())
        self.assertTrue(np.isnan(debt.iloc[2:]).all())

if __name__=='__main__': unittest.main()
