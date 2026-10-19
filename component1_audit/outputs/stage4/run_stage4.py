"""Research output - not an eligibility determination. Stage 4 runner."""
from __future__ import annotations
from pathlib import Path
import hashlib, json, sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "component1_audit/outputs/stage4"
STAGE3 = ROOT / "component1_audit/outputs/stage3"
ENGINE_DIR = ROOT / "component1_audit/fuzzy_engine"
sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(OUT))
import fuzzy_v0_1 as engine
from fuzzy_adapter import adapt, LABEL

INPUT = STAGE3 / "modelling_inputs_v0_1.csv"
DICTIONARY = STAGE3 / "column_dictionary.csv"
ENGINE_FILE = ENGINE_DIR / "fuzzy_v0_1.py"
SPEC = ROOT / "component1_audit/docs/spec_v0_1_decision_log.md"
SENS = OUT / "sensitivity"

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def save_csv(df, path):
    x = df.copy()
    if "research_label" not in x:
        x.insert(0, "research_label", LABEL)
    x.to_csv(path, index=False, na_rep="", encoding="utf-8-sig")

def as_scoring_input(df):
    return df.drop(columns=["hhcode"], errors="ignore").copy()

def full_score(engine_input, refs):
    return engine.score_households(engine_input, refs)

def override_crowding(engine_input, refs, midpoint, half_width):
    old_mid, old_width = engine.CROWDING_MIDPOINT, engine.CROWDING_HALF_WIDTH
    try:
        engine.CROWDING_MIDPOINT = float(midpoint)
        engine.CROWDING_HALF_WIDTH = float(half_width)
        return full_score(engine_input, refs)
    finally:
        engine.CROWDING_MIDPOINT, engine.CROWDING_HALF_WIDTH = old_mid, old_width

def score_operator(engine_input, refs, operator):
    mu = engine.memberships(engine_input, refs)
    result = pd.concat([mu, operator_domains(mu, operator)], axis=1)
    for domain in engine.DOMAINS:
        lv = engine.soft_levels(result[f"dom_{domain}"]).add_prefix(f"soft_{domain}_")
        result = pd.concat([result, lv], axis=1)
    if "hhcode" in engine_input:
        result.insert(0, "hhcode", engine_input["hhcode"])
    return result

def operator_domains(mu, operator="mean"):
    out = pd.DataFrame(index=mu.index)
    for name, cols in engine.DOMAINS.items():
        block = mu[cols]
        if operator == "mean": value = block.mean(axis=1, skipna=True)
        elif operator == "min": value = block.min(axis=1, skipna=True)
        elif operator == "max": value = block.max(axis=1, skipna=True)
        else: raise ValueError(operator)
        out[f"dom_{name}"] = value
        out[f"dom_{name}_n_used"] = block.notna().sum(axis=1)
        out[f"dom_{name}_n_total"] = len(cols)
    return out

def level(scored, domain):
    cols = [f"soft_{domain}_low", f"soft_{domain}_medium", f"soft_{domain}_high"]
    a = scored[cols].to_numpy(float)
    out = np.full(len(a), None, dtype=object)
    valid = np.isfinite(a).any(axis=1)
    names = np.array(["low", "medium", "high"], dtype=object)
    out[valid] = names[np.nanargmax(a[valid], axis=1)]
    return pd.Series(out, index=scored.index, dtype="object")

def comparison_rows(baseline, scenario, name):
    rows=[]
    for domain in engine.DOMAINS:
        left = pd.to_numeric(baseline[f"dom_{domain}"], errors="coerce")
        right = pd.to_numeric(scenario[f"dom_{domain}"], errors="coerce")
        both = left.notna() & right.notna()
        corr = spearmanr(left[both], right[both]).statistic if both.sum() >= 2 else np.nan
        a, b = level(baseline, domain), level(scenario, domain)
        comparable = a.notna() & b.notna()
        changed = float((a[comparable] != b[comparable]).mean()) if comparable.any() else np.nan
        rows.append({"research_label": LABEL, "scenario": name, "domain": domain,
                     "spearman_rho": corr, "spearman_n": int(both.sum()),
                     "level_change_share": changed, "level_comparison_n": int(comparable.sum()), "status": "run"})
    return rows

