"""Local-only API for saved Component 1 scores and BN what-if scoring."""
from __future__ import annotations
import hashlib, json, os, sys
import csv, io, time, uuid
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRoute
from starlette.routing import Mount
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / "component1_audit"
API_DIR = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend" / "component1_candidate"
STAGE5 = PROJECT / "outputs" / "stage5"
FUZZY = PROJECT / "outputs" / "stage4b" / "fuzzy_scores_v0_2.csv"
LABEL = "Research output - not an eligibility determination"
MODEL_VERSION = "bn_v0.1.0"
SPEC_VERSION = "component1-v0.2-interim"
LEAVES = ("shelter_quality","sanitation","crowding_tenure","food","demographic","health","economic","financial_resilience")
MAX_CSV_BYTES = 2_000_000
MAX_BATCH_ROWS = 1_000
BATCH_TTL_SECONDS = 30 * 60
BATCH_LIMIT = 5
CSV_COLUMNS = tuple(c for leaf in LEAVES for c in (f"{leaf}_degree", f"{leaf}_coverage_fraction"))
sys.path.insert(0,str(PROJECT/"bn_engine")); sys.path.insert(0,str(PROJECT/"fuzzy_engine"))
import bn_v0_1
from fuzzy_v0_1 import soft_levels

class Leaf(BaseModel):
    model_config=ConfigDict(extra="forbid")
    degree: Any
    coverage_fraction: float
class WhatIf(BaseModel):
    model_config=ConfigDict(extra="forbid")
    leaves: dict[str,Leaf]

