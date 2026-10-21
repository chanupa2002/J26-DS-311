from __future__ import annotations
import unittest
import csv
import io
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from .. import model_api as api
from app.main import app as shared_backend_app
import bn_v0_1
from fuzzy_v0_1 import soft_levels

class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=api.create_app(force_synthetic=True); cls.client=TestClient(cls.app)
    def test_all_json_routes_have_metadata_and_synthetic_mark(self):
        answers=[self.client.get(p) for p in ("/health","/model-info","/spec","/sensitivity","/summary","/households?limit=4","/households/1")]
        leaves={k:{"degree":.5,"coverage_fraction":1} for k in api.LEAVES}
        answers.append(self.client.post("/whatif",json={"leaves":leaves}))
        for r in answers:
            self.assertEqual(r.status_code,200,r.text); body=r.json()
            for key in ("research_label","model_version","spec_version","data_manifest_sha256","data_mode"): self.assertIn(key,body)
            self.assertEqual(body["research_label"],api.LABEL); self.assertEqual(body["data_mode"],"SYNTHETIC")
            self.assertEqual(r.headers["X-Research-Label"],api.LABEL)
    def test_candidate_page_uses_separate_frontend(self):
        r=self.client.get("/"); self.assertEqual(r.status_code,200); self.assertIn("candidate",r.text.lower()); self.assertIn(api.LABEL,r.text)
        self.assertEqual(self.client.get("/assets/app.js").status_code,200)
    def test_paging_privacy_and_row_identifier(self):
        r=self.client.get("/households",params={"province":"1","district":"1","limit":3})
        self.assertEqual(r.status_code,200); self.assertLessEqual(len(r.json()["items"]),3)
        self.assertNotIn("hhcode",str(r.json()).lower())
        self.assertIn("/households/{row_id}",[x.path for x in self.app.routes])
        self.assertNotIn("/households/{hhcode}",[x.path for x in self.app.routes])
        self.assertEqual(self.client.get("/households/99999").status_code,404)
    def test_aggregate_suppression(self):
        rows=[{"name":"below","households_n":9},{"name":"at","households_n":10}]
        self.assertEqual(api.suppress(rows),[rows[1]])
        for key in ("by_province","by_district"):
            self.assertTrue(all(x["households_n"]>=10 for x in self.client.get("/summary").json()["geography"][key]))
    def test_routes_are_registered_in_shared_backend(self):
        shared=TestClient(shared_backend_app)
        for path in ("/households","/summary","/sensitivity","/spec","/model-info","/health"):
            response=shared.get(path)
            self.assertEqual(response.status_code,200,path)
            self.assertIn("research_label",response.json())
            self.assertIn("data_manifest_sha256",response.json())
        contract=shared_backend_app.openapi()
        for path in ("/households","/households/{row_id}","/summary","/whatif","/sensitivity","/spec","/model-info"):
            self.assertIn(path,contract["paths"])
    def test_whatif_equals_direct_engine_and_preserves_unknown(self):
        vals={leaf:{"degree":(i+1)/10,"coverage_fraction":.65} for i,leaf in enumerate(api.LEAVES)}
        body=self.client.post("/whatif",json={"leaves":vals}).json(); row={}
        for leaf in api.LEAVES:
            m=soft_levels(pd.Series([vals[leaf]["degree"]])).iloc[0]
            for s in ("low","medium","high"): row[f"soft_{leaf}_{s}"]=m[s]
            row[f"dom_{leaf}_n_used"]=.65; row[f"dom_{leaf}_n_total"]=1
        direct=bn_v0_1.score(pd.DataFrame([row]),bn_v0_1.config_v02_interim()).iloc[0]
        self.assertAlmostEqual(body["expected_vulnerability"],direct.bn_expected_vulnerability,places=12)
        self.assertAlmostEqual(body["uncertainty_entropy"],direct.bn_uncertainty_entropy,places=12)
        self.assertIn("candidate_rank_among_baseline_plus_candidate",body)
        unknown={x:{"degree":"unobserved","coverage_fraction":0} for x in api.LEAVES}
        result=self.client.post("/whatif",json={"leaves":unknown}).json()
        self.assertAlmostEqual(result["node_posteriors"]["vulnerability"]["low"],result["node_posteriors"]["vulnerability"]["high"],places=12)
    def test_csv_bulk_upload_is_validated_paginated_and_kept_out_of_response_body(self):
        self.assertEqual(self.client.get("/whatif/template.csv").status_code,200)
        stream=io.StringIO(); writer=csv.writer(stream); writer.writerow(api.CSV_COLUMNS)
        valid=[]; invalid=[]
        for leaf in api.LEAVES:
            valid.extend(["" if leaf=="health" else "0.6", "" if leaf=="health" else "1.0"])
            invalid.extend(["1.5" if leaf=="shelter_quality" else "0.4", "1.0"])
        writer.writerow(valid); writer.writerow(invalid)
        upload=self.client.post("/whatif",content=stream.getvalue(),headers={"Content-Type":"text/csv"})
        self.assertEqual(upload.status_code,200,upload.text)
        receipt=upload.json(); self.assertEqual(receipt["submitted_rows"],2); self.assertEqual(receipt["scored_rows"],1); self.assertEqual(receipt["rejected_rows"],1)
        self.assertNotIn("items",receipt); self.assertNotIn("hhcode",str(receipt).lower())
        page=self.client.get(receipt["results_url"])
        self.assertEqual(page.status_code,200,page.text); result=page.json()
        self.assertEqual(result["total"],1); self.assertEqual(result["items"][0]["candidate_row_id"],2)
        self.assertEqual(result["items"][0]["domain_inputs"]["health"]["degree"],"unobserved")
        self.assertNotIn("hhcode",str(result).lower())

if __name__=="__main__": unittest.main()
