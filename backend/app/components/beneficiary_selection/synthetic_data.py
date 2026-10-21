"""Deterministic fake Stage 5-shaped data for demos and API tests."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

LABEL = "Research output - not an eligibility determination"
SCENARIOS = ["sigma_0.08", "sigma_0.25", "n_states_5", "weights_economic_food_doubled", "weights_demographic_doubled",
"blend_none", "blend_min_coverage_0.5", "empirical_priors", "flat_sensitivity_structure", "drop_shelter_quality",
"drop_sanitation", "drop_crowding_tenure", "drop_food", "drop_demographic", "drop_health", "drop_economic",
"drop_financial_resilience", "include_exposure"]

def build(directory: Path, n: int = 60) -> None:
    directory.mkdir(parents=True, exist_ok=True); (directory / "sensitivity").mkdir(exist_ok=True)
    rng = np.random.default_rng(731)
    df = pd.DataFrame({"research_label": LABEL, "hhcode": [f"SYNTH-{i:05}" for i in range(1,n+1)]})
    for node in ("living_conditions", "sensitivity", "adaptive_capacity", "vulnerability"):
        probs = rng.dirichlet([2,2,1.1], n)
        for j,s in enumerate(("low","medium","high")): df[f"bn_{node}_{s}"] = probs[:,j]
    df["bn_p_high"] = df.bn_vulnerability_high
    df["bn_expected_vulnerability"] = df.bn_vulnerability_low/6 + df.bn_vulnerability_medium/2 + df.bn_vulnerability_high*5/6
    v = df[["bn_vulnerability_low","bn_vulnerability_medium","bn_vulnerability_high"]].to_numpy()
    df["bn_uncertainty_entropy"] = -(np.where(v>0,v*np.log(v),0)).sum(1)/np.log(3)
    df["bn_leaves_observed"] = rng.integers(4,9,n); df["bn_leaves_total"] = 8
    df["bn_model_version"] = "bn_v0.1.0"; df["bn_sigma"] = .15; df["bn_blend"] = "proportional"
    df.to_csv(directory/"bn_scores_v0_2_interim.csv",index=False)
    cmp=[]; base=df.bn_expected_vulnerability.to_numpy()
    for i,scenario in enumerate(SCENARIOS):
        alt=df.copy(); noise=rng.normal(0,.025+(i%4)*.005,n)
        alt.bn_expected_vulnerability=np.clip(base+noise,.05,.95); alt.bn_p_high=np.clip(df.bn_p_high+noise*.7,0,1)
        alt.bn_vulnerability_high=alt.bn_p_high
        alt.bn_vulnerability_low=(1-alt.bn_p_high)*df.bn_vulnerability_low/(df.bn_vulnerability_low+df.bn_vulnerability_medium)
        alt.bn_vulnerability_medium=1-alt.bn_vulnerability_low-alt.bn_p_high
        alt["bn_scenario"]=scenario; alt["bn_scenario_status"]="SYNTHETIC example"
        alt.to_csv(directory/"sensitivity"/f"{scenario}.csv",index=False)
        cmp.append({"research_label":LABEL,"scenario":scenario,"status":"SYNTHETIC example","spearman_expected_vulnerability_vs_baseline":.9,
          "rank_correlation_n":n,"mean_absolute_bn_p_high_change":float(np.abs(alt.bn_p_high-df.bn_p_high).mean()),"p_high_comparison_n":n,
          "most_probable_vulnerability_level_changed_n":1,"most_probable_vulnerability_level_changed_share":1/n})
    pd.DataFrame(cmp).to_csv(directory/"sensitivity_comparison.csv",index=False)
    for name,keys in (("by_province.csv",["a_01_province"]),("by_district.csv",["a_01_province","a_02_district"])):
        groups=[]
        for p in (1,2,3):
            for d in ((None,) if len(keys)==1 else (1,2)):
                mask=(np.arange(n)%3==p-1)
                if d is not None: mask &= (np.arange(n)%2==d-1)
                part=df.loc[mask]; row={"research_label":LABEL,"a_01_province":p,"households_n":len(part),
                 "mean_bn_p_high":part.bn_p_high.mean(),"mean_bn_expected_vulnerability":part.bn_expected_vulnerability.mean(),"mean_bn_uncertainty_entropy":part.bn_uncertainty_entropy.mean()}
                if d is not None: row["a_02_district"]=d
                groups.append(row)
        pd.DataFrame(groups).to_csv(directory/name,index=False)
    manifest={"research_label":LABEL,"mode":"SYNTHETIC","model_version":"bn_v0.1.0","row_count":n,"files":{}}
    for p in sorted(directory.rglob("*.csv")): manifest["files"][str(p.relative_to(directory)).replace("\\","/")]=hashlib.sha256(p.read_bytes()).hexdigest()
    (directory/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