def baseline_validation(stage3, engine_input, memberships, scores, refs):
    blocks=[]
    for col in memberships.columns:
        s=memberships[col]
        vals=s.dropna()
        for value,n in vals.value_counts(dropna=False).sort_index().items():
            blocks.append({"research_label":LABEL,"input_membership":col,"membership_value":float(value),"households_n":int(n),"known_n":int(s.notna().sum()),"unknown_n":int(s.isna().sum())})
        if vals.empty:
            blocks.append({"research_label":LABEL,"input_membership":col,"membership_value":"no_known_values","households_n":0,"known_n":0,"unknown_n":len(s)})
    save_csv(pd.DataFrame(blocks), OUT/"membership_distributions.csv")
    domain_rows=[]
    for dom in engine.DOMAINS:
        ncol=f"dom_{dom}_n_used"
        vc=scores[ncol].value_counts(dropna=False).sort_index()
        for n_used,count in vc.items():
            domain_rows.append({"research_label":LABEL,"domain":dom,"n_used":int(n_used),"households_n":int(count),"n_total":len(engine.DOMAINS[dom])})
    save_csv(pd.DataFrame(domain_rows), OUT/"domain_n_used_distributions.csv")
    domain_cols=[f"dom_{d}" for d in engine.DOMAINS]
    all_unknown=int(scores[domain_cols].isna().all(axis=1).sum())
    value_cols=list(memberships.columns)+domain_cols+[c for c in scores if c.startswith("soft_")]
    ranges={c:{"within_0_1":bool(scores[c].dropna().between(0,1).all()),"observed_n":int(scores[c].notna().sum()),"min":None if scores[c].dropna().empty else float(scores[c].min()),"max":None if scores[c].dropna().empty else float(scores[c].max())} for c in value_cols}
    solo=engine.score_households(as_scoring_input(engine_input.iloc[[0]]),refs)
    full=scores.iloc[[0]].drop(columns=["hhcode"],errors="ignore")
    solo_vals=solo.drop(columns=["hhcode"],errors="ignore").reset_index(drop=True)
    full_vals=full.reset_index(drop=True)
    solo_equal=bool(np.allclose(solo_vals.to_numpy(float),full_vals.to_numpy(float),equal_nan=True))
    # Write a detailed validation report with machine-checkable results and no IDs.
    lines=[LABEL,"","# Fuzzy validation report","",
      f"Input rows: {len(stage3):,}. Input SHA-256: `{sha(INPUT)}`.",
      f"Proxy columns present in Stage 3 table: {sorted({'label_high_vuln','pc_cons'} & set(stage3.columns))}.",
      "Membership value distributions and per-domain n_used distributions are in `membership_distributions.csv` and `domain_n_used_distributions.csv`.",
      f"Households with all domains unknown: {all_unknown:,}.",
      f"Scoring one household alone equals its full-batch score: {solo_equal}.","",
      "## Range checks","", "| Output | Within [0,1] | Observed | Min | Max |","|---|---:|---:|---:|---:|"]
    lines += [f"| {c} | {v['within_0_1']} | {v['observed_n']} | {v['min']} | {v['max']} |" for c,v in ranges.items()]
    lines += ["","## Coverage","","Known and unknown counts by engine input are in `input_coverage.csv`. Explicit `unknown` strings and blanks are passed as unknown by the adapter.","",
      "No overall vulnerability score or ranking is produced. These engineering and software checks do not validate indicators or domains for decision use.",""]
    (OUT/"fuzzy_validation.md").write_text("\n".join(lines),encoding="utf-8")
    return {"all_domains_unknown_n":all_unknown,"single_equals_batch":solo_equal,"range_checks":ranges}

