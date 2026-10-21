"""Research output - not an eligibility determination. Stage 5 adapter/helper tests."""
import sys, unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_stage5 as s5

class Stage5Tests(unittest.TestCase):
    def test_baseline_whitelist_excludes_legacy_housing_and_exposure(self):
        row={'hhcode':'H1','dom_housing':.4,'soft_housing_low':.2,'dom_exposure':.8,
             'soft_exposure_low':.1,'label_high_vuln':0}
        for leaf in s5.LEAVES:
            row.update({f'soft_{leaf}_{state}':1/3 for state in s5.STATES})
            row[f'dom_{leaf}_n_used']=1; row[f'dom_{leaf}_n_total']=1
        with self.assertRaises(ValueError): s5.make_network_input(pd.DataFrame([row]))
        row.pop('label_high_vuln')
        out=s5.make_network_input(pd.DataFrame([row]))
        self.assertNotIn('dom_housing',out)
        self.assertNotIn('soft_housing_low',out)
        self.assertNotIn('dom_exposure',out)
        self.assertNotIn('soft_exposure_low',out)
        self.assertEqual(set(s5.LEAVES),{c[len('soft_'):-len('_low')] for c in out if c.startswith('soft_') and c.endswith('_low')})

    def test_five_state_map_collapses_to_comparable_levels(self):
        row={'bn_vulnerability_very_low':.05,'bn_vulnerability_low':.2,'bn_vulnerability_medium':.4,
             'bn_vulnerability_high':.2,'bn_vulnerability_very_high':.15}
        self.assertEqual(s5.vulnerability_levels(pd.DataFrame([row])).iloc[0],'medium')

    def test_three_state_map_uses_most_probable_state(self):
        row={'bn_vulnerability_low':.1,'bn_vulnerability_medium':.2,'bn_vulnerability_high':.7}
        self.assertEqual(s5.vulnerability_levels(pd.DataFrame([row])).iloc[0],'high')

    def test_flat_structure_sensitivity_has_729_parent_configurations(self):
        cfg=s5.flat_config(s5.bn.config_v02_interim())
        self.assertEqual(len(s5.bn.cpt_table('sensitivity',cfg)),729)

if __name__=='__main__': unittest.main()