def file_hash(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def suppress(rows: list[dict], threshold: int=10) -> list[dict]: return [r for r in rows if int(r.get("households_n",0))>=threshold]

def public_row(row: pd.Series) -> dict[str,Any]:
    keys=("row_id","province","district","percentile_rank","bn_expected_vulnerability","bn_p_high","bn_uncertainty_entropy",
          "bn_leaves_observed","bn_leaves_total","sensitivity_expected_min","sensitivity_expected_max","sensitivity_rank_min","sensitivity_rank_max")
    out={}
    for k in keys:
        v=row.get(k)
        out[k]=None if pd.isna(v) else int(v) if k in ("row_id","bn_leaves_observed","bn_leaves_total") else str(v) if k in ("province","district") else float(v)
    return out

class Data:
    def __init__(self, force_synthetic: bool=False):
        real=(STAGE5/"bn_scores_v0_2_interim.csv").is_file() and not force_synthetic and os.getenv("COMPONENT1_API_SYNTHETIC")!="1"
        self.mode="REAL" if real else "SYNTHETIC"
        self.directory=STAGE5 if real else API_DIR/"sample_data"/"synthetic_api"
        if not (self.directory/"bn_scores_v0_2_interim.csv").exists():
            from .synthetic_data import build
            build(self.directory)
        manifest=self.directory/"manifest.json"
        if not manifest.exists():
            from .synthetic_data import build
            build(self.directory)
        self.manifest_hash=file_hash(manifest)
        self.frame=pd.read_csv(self.directory/"bn_scores_v0_2_interim.csv",dtype={"hhcode":"string"})
        if {"label_high_vuln","pc_cons"}.intersection(self.frame.columns): raise ValueError("proxy/label columns cannot be API inputs")
        self.frame.insert(0,"row_id",np.arange(1,len(self.frame)+1))
        self.frame["percentile_rank"]=self.frame.bn_expected_vulnerability.rank(method="average",pct=True)*100
        self.frame["province"]=np.nan; self.frame["district"]=np.nan
        if self.mode=="SYNTHETIC":
            self.frame["province"]=((self.frame.row_id-1)%3+1).astype(str); self.frame["district"]=((self.frame.row_id-1)%2+1).astype(str)
        else:
            geo_path=ROOT/"Data"/"processed"/"clean"/"mod_a_household_identification.csv"
            if geo_path.exists() and "hhcode" in self.frame:
                geo=pd.read_csv(geo_path,usecols=["hhcode","a_01_province","a_02_district"],dtype={"hhcode":"string"})
                if geo.hhcode.duplicated().any(): raise ValueError("geography keys are not unique")
                joined=self.frame[["hhcode"]].merge(geo,on="hhcode",how="left",validate="one_to_one",sort=False)
                if len(joined)!=len(self.frame) or joined[["a_01_province","a_02_district"]].isna().any().any(): raise ValueError("geography join incomplete")
                self.frame["province"]=joined.a_01_province.astype("string"); self.frame["district"]=joined.a_02_district.astype("string")
        self.sensitivity_files=sorted((self.directory/"sensitivity").glob("*.csv"))
        vals=[self.frame.bn_expected_vulnerability.to_numpy()]; ranks=[self.frame.percentile_rank.to_numpy()]
        for p in self.sensitivity_files:
            s=pd.read_csv(p,dtype={"hhcode":"string"})
            if "bn_expected_vulnerability" not in s: continue
            if "hhcode" in s and "hhcode" in self.frame:
                if s.hhcode.duplicated().any(): raise ValueError(f"duplicate keys in {p.name}")
                j=self.frame[["hhcode"]].merge(s[["hhcode","bn_expected_vulnerability"]],on="hhcode",how="left",validate="one_to_one",sort=False)
                v=j.bn_expected_vulnerability.to_numpy(float)
                if np.isnan(v).any(): raise ValueError(f"incomplete sensitivity file {p.name}")
            else: v=s.bn_expected_vulnerability.to_numpy(float)
            if len(v)==len(self.frame): vals.append(v); ranks.append(pd.Series(v).rank(method="average",pct=True).to_numpy()*100)
        vm,rm=np.vstack(vals),np.vstack(ranks)
        self.frame["sensitivity_expected_min"]=np.nanmin(vm,axis=0); self.frame["sensitivity_expected_max"]=np.nanmax(vm,axis=0)
        self.frame["sensitivity_rank_min"]=np.nanmin(rm,axis=0); self.frame["sensitivity_rank_max"]=np.nanmax(rm,axis=0)
        self.sorted_expected=np.sort(self.frame.bn_expected_vulnerability.to_numpy(float))
        self.comparison=pd.read_csv(self.directory/"sensitivity_comparison.csv").replace({np.nan:None}).to_dict("records")
        self.province=self.aggregate("by_province.csv"); self.district=self.aggregate("by_district.csv")
        self.fuzzy_check="unavailable"; self.fuzzy_rows=None
        if self.mode=="REAL" and FUZZY.exists():
            cols=[f"soft_{l}_{s}" for l in LEAVES for s in ("low","medium","high")]
            f=pd.read_csv(FUZZY,usecols=lambda c:c=="hhcode" or c in cols,dtype={"hhcode":"string"},low_memory=False)
            if len(f)!=len(self.frame) or f.hhcode.duplicated().any() or self.frame.hhcode.duplicated().any() or set(f.hhcode)!=set(self.frame.hhcode): raise ValueError("Stage 4 fuzzy keys do not match Stage 5")
            for leaf in LEAVES:
                x=f[[f"soft_{leaf}_{s}" for s in ("low","medium","high")]].to_numpy(float); obs=~np.isnan(x).any(1)
                if not np.allclose(x[obs].sum(1),1,atol=1e-6): raise ValueError(f"invalid memberships for {leaf}")
            self.fuzzy_rows=len(f); self.fuzzy_check="all eight leaf membership triplets found; observed rows sum to one"
        self.decisions=self.decision_index()

    def aggregate(self,name):
        p=self.directory/name
        if not p.exists(): return []
        d=pd.read_csv(p).replace({np.nan:None}).to_dict("records")
        return suppress(d)
    @staticmethod
    def decision_index():
        return [
          {"id":"S-02","status":"approved","open_conditions":[]},{"id":"M-03","status":"approved","open_conditions":[]},
          {"id":"M-04","status":"approved","open_conditions":[]},{"id":"M-05","status":"approved","open_conditions":[]},
          {"id":"M-06","status":"approved","open_conditions":[]},{"id":"M-07","status":"approved","open_conditions":[]},
          {"id":"D-10a","status":"approved","open_conditions":[]},
          *[{"id":f"B-0{i}","status":"approved","open_conditions":[]} for i in range(1,6)],
          {"id":"N-01","status":"approved with condition","open_conditions":["Stage 3b value-set check"]},
          {"id":"N-02","status":"approved with condition","open_conditions":["Source-flag agreement; direction is a researcher judgement"]},
          {"id":"H-01","status":"approved with condition","open_conditions":["Quantify B3 skip conflict under ISS-04 and ISS-05"]},
          {"id":"X-01","status":"conditional","open_conditions":["ISS-11 reference period; exposure excluded from baseline"]},
          {"id":"C-01","status":"conditional","open_conditions":["ISS-12 handling of codes 3, 4 and 997"]},
          {"id":"E-01","status":"candidate","open_conditions":["Evidence review and scale/skip checks"]},
          {"id":"W-01","status":"candidate","open_conditions":["Evidence review"]}]

def create_app(data: Data|None=None,force_synthetic=False):
    d=data or Data(force_synthetic)
    batches = {}
    app=FastAPI(title="Component 1 local scored-model API",version="0.1.0")
    app.state.data=d
    def env(**kwargs): return {"research_label":LABEL,"model_version":MODEL_VERSION,"spec_version":SPEC_VERSION,"data_manifest_sha256":d.manifest_hash,"data_mode":d.mode,**kwargs}
    app.mount("/assets",StaticFiles(directory=str(FRONTEND)),name="assets")
    @app.middleware("http")
    async def headers(request,call_next):
        res=await call_next(request)
        for k,v in (("X-Research-Label",LABEL),("X-Model-Version",MODEL_VERSION),("X-Spec-Version",SPEC_VERSION),("X-Data-Manifest-SHA256",d.manifest_hash),("X-Data-Mode",d.mode)): res.headers[k]=v
        return res
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request:Request,exc:StarletteHTTPException): return JSONResponse(status_code=exc.status_code,content=env(error=exc.detail))
    @app.exception_handler(RequestValidationError)
    async def bad_request(request:Request,exc:RequestValidationError): return JSONResponse(status_code=422,content=jsonable_encoder(env(error="Invalid request",details=exc.errors())))
    @app.get("/",include_in_schema=False)
    def page(): return FileResponse(FRONTEND/"index.html")
    @app.get("/openapi.yaml",include_in_schema=False)
    def contract(): return Response((API_DIR/"openapi.yaml").read_text(encoding="utf-8"),media_type="application/yaml")
    @app.get("/whatif/template.csv",include_in_schema=False)
    def csv_template():
        header=",".join(CSV_COLUMNS)+"\n"
        return Response(header,media_type="text/csv",headers={"Content-Disposition":"attachment; filename=component1_whatif_template.csv"})
    @app.get("/households")
    def households(province:str|None=None,district:str|None=None,min_percentile:float|None=Query(None,ge=0,le=100),max_percentile:float|None=Query(None,ge=0,le=100),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
        if min_percentile is not None and max_percentile is not None and min_percentile>max_percentile: raise HTTPException(422,"min_percentile must be <= max_percentile")
        f=d.frame; mask=pd.Series(True,index=f.index)
        if province is not None: mask &= f.province.astype("string")==province
        if district is not None: mask &= f.district.astype("string")==district
        if min_percentile is not None: mask &= f.percentile_rank>=min_percentile
        if max_percentile is not None: mask &= f.percentile_rank<=max_percentile
        subset=f.loc[mask].sort_values("row_id")
        return env(total=len(subset),offset=offset,limit=limit,items=[public_row(r) for _,r in subset.iloc[offset:offset+limit].iterrows()])
    @app.get("/households/{row_id}")
    def household(row_id:int):
        hit=d.frame.loc[d.frame.row_id==row_id]
        if hit.empty: raise HTTPException(404,"row_id not found")
        return env(item=public_row(hit.iloc[0]))
    @app.get("/summary")
    def summary():
        f=d.frame; q=f.bn_expected_vulnerability.quantile([0,.25,.5,.75,1]).to_dict(); bands=[]
        for lo in range(0,100,10):
            hi=lo+10; n=int(((f.percentile_rank>lo)&(f.percentile_rank<=hi)).sum())
            bands.append({"percentile_band":f"({lo}, {hi}]","households_n":n} if n>=10 else {"percentile_band":f"({lo}, {hi}]","suppressed":True})
        return env(household_count=len(f),score_summary={"expected_vulnerability_quantiles":{str(k):float(v) for k,v in q.items()},"mean_bn_p_high":float(f.bn_p_high.mean()),"mean_uncertainty_entropy":float(f.bn_uncertainty_entropy.mean())},percentile_bands=bands,geography={"by_province":d.province,"by_district":d.district})
    def input_record(leaves):
        if set(leaves)!=set(LEAVES): raise HTTPException(422,"leaves must contain exactly the eight baseline domains")
        rec={}
        for leaf in LEAVES:
            item=leaves[leaf]; c=float(item.coverage_fraction)
            if not 0<=c<=1: raise HTTPException(422,f"{leaf} coverage_fraction must be in [0,1]")
            val=item.degree
            if isinstance(val,str) and val.lower()=="unobserved":
                for s in ("low","medium","high"): rec[f"soft_{leaf}_{s}"]=np.nan
                c=0
            else:
                try: val=float(val)
                except (ValueError,TypeError): raise HTTPException(422,f"{leaf} degree must be [0,1] or 'unobserved'")
                if not 0<=val<=1: raise HTTPException(422,f"{leaf} degree must be in [0,1]")
                m=soft_levels(pd.Series([val])).iloc[0]
                for s in ("low","medium","high"): rec[f"soft_{leaf}_{s}"]=float(m[s])
            rec[f"dom_{leaf}_n_used"]=c; rec[f"dom_{leaf}_n_total"]=1.0
        return rec
    def score_records(entries):
        frame=pd.DataFrame([input_record(x["leaves"]) for x in entries])
        scored_frame=bn_v0_1.score(frame,bn_v0_1.config_v02_interim())
        output=[]
        for index,(_,scored) in enumerate(scored_frame.iterrows()):
            nodes={node:{s:float(scored[f"bn_{node}_{s}"]) for s in ("low","medium","high")} for node in ("living_conditions","sensitivity","adaptive_capacity","vulnerability")}
            expected=float(scored.bn_expected_vulnerability); pos=int(np.searchsorted(d.sorted_expected,expected,side="left"))
            result={"candidate_row_id":entries[index]["candidate_row_id"],"domain_inputs":entries[index]["domain_inputs"],"node_posteriors":nodes,
              "expected_vulnerability":expected,"uncertainty_entropy":float(scored.bn_uncertainty_entropy),"bn_p_high":float(scored.bn_p_high),
              "comparison_percentile":float(np.searchsorted(d.sorted_expected,expected,side="right")/len(d.sorted_expected)*100),
              "candidate_rank_among_baseline_plus_candidate":len(d.sorted_expected)-pos+1,"baseline_household_count":len(d.sorted_expected)}
            output.append(result)
        return output,scored_frame
    def clear_expired_batches():
        now=time.monotonic()
        for batch_id in list(batches):
            if now-batches[batch_id]["created"]>BATCH_TTL_SECONDS: batches.pop(batch_id,None)
    def parse_csv(raw):
        if len(raw)>MAX_CSV_BYTES: raise HTTPException(413,f"CSV exceeds the {MAX_CSV_BYTES} byte limit")
        try: text=raw.decode("utf-8-sig")
        except UnicodeDecodeError: raise HTTPException(400,"CSV must use UTF-8 encoding")
        reader=csv.DictReader(io.StringIO(text,newline=""))
        headers=reader.fieldnames or []
        if len(headers)!=len(set(headers)): raise HTTPException(422,"CSV has duplicate column names")
        if set(headers)!=set(CSV_COLUMNS):
            raise HTTPException(422,{"message":"CSV columns must exactly match the downloadable template","missing_columns":sorted(set(CSV_COLUMNS)-set(headers)),"unexpected_columns":sorted(set(headers)-set(CSV_COLUMNS))})
        accepted=[]; errors=[]; count=0
        for row_number,row in enumerate(reader,start=2):
            count+=1
            if count>MAX_BATCH_ROWS: raise HTTPException(413,f"CSV exceeds the {MAX_BATCH_ROWS} row limit")
            if row.get(None):
                errors.append({"row":row_number,"errors":["row has more values than the template columns"]})
                continue
            leaves={}; row_errors=[]
            for leaf in LEAVES:
                raw_degree=(row.get(f"{leaf}_degree") or "").strip()
                raw_coverage=(row.get(f"{leaf}_coverage_fraction") or "").strip()
                if not raw_degree or raw_degree.lower()=="unobserved":
                    degree="unobserved"; coverage=0.0
                else:
                    try: degree=float(raw_degree)
                    except ValueError: row_errors.append(f"{leaf}_degree must be a number or unobserved"); continue
                    if not np.isfinite(degree) or not 0<=degree<=1: row_errors.append(f"{leaf}_degree must be within 0..1"); continue
                    try: coverage=float(raw_coverage)
                    except ValueError: row_errors.append(f"{leaf}_coverage_fraction is required for an observed degree"); continue
                    if not np.isfinite(coverage) or not 0<=coverage<=1: row_errors.append(f"{leaf}_coverage_fraction must be within 0..1"); continue
                leaves[leaf]=Leaf(degree=degree,coverage_fraction=coverage)
            if row_errors: errors.append({"row":row_number,"errors":row_errors})
            else:
                values={leaf:{"degree":leaves[leaf].degree,"coverage_fraction":float(leaves[leaf].coverage_fraction)} for leaf in LEAVES}
                accepted.append({"candidate_row_id":row_number,"leaves":leaves,"domain_inputs":values})
        return accepted,errors,count
    async def read_csv_limited(request):
        chunks=[]; size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>MAX_CSV_BYTES: raise HTTPException(413,f"CSV exceeds the {MAX_CSV_BYTES} byte limit")
            chunks.append(chunk)
        return b"".join(chunks)
    @app.post("/whatif")
    async def whatif(request:Request):
        content_type=request.headers.get("content-type","").split(";",1)[0].strip().lower()
        if content_type in ("text/csv","application/csv"):
            accepted,errors,submitted=parse_csv(await read_csv_limited(request))
            if not accepted: raise HTTPException(422,{"message":"No valid candidate rows to score","submitted_rows":submitted,"rejected_rows":len(errors),"errors":errors[:100]})
            results,_=score_records(accepted)
            clear_expired_batches()
            while len(batches)>=BATCH_LIMIT:
                oldest=min(batches,key=lambda key:batches[key]["created"]); batches.pop(oldest,None)
            batch_id=uuid.uuid4().hex
            batches[batch_id]={"created":time.monotonic(),"results":results}
            return env(batch_id=batch_id,submitted_rows=submitted,scored_rows=len(results),rejected_rows=len(errors),errors=errors[:100],
                       results_url=f"/whatif/batches/{batch_id}?offset=0&limit=50",page_limit=100,expires_in_seconds=BATCH_TTL_SECONDS)
        if content_type!="application/json": raise HTTPException(415,"Send application/json for one candidate or text/csv for a batch")
        try: body=WhatIf.model_validate(await request.json())
        except (ValidationError,ValueError) as exc: raise HTTPException(422,"Invalid what-if JSON") from exc
        entry={"candidate_row_id":1,"leaves":body.leaves,"domain_inputs":{leaf:{"degree":body.leaves[leaf].degree,"coverage_fraction":float(body.leaves[leaf].coverage_fraction)} for leaf in body.leaves}}
        results,scored_frame=score_records([entry]); result=results[0]
        cpt=bn_v0_1.cpt_table("vulnerability",bn_v0_1.config_v02_interim()).to_dict("records")
        return env(**{k:v for k,v in result.items() if k!="candidate_row_id"},vulnerability_conditional_table=cpt)
    @app.get("/whatif/batches/{batch_id}")
    def batch_results(batch_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
        clear_expired_batches(); batch=batches.get(batch_id)
        if batch is None: raise HTTPException(404,"Batch not found or expired")
        results=batch["results"]
        return env(batch_id=batch_id,total=len(results),offset=offset,limit=limit,items=results[offset:offset+limit],expires_in_seconds=max(0,int(BATCH_TTL_SECONDS-(time.monotonic()-batch["created"]))))
    @app.get("/sensitivity")
    def sensitivity(): return env(scenarios=d.comparison)
    @app.get("/spec")
    def spec():
        docs=[{"filename":p.name,"content":p.read_text(encoding="utf-8-sig")} for p in sorted((PROJECT/"docs").glob("*decision_log*.md"))]
        return env(documents=docs,approved_decisions=d.decisions)
    @app.get("/model-info")
    def model_info(): return env(pipeline_version="stage5-v0.2.0",baseline_config="config_v02_interim()",baseline_leaves=list(LEAVES),exposure_in_baseline=False,household_count=len(d.frame),sensitivity_scenarios=len(d.sensitivity_files),stage4_fuzzy_row_count=d.fuzzy_rows,stage4_fuzzy_input_check=d.fuzzy_check,use_notice="Research prototype; no score is validated for decision use.")
    @app.get("/health")
    def health(): return env(status="ok",loaded_rows=len(d.frame),data_loaded=True)
    return app

app=create_app()

# Reuse the same endpoint definitions in the repository's shared FastAPI app.
# The shared app has its own /health route, so the model health route remains
# available only on the component's standalone development app.
api_router=APIRouter()
for route in app.routes:
    if isinstance(route, APIRoute) and route.path != "/health":
        api_router.routes.append(route)
    elif isinstance(route, Mount) and route.name == "assets":
        api_router.routes.append(route)