def run_sensitivities(stage3, adapted, refs, baseline):
    SENS.mkdir(parents=True,exist_ok=True); comparisons=[]
    # (a) Crowding ramp perturbations, using the frozen baseline references.
    for midpoint in [3,4]:
        for half in [0.5,1.5]:
            name=f"crowding_mid{midpoint}_half{half:g}"
            score=override_crowding(as_scoring_input(adapted),refs,midpoint,half)
            save_csv(pd.concat([adapted[["hhcode"]].reset_index(drop=True),score.drop(columns=["hhcode"],errors="ignore").reset_index(drop=True)],axis=1),SENS/f"{name}.csv")
            comparisons += comparison_rows(baseline,score,name)
    # (b) 60+ definition with references re-fit using the alternate dependency ratio.
    alt=as_scoring_input(adapted).copy()
    denominator=pd.to_numeric(stage3["n_15_59"],errors="coerce")
    numerator=pd.to_numeric(stage3["n_under15"],errors="coerce")+pd.to_numeric(stage3["n_60plus"],errors="coerce")
    alt["dependency_ratio"]=numerator.div(denominator.where(denominator.ge(1)))
    alt["no_working_age_member"]=(denominator.fillna(0).lt(1)).astype(int)
    refs60=engine.fit_references(alt)
    age60=engine.score_households(alt,refs60)
    save_csv(pd.concat([adapted[["hhcode"]].reset_index(drop=True),age60.drop(columns=["hhcode"],errors="ignore").reset_index(drop=True)],axis=1),SENS/"age_cutoff_60plus.csv")
    comparisons += comparison_rows(baseline,age60,"age_cutoff_60plus")
    # (c) Alternative tenure statement is identical to the approved D-05 mapping.
    tenure=as_scoring_input(adapted).copy()
    tenure["tenure_class"] = stage3["c1_07"].map(lambda x: "secure" if x in (1,2,3) else "intermediate" if x in (4,5,6) else "insecure" if x in (7,8) else np.nan)
    ten=engine.score_households(tenure,refs)
    save_csv(pd.concat([adapted[["hhcode"]].reset_index(drop=True),ten.drop(columns=["hhcode"],errors="ignore").reset_index(drop=True)],axis=1),SENS/"tenure_codes_7_8_insecure.csv")
    comparisons += comparison_rows(baseline,ten,"tenure_codes_7_8_insecure")
    # (d) Toilet type only: deliberately ignore sharing and map type to the
    # corresponding type-level service degree for this requested sensitivity.
    toilet_only=as_scoring_input(adapted).copy()
    t=stage3["toilet_type_class"].astype("string")
    toilet_only["toilet_service_class"]=t.map({"improved":"basic","unimproved":"unimproved","open_defecation":"open_defecation"})
    type_score=engine.score_households(toilet_only,refs)
    save_csv(pd.concat([adapted[["hhcode"]].reset_index(drop=True),type_score.drop(columns=["hhcode"],errors="ignore").reset_index(drop=True)],axis=1),SENS/"toilet_type_only.csv")
    comparisons += comparison_rows(baseline,type_score,"toilet_type_only")
    # (e) No approved prorating formula specifies how to scale one/two invalid items.
    comparisons += [{"research_label":LABEL,"scenario":"fies_prorated_1_or_2_invalid_not_run","domain":domain,
                     "spearman_rho":np.nan,"spearman_n":0,"level_change_share":np.nan,
                     "level_comparison_n":0,"status":"not_run: prorating formula unspecified"}
                    for domain in engine.DOMAINS]
    # (f) Domain aggregation alternatives, preserving the same memberships.
    for op in ["min","max"]:
        op_score=score_operator(as_scoring_input(adapted),refs,op)
        save_csv(pd.concat([adapted[["hhcode"]].reset_index(drop=True),op_score.drop(columns=["hhcode"],errors="ignore").reset_index(drop=True)],axis=1),SENS/f"domain_{op}.csv")
        comparisons += comparison_rows(baseline,op_score,f"domain_{op}")
    comparison=pd.DataFrame(comparisons)
    save_csv(comparison,SENS/"sensitivity_comparison.csv")
    (SENS/"sensitivity_notes.md").write_text(
      f"{LABEL}\n\n# Sensitivity notes\n\n"
      "Crowding runs use the specified midpoint/half-width grid and the frozen baseline references. The 60+ age run uses n_15_59/n_60plus and re-fits only the dependency reference to the alternate dependency-ratio distribution. Tenure codes 7/8 as insecure reproduces the approved D-05 baseline mapping and is expected to be a no-op. The toilet-type-only sensitivity ignores sharing by assigning the engine's basic degree to improved toilet types. Domain min/max operators replace the approved mean only for the sensitivity files.\n\n"
      "FIES prorating was not run: the approved decision log calls for a one/two-item prorated-score sensitivity but does not specify the prorating formula or the denominator treatment. No new formula was assumed.\n",encoding="utf-8")

