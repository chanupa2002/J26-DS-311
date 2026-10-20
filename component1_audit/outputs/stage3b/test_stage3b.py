"""Research output - not an eligibility determination.
Synthetic edge-case tests for Stage 3b transformations.
"""
import sys
import unittest
from pathlib import Path
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_stage3b import binary_answer, count_valid_o1, health_aggregate, validate_unique_household_key

class Stage3bTests(unittest.TestCase):
    def test_bank_account_binary_and_unknown(self):
        self.assertEqual(binary_answer('0'),0)
        self.assertEqual(binary_answer('1'),1)
        self.assertIsNone(binary_answer(None))
        self.assertIsNone(binary_answer('2'))
        self.assertIsNone(binary_answer('997'))

    def test_has_debt_task_mapping_and_unknown(self):
        self.assertEqual(binary_answer('1'),1)
        self.assertEqual(binary_answer('0'),0)
        self.assertIsNone(binary_answer(''))
        self.assertIsNone(binary_answer('8'))

    def test_o1_raw_items_count_only_valid_values(self):
        self.assertEqual(count_valid_o1(['1','2','3',None,'0','997']),3)

    def test_health_aggregation_missing_member_and_no_valid(self):
        spine=pd.DataFrame({'hhcode':['A','B']})
        roster=pd.DataFrame({'hhcode':['A','A','B'],'pid':['1','2','1']})
        b3=pd.DataFrame({'hhcode':['A','A','B'],'pid':['1','2','1'],'b3_01':['1',None,'2'],'b3_03':[None,1,1],'b3_04':[1,1,1]})
        out=health_aggregate(spine,roster,b3).set_index('hhcode')
        self.assertEqual(out.loc['A','n_members_b3_valid'],1)
        self.assertEqual(out.loc['A','n_chronic'],1)
        self.assertEqual(out.loc['A','share_chronic'],1.0)
        self.assertEqual(out.loc['A','health_status'],'partial')
        self.assertEqual(out.loc['B','n_members_b3_valid'],0)
        self.assertTrue(pd.isna(out.loc['B','share_chronic']))
        self.assertEqual(out.loc['B','health_status'],'missing')

    def test_health_aggregation_valid_and_no_derived_followups(self):
        spine=pd.DataFrame({'hhcode':['C']})
        roster=pd.DataFrame({'hhcode':['C','C'],'pid':['1','2']})
        b3=pd.DataFrame({'hhcode':['C','C'],'pid':['1','2'],'b3_01':['1','0'],'b3_03':['arbitrary','arbitrary'],'b3_04':['x','y']})
        out=health_aggregate(spine,roster,b3).iloc[0]
        self.assertEqual(out.n_members_b3_valid,2)
        self.assertEqual(out.n_chronic,1)
        self.assertEqual(out.share_chronic,.5)
        self.assertEqual(out.health_status,'valid')

    def test_household_outside_spine_does_not_expand_spine(self):
        spine=pd.DataFrame({'hhcode':['A']})
        roster=pd.DataFrame({'hhcode':['A'],'pid':['1']})
        b3=pd.DataFrame({'hhcode':['Z'],'pid':['9'],'b3_01':['1']})
        out=health_aggregate(spine,roster,b3)
        self.assertEqual(out.hhcode.tolist(),['A'])
        self.assertEqual(out.n_members_b3_valid.tolist(),[0])

    def test_duplicate_household_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_unique_household_key(pd.DataFrame({'hhcode':['A','A']}),'synthetic')

    def test_duplicate_member_key_rejected(self):
        spine=pd.DataFrame({'hhcode':['A']})
        roster=pd.DataFrame({'hhcode':['A'],'pid':['1']})
        b3=pd.DataFrame({'hhcode':['A','A'],'pid':['1','1'],'b3_01':['0','1']})
        with self.assertRaises(ValueError): health_aggregate(spine,roster,b3)

if __name__=='__main__': unittest.main()