def main():
    OUT.mkdir(parents=True,exist_ok=True); SENS.mkdir(parents=True,exist_ok=True)
    stage3=pd.read_csv(INPUT,low_memory=False)
    dictionary=pd.read_csv(DICTIONARY,low_memory=False)
    if len(stage3)!=6847 or stage3.hhcode.isna().any() or stage3.hhcode.duplicated().any():
        raise ValueError("Stage 3 input must have 6,847 unique nonmissing household keys")
    if {"pc_cons","label_high_vuln"} & set(stage3.columns):
        raise ValueError("Proxy columns are forbidden in every Stage 4 input")
    adapted,coverage=adapt(stage3)
    if adapted.hhcode.isna().any() or adapted.hhcode.duplicated().any(): raise ValueError("Adapter key check failed")
    save_csv(coverage,OUT/"input_coverage.csv")
    prereq=[]
    for name,path in [("Stage 3 modelling input",INPUT),("Stage 3 column dictionary",DICTIONARY),
                      ("Reference fuzzy engine",ENGINE_FILE),("Reference engine tests",ENGINE_DIR/"test_fuzzy_v0_1.py"),("Approved decision log",SPEC)]:
        prereq.append({"research_label":LABEL,"input":str(path.relative_to(ROOT)),
                       "status":"present" if path.is_file() else "missing",
                       "sha256":sha(path) if path.is_file() else "",
                       "rows":int(sum(1 for _ in path.open(encoding="utf-8-sig"))-1) if path.is_file() and path.suffix==".csv" else ""})
    save_csv(pd.DataFrame(prereq),OUT/"prerequisite_check.csv")
    refs=engine.fit_references(as_scoring_input(adapted))
    previous_score_path=OUT/"fuzzy_scores_v0_1.csv"
    previous_toilet=None
    previous_score_sha=None
    correction_record=OUT/"toilet_score_correction_comparison.json"
    if correction_record.is_file():
        previous_toilet=json.loads(correction_record.read_text(encoding="utf-8"))
    elif previous_score_path.is_file():
        previous_df=pd.read_csv(previous_score_path,dtype={"hhcode":"string"},low_memory=False)
        if {"hhcode","mu_toilet"}.issubset(previous_df.columns):
            previous_toilet=previous_df[["hhcode","mu_toilet"]].copy()
            previous_score_sha=sha(previous_score_path)
    ref_obj={"research_label":LABEL,"model_version":engine.MODEL_VERSION,"spec_version":engine.SPEC_VERSION,
      "stage3_input":"component1_audit/outputs/stage3/modelling_inputs_v0_1.csv","stage3_input_sha256":sha(INPUT),
      "fit_rows":len(adapted),"reference_method":"Engine Reference empirical mid-rank CDF; income, asset_types_owned_n, dependency_ratio; no-worker dependency excluded from fit as engine defines.",
      "defaults":{"crowding_midpoint":engine.CROWDING_MIDPOINT,"crowding_half_width":engine.CROWDING_HALF_WIDTH,
        "minimum_valid_assets":engine.MIN_VALID_ASSETS,"tenure_degree":engine.TENURE_DEGREE,"toilet_degree":engine.TOILET_DEGREE,
        "material_degree":engine.MATERIAL_DEGREE,"soft_level_boundaries":"engine soft_levels triangular low/medium/high"},
      "references":{k:json.loads(v.to_json())["sorted"] for k,v in refs.items()}}
    (OUT/"reference_v0_1.json").write_text(json.dumps(ref_obj,indent=2),encoding="utf-8")
    baseline=engine.score_households(as_scoring_input(adapted),refs)
    score=pd.concat([adapted[["hhcode"]].reset_index(drop=True),baseline.reset_index(drop=True)],axis=1)
    score.insert(0,"research_label",LABEL)
    save_csv(score,OUT/"fuzzy_scores_v0_1.csv")
    service_tab=pd.crosstab(stage3["toilet_service_class"],stage3["toilet_type_class"],dropna=False)
    service_tab.index.name="toilet_service_class"
    save_csv(service_tab.reset_index(),OUT/"toilet_service_cross_tab.csv")
    if isinstance(previous_toilet,pd.DataFrame):
        old=previous_toilet.set_index("hhcode")["mu_toilet"]
        new=baseline.assign(hhcode=adapted.hhcode.to_numpy()).set_index("hhcode")["mu_toilet"]
        new=new.reindex(old.index)
        oldn=pd.to_numeric(old,errors="coerce"); newn=pd.to_numeric(new,errors="coerce")
        same=oldn.notna() & newn.notna() & np.isclose(oldn.fillna(0),newn.fillna(0),rtol=0,atol=1e-12)
        changed=int((~same & (oldn.notna() | newn.notna())).sum())
        comparison={"research_label":LABEL,"previous_score_file_sha256":previous_score_sha,
          "new_score_file_sha256":sha(OUT/"fuzzy_scores_v0_1.csv"),"households_compared":len(old),
          "previous_mu_toilet_observed_n":int(oldn.notna().sum()),"new_mu_toilet_observed_n":int(newn.notna().sum()),
          "households_with_changed_mu_toilet":changed,
          "change_definition":"membership differs (tolerance 1e-12), or known/unknown status changes; household keys aligned by hhcode"}
        correction_record.write_text(json.dumps(comparison,indent=2),encoding="utf-8")
        previous_toilet=comparison
    elif isinstance(previous_toilet,dict):
        # Keep the original toilet-membership comparison while refreshing the
        # hash of the current full score file, which may include other updates.
        previous_toilet["new_score_file_sha256"]=sha(OUT/"fuzzy_scores_v0_1.csv")
        previous_toilet["stage3_input_sha256"]=sha(INPUT)
        correction_record.write_text(json.dumps(previous_toilet,indent=2),encoding="utf-8")
    mu=engine.memberships(as_scoring_input(adapted),refs)
    validation=baseline_validation(stage3,adapted,mu,baseline,refs)
    run_sensitivities(stage3,adapted,refs,baseline)
    # Explicit source coverage notes for present but unknown Stage 3 fields.
    open_questions=[
      "D-04b correction applied: C1_10 codebook is 0=not shared and 1=shared for this cleaned file only; other values are unknown. This overrides the questionnaire's 1/2 convention for C1_10, with no other variable recoded.",
      "FIES prorated score sensitivity not run because D-01 does not specify how to prorate a raw score with one or two invalid items; no formula was invented.",
      "Stage 3 material durability fields are all the literal value `unknown` because the local DCS rule was unavailable in Stage 3; the adapter passes these as NaN. No material memberships can be observed.",
      "The supplied codebook rule for d_12-d_16 (0=No, 1=Yes; owned=1) is applied in Stage 3 only to those five variables. Stage 4 consumes the resulting asset_types_owned_n and asset_items_valid_n. The named docs/codebook_crosscheck_v0_1.md was not present in the workspace, so this build relies on the explicit code facts in the task.",
      "Stage 3 reports b0_01a/b0_01b failure counts and household-size/dependency counterfactuals in checks/A8_roster_flag_counterfactuals.csv, assuming raw flag=0 means fail for the diagnostic. Neither flag is applied to Stage 3 or Stage 4 inputs.",
      "The engine default MIN_VALID_ASSETS=None is retained: no minimum asset-item completeness threshold is enforced. D-10 leaves the denominator rule open; Stage 4 does not add a threshold.",
      "The crowding midpoint 3/half-width 1, TENURE_DEGREE and TOILET_DEGREE equal-spaced ordinal mappings, and soft low/medium/high boundaries are researcher judgements retained from the reference engine, not validated standards. The requested crowding perturbations are reported separately.",
      "The Stage 3 C1_08 mapping retains codes 5 and 10 as unconfirmed; the toilet-type-only sensitivity does not resolve those codes.",
      "Sensitivity level-change shares assign exact soft-membership ties using the engine output order low, medium, high (first maximum wins). The decision log does not specify a tie rule; the comparison should be interpreted with this implementation convention in mind.",
    ]
    (OUT/"open_questions.md").write_text(f"{LABEL}\n\n# Stage 4 open questions\n\n"+"\n\n".join(f"{i}. {q}" for i,q in enumerate(open_questions,1))+"\n",encoding="utf-8")
    all_unknown=validation["all_domains_unknown_n"]
    toilet_change=previous_toilet if isinstance(previous_toilet,dict) else json.loads(correction_record.read_text(encoding="utf-8")) if correction_record.is_file() else {}
    summary=(f"{LABEL}\n\n# Stage 4 fuzzy layer v0.1 summary\n\n"
      f"Integrated engine `{engine.MODEL_VERSION}` with {len(stage3):,} Stage 3 households. Created frozen income, asset and dependency empirical references; per-input memberships, domain degrees, n_used/n_total and soft levels; validation and sensitivity artifacts. No overall vulnerability score or ranking was produced.\n\n"
      f"Validation: unique household keys and expected row count passed; proxy columns absent; single-household/full-batch equivalence={validation['single_equals_batch']}; all-domain-unknown households={all_unknown:,}. Per-output [0,1] checks are recorded in `fuzzy_validation.md`.\n\n"
      f"Toilet correction: `mu_toilet` is observed for {int(baseline.mu_toilet.notna().sum()):,} households. Compared with the previous score, {toilet_change.get('households_with_changed_mu_toilet','not available')} households changed; details are in `toilet_score_correction_comparison.json`.\n\n"
      "The `toilet_service_class` by `toilet_type_class` cross-tab is in `toilet_service_cross_tab.csv`.\n\n"
      "Sensitivity includes four crowding ramp combinations, alternate 60+ age definition, D-05 tenure recoding, toilet type-only (sharing ignored), and domain min/max operators. Sensitivity Spearman correlations and largest-soft-membership level change shares are in `sensitivity/sensitivity_comparison.csv`. FIES prorating was not run because its scaling rule is unspecified.\n\n"
      "## Open questions\n\n"
      "1. FIES prorating for one or two invalid items remains unrun because D-01 does not specify a prorating formula.\n"
      "2. All three Stage 3 material durability fields remain unknown because the local DCS rule was unavailable; no material memberships are observed.\n"
      "3. Binary ownership fields d_12-d_16 remain partly missing under the registered 1/2 versus cleaned 0/1 mismatch; Stage 4 uses the existing asset aggregate unchanged.\n"
      "4. `MIN_VALID_ASSETS=None` is retained; D-10 leaves the valid-item denominator threshold open, so no threshold is enforced.\n"
      "5. Crowding midpoint 3/half-width 1, equal-spaced TENURE_DEGREE and TOILET_DEGREE, and triangular soft low/medium/high boundaries are researcher judgements retained from the engine, not validated standards; crowding alternatives are reported in sensitivity outputs.\n"
      "6. Sanitation codes 5 and 10 remain unconfirmed by Stage 3; the toilet-type-only run does not resolve them.\n"
      "7. Sensitivity change shares resolve exact soft-membership ties by engine output order (low, medium, high; first maximum wins); the decision log specifies no tie rule.\n\n"
      "Results are research outputs only; no indicator or domain is validated for decision use. See `open_questions.md` for detail.\n")
    (OUT/"stage4_summary.md").write_text(summary,encoding="utf-8")
    # Manifest is assembled last; household-level CSVs are git-ignored by the project.
    files=[p for p in OUT.rglob("*") if p.is_file() and p.name!="manifest.json" and "__pycache__" not in p.parts and p.suffix!=".pyc"]
    inputs=[INPUT,DICTIONARY,ENGINE_FILE,ENGINE_DIR/"test_fuzzy_v0_1.py",SPEC]
    manifest={"research_label":LABEL,"stage_version":"4.0.1","engine_model_version":engine.MODEL_VERSION,
      "spec_version":engine.SPEC_VERSION,"household_rows":len(stage3),"inputs":{},"outputs":{}}
    for p in inputs:
        manifest["inputs"][str(p.relative_to(ROOT))]={"sha256":sha(p),"rows":int(sum(1 for _ in p.open(encoding="utf-8-sig"))-1) if p.suffix==".csv" else None}
    for p in files:
        manifest["outputs"][str(p.relative_to(OUT))]={"sha256":sha(p),"rows":int(sum(1 for _ in p.open(encoding="utf-8-sig"))-1) if p.suffix==".csv" else None}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"Stage 4 built: {len(stage3)} rows; {len(baseline.columns)} score columns; {len(manifest['outputs'])} output hashes")

if __name__=="__main__": main()
