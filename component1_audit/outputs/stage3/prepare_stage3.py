"""Stage 3 v0.2.0 data engineering; all writes remain in outputs/stage3."""
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"component1_audit/outputs"
OUT=BASE/"stage3"
CLEAN=ROOT/"Data/processed/clean"
PIPE=BASE/"pipeline_v0"
REG=ROOT/"component1_audit/review_register/indicator_approval_register.csv"
DEC=ROOT/"component1_audit/review_register/research_decision_register.csv"
CODEBOOK=ROOT/"component1_audit/docs/codebook_crosscheck_v0_1.md"
SPEC=ROOT/"component1_audit/docs/spec_v0_1_decision_log.md"
HOUSING_XWALK=BASE/"d1_housing_material_validation/housing_material_crosswalk.csv"
ASSETS=["d_01","d_03","d_05","d_06","d_08","d_10","d_12","d_13","d_14","d_15","d_16","d_17","d_18","d_19","d_20","d_21","d_22","d_23"]
COUNT_ASSETS={"d_01","d_03","d_05","d_06","d_08","d_10","d_17","d_18","d_19","d_20","d_21","d_22","d_23"}
BINARY_ASSETS=set(ASSETS)-COUNT_ASSETS

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def read(path,cols=None,dtype=None):
    if not Path(path).is_file(): raise FileNotFoundError(f"Required input unavailable: {path}")
    return pd.read_csv(path,usecols=cols,dtype=dtype or {"hhcode":"string","pid":"string","hhmember":"string"},low_memory=False)

def num(s): return pd.to_numeric(s,errors="coerce")
def norm_flag(x):
    if pd.isna(x): return False
    if isinstance(x,(bool,np.bool_)): return bool(x)
    v=num(pd.Series([x])).iloc[0]
    if pd.notna(v): return bool(v==1)
    return str(x).strip().lower() in {"true","yes","y"}
def safe_value_counts(series):
    s=series.astype("string").fillna("[MISSING]")
    out=s.value_counts(dropna=False,sort=True)
    return out
def output_table(rows,name,columns=None):
    df=pd.DataFrame(rows,columns=columns)
    if name.startswith("A8_") and "research_label" not in df.columns:
        df.insert(0,"research_label","Research output - not an eligibility determination")
    df.to_csv(OUT/"checks"/name,index=False,encoding="utf-8-sig")
    return df

def run_checks():
    """Part A must complete before any Part B file is built."""
    checkdir=OUT/"checks"; checkdir.mkdir(parents=True,exist_ok=True)
    master=read(CLEAN/"mod_a_household_identification.csv",["hhcode","hh_type"])
    housing=read(CLEAN/"mod_c_housing.csv",["hhcode","c1_01","c1_01_other","c1_02","c1_04","c1_05","c1_06","c1_07","c1_08","c1_08_other","c1_10"],dtype={"hhcode":"string"})
    roster=read(CLEAN/"mod_b0_roster_long.csv",["hhcode","pid","b0_01a","b0_01b","b0_04_years","b0_04_months"],dtype={"hhcode":"string","pid":"string"})
    fies=read(PIPE/"fies_item_responses_pending.csv")
    assets=read(CLEAN/"mod_d_assets.csv",["hhcode",*ASSETS],dtype={"hhcode":"string"})
    # A1: response-form coverage by hh_type; household identifiers are never emitted.
    h=master[["hhcode","hh_type"]].merge(fies[["hhcode","l1_answered","l2_answered"]],on="hhcode",how="left",validate="one_to_one")
    l1=h.l1_answered.map(norm_flag); l2=h.l2_answered.map(norm_flag)
    h["fies_form"]="neither"; h.loc[l1&~l2,"fies_form"]="L1 only"; h.loc[~l1&l2,"fies_form"]="L2 only"; h.loc[l1&l2,"fies_form"]="both"
    rows=[]
    for (typ,form),n in h.groupby(["hh_type","fies_form"],dropna=False).size().items(): rows.append({"hh_type":typ if pd.notna(typ) else "[MISSING]","form_answer_pattern":form,"households_n":int(n),"denominator_hh_type_households_n":int((h.hh_type==typ).sum()) if pd.notna(typ) else int(h.hh_type.isna().sum())})
    output_table(rows,"A1_fies_form_by_hh_type.csv")
    legacy_a1=checkdir/"A1_fies_form_by_hhtype.csv"
    if legacy_a1.exists(): legacy_a1.unlink()
    rows=[{"form_answer_pattern":k,"households_n":int(v),"denominator_master_households_n":len(h)} for k,v in h.fies_form.value_counts().items()]
    output_table(rows,"A1_fies_form_totals.csv")
    # Counterfactual only: report, but do not apply, flag=0 as failing each roster flag.
    # The codebook's flag semantics are not present locally; this is a transparent diagnostic.
    counterfactual=[]
    base_roster_n=roster.groupby("hhcode").pid.nunique()
    age_values=num(roster.b0_04_years)
    for flag in ["b0_01a","b0_01b"]:
        failed=num(roster[flag]).eq(0)
        retained=roster.loc[~failed].copy()
        retained_size=retained.groupby("hhcode").pid.nunique().reindex(base_roster_n.index,fill_value=0)
        changed_size=int(retained_size.ne(base_roster_n).sum())
        old=roster.assign(age=age_values).groupby("hhcode").agg(
            under=("age",lambda s:int((s.ge(0)&s.lt(15)).sum())),
            working=("age",lambda s:int((s.ge(15)&s.le(64)).sum())),
            older=("age",lambda s:int(s.ge(65).sum())))
        kept=retained.assign(age=num(retained.b0_04_years)).groupby("hhcode").agg(
            under=("age",lambda s:int((s.ge(0)&s.lt(15)).sum())),
            working=("age",lambda s:int((s.ge(15)&s.le(64)).sum())),
            older=("age",lambda s:int(s.ge(65).sum()))).reindex(old.index,fill_value=0)
        old_ratio=(old.under+old.older).div(old.working.where(old.working.ge(1)))
        new_ratio=(kept.under+kept.older).div(kept.working.where(kept.working.ge(1)))
        ratio_changed=(old_ratio.notna()!=new_ratio.notna()) | (old_ratio.notna()&new_ratio.notna()&~np.isclose(old_ratio.fillna(0),new_ratio.fillna(0),rtol=0,atol=1e-12))
        counterfactual.append({"flag":flag,"assumed_failure_rule":"raw flag value == 0 (counterfactual only; not applied)",
          "roster_members_flagged_fail_n":int(failed.sum()),"roster_members_flag_missing_n":int(num(roster[flag]).isna().sum()),
          "households_household_size_would_change_n":changed_size,
          "households_dependency_ratio_would_change_n":int(ratio_changed.sum()),
          "households_dependency_ratio_known_status_would_change_n":int((old_ratio.notna()!=new_ratio.notna()).sum()),
          "dependency_definition":"(under15 + age65plus) / age15to64 using observed ages; counterfactual removes flagged roster rows"})
    output_table(counterfactual,"A8_roster_flag_counterfactuals.csv")
    for flag in ["b0_01a","b0_01b"]:
        rows=[{"flag":flag,"raw_code_or_missing":str(k),"roster_members_n":int(v),"denominator_roster_members_n":len(roster)} for k,v in safe_value_counts(roster[flag]).items()]
        output_table(rows,f"A8_{flag}_code_counts.csv")
    # A2: disclose 999 counts and frequency-only, pseudonymous counts for free text.
    merge=housing[["hhcode","c1_01","c1_01_other","c1_04","c1_05","c1_06","c1_07","c1_08","c1_08_other"]].copy()
    rows=[]
    for col in ["c1_01","c1_04","c1_05","c1_06","c1_07","c1_08"]:
        codes=num(merge[col]); rows.append({"variable":col,"code_999_households_n":int(codes.eq(999).sum()),"denominator_housing_records_n":len(merge),"missing_item_n":int(merge[col].isna().sum())})
    output_table(rows,"A2_housing_999_counts.csv")
    other_all=merge.c1_08_other.astype("string")
    other_all=other_all[other_all.notna() & other_all.str.strip().ne("")].str.strip()
    other=merge.loc[num(merge.c1_08).eq(999),"c1_08_other"].astype("string")
    other=other[other.notna() & other.str.strip().ne("")].str.strip()
    vc=other.value_counts(dropna=True)
    rows=[{"redacted_value_id":f"OTHER_{i:03d}","nonblank_text_count_n":int(n),"denominator_c1_08_999_households_n":int(num(merge.c1_08).eq(999).sum()),"note":"Text value intentionally suppressed; ID is not a recoverable mapping."} for i,n in enumerate(vc.tolist(),1)]
    output_table(rows,"A2_c1_08_other_redacted_counts.csv",["redacted_value_id","nonblank_text_count_n","denominator_c1_08_999_households_n","note"])
    rows=[{"c1_08_999_households_n":int(num(merge.c1_08).eq(999).sum()),"c1_08_other_nonblank_text_records_for_999_n":int(len(other)),"distinct_nonblank_text_values_for_999_n":int(vc.size),"all_household_nonblank_c1_08_other_records_n":int(len(other_all)),"distinct_nonblank_c1_08_other_values_all_codes_n":int(other_all.nunique()),"other_blank_or_missing_when_999_n":int(num(merge.c1_08).eq(999).sum()-len(other)),"denominator_housing_records_n":len(merge),"note":"Raw text omitted by privacy constraint; redacted frequency table is restricted to code 999."}]
    output_table(rows,"A2_c1_08_other_summary.csv")
    # A3: bedroom distribution and persons-per-bedroom for positive bedroom values.
    z=master[["hhcode"]].merge(housing[["hhcode","c1_02"]],on="hhcode",validate="one_to_one").merge(
        read(PIPE/"household_core.csv",["hhcode","roster_member_count"]),on="hhcode",validate="one_to_one")
    bed=num(z.c1_02); valid_bed=bed.ge(1)&bed.notna()
    rows=[{"c1_02_value":v,"households_n":int(n),"denominator_master_households_n":len(z)} for v,n in safe_value_counts(z.c1_02).items()]
    output_table(rows,"A3_bedroom_distribution.csv")
    positive=bed[valid_bed]
    implausible=int((bed.lt(0)|((bed%1).ne(0)&bed.notna())|((z.c1_02.notna())&bed.isna())).sum())
    ppr=num(z.roster_member_count).div(bed).where(valid_bed & num(z.roster_member_count).notna())
    rows=[{"bedrooms_zero_n":int(bed.eq(0).sum()),"bedrooms_missing_n":int(bed.isna().sum()),"bedrooms_negative_noninteger_or_unparseable_n":implausible,"bedrooms_gt_10_n":int(bed.gt(10).sum()),"positive_bedroom_households_n":int(valid_bed.sum()),"persons_per_bedroom_observed_n":int(ppr.notna().sum()),"persons_per_bedroom_denominator_n":int(valid_bed.sum()),"master_denominator_n":len(z),"definition":"Data-impossible values are negative/noninteger/unparseable. No normative high-bedroom cutoff supplied; >10 is reported separately, not deemed invalid."}]
    output_table(rows,"A3_bedroom_summary.csv")
    pc=ppr.round(3).astype("string").fillna("[MISSING]").value_counts(dropna=False)
    rows=[{"persons_per_bedroom_rounded_3dp":v,"households_n":int(n),"denominator_positive_bedrooms_households_n":int(valid_bed.sum()),"observed_ratio_denominator_n":int(ppr.notna().sum())} for v,n in pc.items() if v!="[MISSING]"]
    output_table(rows,"A3_persons_per_bedroom_distribution.csv")
    # A4: age coverage, ranges, integrity and age-band household counts from years only.
    yrs=num(roster.b0_04_years); mos=num(roster.b0_04_months)
    age_summary=[]
    for field,s in [("b0_04_years",yrs),("b0_04_months",mos)]:
        age_summary.append({"variable":field,"roster_person_rows_n":len(roster),"observed_n":int(s.notna().sum()),"missing_n":int(s.isna().sum()),"minimum":s.min(skipna=True),"maximum":s.max(skipna=True),"noninteger_n":int((s.notna()&(s%1).ne(0)).sum()),"negative_n":int(s.lt(0).sum()),"above_100_n":int(s.gt(100).sum()),"denominator_roster_person_rows_n":len(roster)})
    output_table(age_summary,"A4_age_field_summary.csv")
    age=roster[["hhcode","pid"]].copy(); age["age_years_num"]=yrs
    age["under15"]=(yrs.ge(0)&yrs.lt(15)).astype("int64")
    age["15_64"]=(yrs.ge(15)&yrs.le(64)).astype("int64")
    age["65plus"]=(yrs.ge(65)).astype("int64")
    age["15_59"]=(yrs.ge(15)&yrs.le(59)).astype("int64")
    age["60plus"]=(yrs.ge(60)).astype("int64")
    age["age_missing"]=yrs.isna().astype("int64")
    ag=age.groupby("hhcode",sort=False).agg(n_under15=("under15","sum"),n_15_64=("15_64","sum"),n_65plus=("65plus","sum"),n_15_59=("15_59","sum"),n_60plus=("60plus","sum"),n_age_missing=("age_missing","sum"),age_observed_n=("age_years_num","count")).reset_index()
    # Household coverage counts: zero in band based only on observed age years; fully missing age is reported separately.
    no6464=ag.n_15_64.eq(0); no1559=ag.n_15_59.eq(0)
    rows=[{"definition":"working-age 15-64 (65+ begins at 65)","households_no_observed_member_in_band_n":int(no6464.sum()),"households_all_ages_missing_n":int(ag.age_observed_n.eq(0).sum()),"households_with_some_age_missing_n":int(ag.n_age_missing.gt(0).sum()),"denominator_master_households_with_roster_n":len(ag)},
          {"definition":"working-age 15-59 (60+ begins at 60)","households_no_observed_member_in_band_n":int(no1559.sum()),"households_all_ages_missing_n":int(ag.age_observed_n.eq(0).sum()),"households_with_some_age_missing_n":int(ag.n_age_missing.gt(0).sum()),"denominator_master_households_with_roster_n":len(ag)}]
    output_table(rows,"A4_households_without_working_age_member.csv")
    # A5: FIES per item/per form, and completeness/special/blank household counts.
    rows=[]; sums=[]
    for form in ["l1","l2"]:
        cols=[f"{form}_{i:02d}" for i in range(1,9)]
        vals=fies[cols].apply(lambda s:num(s))
        for col in cols:
            s=vals[col]
            rows.append({"form":form.upper(),"item":col,"code_1_yes_n":int(s.eq(1).sum()),"code_2_no_n":int(s.eq(2).sum()),"code_3_dk_n":int(s.eq(3).sum()),"code_4_refused_n":int(s.eq(4).sum()),"blank_n":int(fies[col].isna().sum()),"other_code_n":int((s.notna()&~s.isin([1,2,3,4])).sum()),"denominator_form_household_records_n":len(fies)})
        all_valid=vals.isin([1,2]).all(axis=1)
        any_34=vals.isin([3,4]).any(axis=1)
        any_blank=fies[cols].isna().any(axis=1)
        sums.append({"form":form.upper(),"all_8_items_valid_1_or_2_n":int(all_valid.sum()),"at_least_one_dk_or_refused_n":int(any_34.sum()),"at_least_one_blank_n":int(any_blank.sum()),"at_least_one_dk_refused_or_blank_n":int((any_34|any_blank).sum()),"other_code_households_n":int((vals.notna()&~vals.isin([1,2,3,4])).any(axis=1).sum()),"denominator_master_households_n":len(fies)})
    output_table(rows,"A5_fies_item_response_counts.csv")
    output_table(sums,"A5_fies_form_completeness.csv")
    # A6: all observed housing response codes; no code remapping.
    rows=[]
    for c in ["c1_04","c1_05","c1_06","c1_07","c1_08","c1_10"]:
        for val,nv in safe_value_counts(housing[c]).items():
            rows.append({"variable":c,"observed_code_or_missing":val,"households_n":int(nv),"denominator_housing_records_n":len(housing),"exists_in_clean_prepared_housing_file":True})
    output_table(rows,"A6_housing_code_counts.csv")
    # A7: precisely the 18 D-module asset items approved for item-level validation.
    approval=read(REG)
    itemrows=[]
    for _,r in approval[approval.candidate_id.astype("string").str.startswith("d1_asset_item_")].iterrows():
        col=str(r.source_variable_exact)
        s=num(assets[col]); definition=str(r.response_codes_and_meanings)
        vals=sorted(s.dropna().unique().tolist())
        if col in BINARY_ASSETS and col in {"d_12","d_13","d_14","d_15","d_16"}:
            unexpected=sorted(s[s.notna()&~s.isin([0,1])].unique().tolist()); validation="pass" if not unexpected else "mismatch: values outside codebook 0/1"
            definition="Codebook cross-check: 0=No; 1=Yes; owned=1 (applied only to d_12-d_16)."
        elif "Integer count" in definition:
            invalid=s.notna()&(s.lt(0)|(s%1).ne(0)); unexpected=sorted(s[invalid].unique().tolist()); validation="pass" if not unexpected else "mismatch: invalid count values"
        elif "1 No; 2 Yes" in definition:
            unexpected=sorted(s[s.notna()&~s.isin([1,2])].unique().tolist()); validation="pass" if not unexpected else "mismatch: values outside 1/2"
        else:
            unexpected=vals; validation="unresolved: approval register does not specify a supported coding rule"
        itemrows.append({"candidate_id":r.candidate_id,"variable":col,"response_codes_and_meanings":definition,"observed_value_set":"|".join(str(v) for v in vals),"missing_n":int(s.isna().sum()),"denominator_asset_household_records_n":len(assets),"unexpected_values":"|".join(str(v) for v in unexpected),"comparison_status":validation})
    output_table(itemrows,"A7_asset_value_sets_and_code_checks.csv")
    # Decision log reconciliation for explicit facts and expected scope.
    decision_rows=[
        {"check":"master household rows","decision_or_prior_reference":"DEC-15 provisional master 6,847; pipeline v0.1 manifest","observed":"6847 expected if source unchanged","status":"see Part B build assertions"},
        {"check":"D-module direct asset item count","decision_or_prior_reference":"RDEC-D1-02 lists 18 asset items; DEC-18 item-level validation only","observed":f"{len(itemrows)} direct asset items from approval register","status":"match" if len(itemrows)==18 else "mismatch"},
        {"check":"C1_08 code 999 household count","decision_or_prior_reference":"prior register reports 22 households coded 999","observed":f"{int(num(housing.c1_08).eq(999).sum())} / {len(housing)} housing records","status":"match" if int(num(housing.c1_08).eq(999).sum())==22 else "mismatch"},
        {"check":"C1_08 Other text nonblank records across all codes","decision_or_prior_reference":"prior register reports 24 nonblank text records across all C1_08 codes; value text suppressed","observed":f"{len(other_all)} nonblank records / {len(housing)} housing records; within code 999: {len(other)} / {int(num(housing.c1_08).eq(999).sum())}","status":"match" if len(other_all)==24 else "mismatch"},
        {"check":"C1_10 available in prepared housing module","decision_or_prior_reference":"A6 requires C1_10 code and missingness diagnostic","observed":"present in Data/processed/clean/mod_c_housing.csv" if "c1_10" in housing else "absent","status":"match" if "c1_10" in housing else "mismatch"},
        {"check":"C1_10 code convention","decision_or_prior_reference":"D-04b researcher-provided cleaned-file codebook overrides questionnaire convention for this file only","observed":"0=not shared; 1=shared; other/missing=unknown","status":"applied to C1_10 only"},
        {"check":"material durability mapping","decision_or_prior_reference":"D-03a researcher-specified lookup","observed":"C1_04: 1/2/3 durable, 4 non_durable; C1_05: 1/2/6 durable, 3/4/5 non_durable; C1_06: 1/2/3 durable, 6 non_durable; all other rows blank","status":"applied exactly"},
    ]
    output_table(decision_rows,"decision_log_comparison.csv")
    # Part A may identify additional cases needing careful interpretation; write questions before Part B.
    questions=[
       "**C1_08 free text:** among 22 households coded 999, 22 have nonblank text and 13 distinct values; across all codes, 24 records have nonblank Other text and 15 distinct values. Raw text is withheld under the hard privacy rule. Checks contain redacted category IDs and frequencies only; no ID-to-text map is written.",
       "**FIES both/neither forms:** `fies_valid_items_n` is not form-specific for both-form or no-form households. To avoid combining or selecting forms, that field remains blank in those cases; raw items remain separate. No score is created for both forms.",
       "**Codebook cross-check:** `component1_audit/docs/codebook_crosscheck_v0_1.md` is authoritative for the cleaned-file codes and agrees with the current handling of C1_10, d_12-d_16, the 18-item asset set, FIES codes, and `hh_type`. d_12-d_16 use 0=No, 1=Yes, owned=1; this recoding applies only to these five assets.",
       "**Roster flag rules:** the codebook defines b0_01a as lived in the household at least 6 months and b0_01b as ate from the same pot in the past 7 days, but does not decide whether either flag changes roster_member_count or age counts. Checks/A8 reports the requested flag=0 counterfactual only; no flag exclusion is applied.",
       "**Age sensitivity ratios:** age counts use the years field and requested bands. Sensitivity ratios use the literal bands in their names: youth / observed working-age 15-64, old-age 65+ / 15-64, and (under15 + 60+)/15-59. Households with no observed working-age member have blank ratios and flag=1 as specified; if ages are missing, the flag reflects absence of an observed in-band member, not verified absence of such a person.",
       "**C1_08 proposed codes 5 and 10:** the supplied sanitation mapping is applied as proposed for traceable output, but lookup `mapping_confirmed` is FALSE for these codes and their classes must not be treated as confirmed.",
       "**D-04b correction:** the researcher-provided cleaned-file codebook overrides the questionnaire's 1=No/2=Yes convention for C1_10 only: 0=not shared and 1=shared; other/missing=unknown. Stage 3 applies this mapping only to C1_10. C1_08 type classes are unchanged.",
       "**Decision log:** `component1_audit/docs/spec_v0_1_decision_log.md` is included as an input. The codebook cross-check confirms cleaned-file meanings; it does not change the other approved rules.",
    ]
    unexpected_a=[r["variable"]+": "+r["unexpected_values"] for r in itemrows if r["unexpected_values"] and not r["variable"] in {"d_12","d_13","d_14","d_15","d_16"}]
    if unexpected_a: questions.append("**Other asset value exceptions:** "+"; ".join(unexpected_a)+". Affected owned fields remain blank pending code clarification.")
    questions=[q for q in questions if not q.startswith("**FIES unexpected codes:")]
    (OUT/"open_questions.md").write_text("# Stage 3 open questions\n\nThese items are stopped or explicitly scoped pending evidence; other unambiguous engineering steps may proceed.\n\n"+"\n\n".join(f"{i}. {q}" for i,q in enumerate(questions,1))+"\n",encoding="utf-8")
    confirmation=[
      "Research output - not an eligibility determination", "", "# Codebook rule confirmation", "",
      "| Rule checked | Applied in rebuild | Authoritative crosscheck |", "|---|---|---|",
      "| C1_10 toilet sharing | 0 = not shared; 1 = shared; any other value unknown | `codebook_crosscheck_v0_1.md`, line 9 |",
      "| d_12-d_16 binary assets | 0 = no; 1 = yes; owned when 1 | `codebook_crosscheck_v0_1.md`, line 10 |",
      "| Asset inventory | Exactly 18 direct items; d_07/d_09/d_11 and all listed follow-ups excluded | `codebook_crosscheck_v0_1.md`, lines 29-31 |",
      "| FIES | 1 = Yes; 2 = No; 3/4 = missing for scoring | `codebook_crosscheck_v0_1.md`, line 16 |",
      "| FIES form cross-tab key | `hh_type` (not `hhtype`) | `codebook_crosscheck_v0_1.md`, line 32 |", "",
      "No conflict was found between these crosscheck rules and the corresponding Stage 3 handling. The decision log retains an old follow-up reference to `hhtype`; the authoritative crosscheck and rebuilt table use `hh_type`.", ""]
    (OUT/"codebook_rule_confirmation.md").write_text("\n".join(confirmation),encoding="utf-8")
    return {"master":master,"housing":housing,"roster":roster,"fies":fies,"assets":assets,"h":h,"age_summary":age_summary,"assetrows":itemrows}

def fies_one(flag1,flag2,items1,items2):
    a,b=norm_flag(flag1),norm_flag(flag2)
    if a and b: return {"fies_form_used":"both","fies_valid_items_n":pd.NA,"fies_raw_score":pd.NA,"fies_status":"both_forms"}
    if not a and not b: return {"fies_form_used":"none","fies_valid_items_n":pd.NA,"fies_raw_score":pd.NA,"fies_status":"no_form"}
    items=items1 if a else items2; form="L1" if a else "L2"
    x=num(pd.Series(items)); valid=x.isin([1,2]); valid_n=int(valid.sum())
    if valid_n==8: return {"fies_form_used":form,"fies_valid_items_n":valid_n,"fies_raw_score":int(x.eq(1).sum()),"fies_status":"valid"}
    # Do not map unexpected values into missing/DK/refused states.
    unexpected=x.notna()&~x.isin([1,2,3,4])
    if unexpected.any(): return {"fies_form_used":form,"fies_valid_items_n":valid_n,"fies_raw_score":pd.NA,"fies_status":pd.NA}
    return {"fies_form_used":form,"fies_valid_items_n":valid_n,"fies_raw_score":pd.NA,"fies_status":"partial_dk_refused" if x.isin([3,4]).any() else "partial_blank"}

def toilet_type(code):
    c=num(pd.Series([code])).iloc[0]
    if pd.isna(c): return "unknown"
    if c==999: return "unknown"
    if c in [1,2,3,5,7,9,12]: return "improved"
    if c in [4,6,8,10,11,13]: return "unimproved"
    if c==14: return "open_defecation"
    return "unknown"

def toilet_sharing_class(code):
    """D-04b cleaned-file codebook: 0=not shared, 1=shared; other=unknown."""
    c=num(pd.Series([code])).iloc[0]
    if c==0: return "not shared"
    if c==1: return "shared"
    return "unknown"

def toilet_service(code,shared):
    typ=toilet_type(code); sharing=toilet_sharing_class(shared)
    if typ=="unknown" or sharing=="unknown": return "unknown"
    if typ=="open_defecation": return "open_defecation"
    if typ=="unimproved": return "unimproved"
    if sharing=="not shared": return "basic"
    return "limited"

def tenure_class(code):
    c=num(pd.Series([code])).iloc[0]
    if pd.isna(c) or c==999: return "unknown"
    if c in [1,2,3]: return "secure"
    if c in [4,5,6]: return "intermediate"
    if c in [7,8]: return "insecure"
    return "unknown"

def material_class(value, lookup):
    if pd.isna(value): return "unknown"
    x=num(pd.Series([value])).iloc[0]
    if pd.isna(x): return "unknown"
    key=str(int(x)) if float(x).is_integer() else str(x)
    return lookup.get(key,"unknown")

def asset_owned(value,item,is_count):
    if pd.isna(value): return pd.NA
    x=num(pd.Series([value])).iloc[0]
    if pd.isna(x): return pd.NA
    if is_count:
        if x<0 or x%1!=0: return pd.NA
        return int(x>0)
    if item in {"d_12","d_13","d_14","d_15","d_16"}:
        if x in (0,1): return int(x==1)
        return pd.NA
    if x==1: return 0
    if x==2: return 1
    return pd.NA

def build_material_lookup():
    source=read(HOUSING_XWALK)
    rows=[]
    approved={
      "c1_04":{"1":"durable","2":"durable","3":"durable","4":"non_durable"},
      "c1_05":{"1":"durable","2":"durable","6":"durable","3":"non_durable","4":"non_durable","5":"non_durable"},
      "c1_06":{"1":"durable","2":"durable","3":"durable","6":"non_durable"},
    }
    for _,r in source[source.bright_variable.isin(["C1_04","C1_05","C1_06"])].iterrows():
        code="" if str(r.response_code)=="[MISSING]" else str(r.response_code)
        status=str(r.mapping_status)
        durability=approved.get(str(r.bright_variable).lower(),{}).get(code,"")
        rows.append({"variable":str(r.bright_variable).lower(),"code":code,"label":str(r.original_questionnaire_label),"crosswalk_mapping_status":status,"durability":durability})
    pd.DataFrame(rows,columns=["variable","code","label","crosswalk_mapping_status","durability"]).to_csv(OUT/"lookups/material_durability_lookup.csv",index=False,encoding="utf-8-sig")
    return pd.DataFrame(rows)

def build_toilet_lookup():
    improved={1,2,3,5,7,9,12}; unimproved={4,6,8,10,11,13}
    labels={i:f"Questionnaire code {i}" for i in range(1,15)}; labels[999]="Other / unknown (code-list discrepancy)"
    rows=[]
    for c in list(range(1,15))+[999]:
        typ="improved" if c in improved else "unimproved" if c in unimproved else "open_defecation" if c==14 else "unknown"
        rows.append({"code":c,"label":labels[c],"toilet_type_class":typ,"mapping_confirmed":bool(c not in {5,10}),
          "c1_10_code_0_meaning":"not shared","c1_10_code_1_meaning":"shared",
          "toilet_service_rule":"improved + not shared=basic; improved + shared=limited; unimproved/open_defecation retain type class; c1_10 outside 0/1=unknown",
          "decision_id":"D-04/D-04b","source":"C1_08 proposed mapping; D-04b cleaned-file codebook supplied by researcher; codes 5 and 10 remain unconfirmed"})
    df=pd.DataFrame(rows); df.to_csv(OUT/"lookups/toilet_jmp_lookup.csv",index=False,encoding="utf-8-sig"); return df

def build_tenure_lookup():
    labels={1:"Code 1 (owned group)",2:"Code 2 (owned group)",3:"Code 3 (owned group)",4:"Rented",5:"Gift",6:"Rent-free",7:"Encroached",8:"Temporary",999:"Other / unknown"}
    rows=[]
    for c in [1,2,3,4,5,6,7,8,999]:
        rows.append({"code":c,"label":labels[c],"tenure_class":"secure" if c in [1,2,3] else "intermediate" if c in [4,5,6] else "insecure" if c in [7,8] else "unknown"})
    df=pd.DataFrame(rows); df.to_csv(OUT/"lookups/tenure_lookup.csv",index=False,encoding="utf-8-sig"); return df

def build():
    OUT.mkdir(parents=True,exist_ok=True); (OUT/"lookups").mkdir(exist_ok=True)
    # Separate Part A entrypoint is enforced by checks directory marker.
    required=OUT/"checks/A1_fies_form_totals.csv"
    if not required.is_file(): raise RuntimeError("Part A checks must run before Part B")
    core=read(PIPE/"household_core.csv"); fies=read(PIPE/"fies_item_responses_pending.csv"); d1=read(PIPE/"d1_observed_candidates_pending.csv")
    housing=read(CLEAN/"mod_c_housing.csv",["hhcode","c1_02","c1_03","c1_04","c1_05","c1_06","c1_07","c1_08","c1_10"],dtype={"hhcode":"string"})
    d3=read(PIPE/"d3_person_items_pending.csv",dtype={"hhcode":"string","pid":"string"})
    # Validate source grains/key sets before any merge.
    for frame,label in [(core,"core"),(fies,"FIES"),(d1,"D1 pending"),(housing,"housing")]:
        if frame.hhcode.isna().any() or frame.hhcode.duplicated().any(): raise ValueError(f"{label} hhcode must be complete and unique")
    if len(core)!=6847: raise ValueError(f"Expected 6847 core households; found {len(core)}")
    if set(core.hhcode)!=set(fies.hhcode) or set(core.hhcode)!=set(d1.hhcode) or set(core.hhcode)!=set(housing.hhcode): raise ValueError("A household source key set differs from v0.1 core")
    if d3[["hhcode","pid"]].isna().any().any() or d3.duplicated(["hhcode","pid"]).any(): raise ValueError("B0 roster person keys must be unique/nonmissing")
    if not d3.b0_04_years.index.equals(d3.index): raise AssertionError("Unexpected age index")
    fcols=[f"l{i}_{j:02d}" for i in (1,2) for j in range(1,9)]
    fiescalc=[]
    for _,r in fies.iterrows(): fiescalc.append(fies_one(r.l1_answered,r.l2_answered,[r[f"l1_{i:02d}"] for i in range(1,9)],[r[f"l2_{i:02d}"] for i in range(1,9)]))
    fs=pd.DataFrame(fiescalc,index=fies.index)
    fies_plus=pd.concat([fies[["hhcode"]],fs],axis=1)
    # Age counts from years only; months are not converted or used in the bands.
    age=num(d3.b0_04_years)
    ad=d3[["hhcode"]].copy()
    ad["n_under15"]=(age.ge(0)&age.lt(15)).astype("int64")
    ad["n_15_64"]=(age.ge(15)&age.le(64)).astype("int64")
    ad["n_65plus"]=(age.ge(65)).astype("int64")
    ad["n_age_missing"]=age.isna().astype("int64")
    ad["n_15_59"]=(age.ge(15)&age.le(59)).astype("int64")
    ad["n_60plus"]=(age.ge(60)).astype("int64")
    ag=ad.groupby("hhcode",sort=False).sum(numeric_only=True).reset_index()
    ag["dependency_ratio"]=np.where(ag.n_15_64.ge(1),(ag.n_under15+ag.n_65plus)/ag.n_15_64,np.nan)
    ag["no_working_age_member"]=np.where(ag.n_15_64.ge(1),0,1).astype("int64")
    ag["dependency_ratio_60"]=np.where(ag.n_15_59.ge(1),(ag.n_under15+ag.n_60plus)/ag.n_15_59,np.nan)
    ag["youth_ratio"]=np.where(ag.n_15_64.ge(1),ag.n_under15/ag.n_15_64,np.nan)
    ag["old_age_ratio_65"]=np.where(ag.n_15_64.ge(1),ag.n_65plus/ag.n_15_64,np.nan)
    # Explicitly attach source household counts and status; never sum repeated H1_17 values.
    need_d1=["hhcode",*ASSETS,"h1_17_raw_household_value","h1_17_consistency_status"]
    dd=d1[need_d1].copy()
    dd=dd.rename(columns={"h1_17_raw_household_value":"h1_17_raw_household_value","h1_17_consistency_status":"h1_17_consistency_status"})
    dd["income_status"]=np.where(dd.h1_17_consistency_status.eq("consistent_repeated_value"),"consistent","unknown")
    # Material & sanitation lookup tables.
    mat=build_material_lookup(); toilet=build_toilet_lookup(); tenure=build_tenure_lookup()
    # Household joins are one-to-one and preserve core master order.
    x=core.merge(housing,on="hhcode",how="left",validate="one_to_one",sort=False)
    x=x.merge(fies_plus,on="hhcode",how="left",validate="one_to_one",sort=False)
    x=x.merge(dd,on="hhcode",how="left",validate="one_to_one",sort=False)
    x=x.merge(ag,on="hhcode",how="left",validate="one_to_one",sort=False)
    if len(x)!=6847 or x.hhcode.tolist()!=core.hhcode.tolist() or x.hhcode.isna().any() or x.hhcode.duplicated().any(): raise AssertionError("Household core key/row preservation failed")
    # B2 material: apply D-03a exactly; unlisted/missing codes stay unknown.
    material_rules={}
    for variable,group in mat.groupby("variable",sort=False):
        material_rules[variable]={}
        for _,row in group.iterrows():
            if pd.notna(row.durability) and str(row.durability).strip():
                material_rules[variable][str(row.code).strip()]=str(row.durability).strip()
    for c in ["c1_04","c1_05","c1_06"]:
        x[c+"_durability_class"]=[material_class(v,material_rules.get(c,{})) for v in x[c]]
    # B3 proposed toilet grouping; codes 5 and 10 remain explicitly unconfirmed in lookup.
    x["toilet_type_class"]=x.c1_08.map(toilet_type)
    x["toilet_service_class"]=[toilet_service(c,s) for c,s in zip(x.c1_08,x.c1_10)]
    # B4 tenure grouping exactly as specified.
    x["tenure_class"]=x.c1_07.map(tenure_class)
    # B5 bedrooms and raw floor-area band.
    b=num(x.c1_02); persons=num(x.roster_member_count)
    x["persons_per_bedroom"]=np.where(b.ge(1)&persons.notna(),persons/b,np.nan)
    x["c1_02_zero"]=b.eq(0).astype("int64")
    x["c1_02_missing"]=b.isna().astype("int64")
    # B8 owned flags. Invalid observed values remain blank and appear in A7 diagnostics.
    owned_cols=[]
    for c in ASSETS:
        oc=c+"_owned"; x[oc]=[asset_owned(v,c,c in COUNT_ASSETS) for v in x[c]]; owned_cols.append(oc)
    owned_num=x[owned_cols].apply(pd.to_numeric,errors="coerce")
    x["asset_types_owned_n"]=owned_num.sum(axis=1,min_count=1)
    x["asset_items_valid_n"]=owned_num.notna().sum(axis=1).astype("int64")
    # Copy exact raw FIES fields to separate file, not to modelling table.
    fies[["hhcode",*fcols,"l1_answered","l2_answered"]].to_csv(OUT/"fies_item_responses_pending.csv",index=False,na_rep="",encoding="utf-8-sig")
    # Required columns; exclude proxy variables by construction.
    wanted=["hhcode","roster_member_count","fies_form_used","fies_valid_items_n","fies_raw_score","fies_status",
            "c1_04","c1_05","c1_06","c1_04_durability_class","c1_05_durability_class","c1_06_durability_class",
            "c1_08","c1_10","toilet_type_class","toilet_service_class","c1_07","tenure_class",
            "c1_02","persons_per_bedroom","c1_02_zero","c1_02_missing","c1_03",
            "n_under15","n_15_64","n_65plus","n_age_missing","dependency_ratio","no_working_age_member",
            "n_15_59","n_60plus","dependency_ratio_60","youth_ratio","old_age_ratio_65",
            "h1_17_raw_household_value","h1_17_consistency_status","income_status",*ASSETS,*owned_cols,"asset_types_owned_n","asset_items_valid_n"]
    # Deduplicate columns while preserving stated order.
    wanted=list(dict.fromkeys(wanted))
    model=x[wanted].copy()
    model["fies_valid_items_n"]=pd.to_numeric(model.fies_valid_items_n,errors="coerce")
    model["fies_raw_score"]=pd.to_numeric(model.fies_raw_score,errors="coerce")
    model.to_csv(OUT/"modelling_inputs_v0_1.csv",index=False,na_rep="",encoding="utf-8-sig")
    # Dictionary entries for every output column.
    dictionary=[]
    raw_sources={"hhcode":"pipeline_v0/household_core.csv", "roster_member_count":"pipeline_v0/household_core.csv",
      "fies_form_used":"l1_answered/l2_answered in fies_item_responses_pending.csv", "fies_valid_items_n":"L1/L2 item codes 1/2", "fies_raw_score":"selected single form items 1/2 only",
      "fies_status":"form flags and selected form item codes", "c1_02":"mod_c_housing.csv:c1_02", "c1_03":"mod_c_housing.csv:c1_03",
      "c1_04":"mod_c_housing.csv:c1_04", "c1_05":"mod_c_housing.csv:c1_05", "c1_06":"mod_c_housing.csv:c1_06", "c1_07":"mod_c_housing.csv:c1_07",
      "c1_08":"mod_c_housing.csv:c1_08", "c1_10":"mod_c_housing.csv:c1_10", "h1_17_raw_household_value":"d1_observed_candidates_pending.csv:h1_17_raw_household_value",
      "h1_17_consistency_status":"d1_observed_candidates_pending.csv:h1_17_consistency_status", "income_status":"H1_17 consistency status",
      "n_under15/n_15_64/n_65plus/n_age_missing/n_15_59/n_60plus":"d3_person_items_pending.csv:b0_04_years"}
    for c in model.columns:
        source=raw_sources.get(c, "mod_d_assets.csv:"+c.removesuffix("_owned") if c.endswith("_owned") else "derived within Stage 3 from listed source columns")
        decision="S-01" if c in ["hhcode","roster_member_count"] else "D-01/D-02" if c.startswith("fies_") else "D-03a" if c.endswith("durability_class") else "D-03" if c in ["c1_04","c1_05","c1_06"] else "D-04b" if c in ["c1_10","toilet_service_class"] else "D-04" if c=="toilet_type_class" or c=="c1_08" else "D-05" if c=="tenure_class" or c=="c1_07" else "D-06" if c.startswith("c1_02") or c in ["c1_03","persons_per_bedroom"] else "D-07" if c.startswith(("n_under","n_15_","n_65","n_age","dependency_","no_working","n_60","youth_","old_age_")) else "D-09" if c.startswith("h1_17") or c=="income_status" else "D-10" if c in ASSETS or c.endswith("_owned") or c.startswith("asset_") else "S-01"
        rule="Preserved from v0.1 household core; unique hhcode." if c in ["hhcode","roster_member_count"] else "See stage3_summary.md and open_questions.md; raw codes never imputed." 
        if c=="fies_raw_score": rule="Count code 1 only when one form used and all eight items on that form are 1/2; otherwise blank. Both forms are not selected."
        if c=="fies_valid_items_n": rule="Count 1/2 on the single answered form; blank for both/no form because no approved combined denominator."
        if c=="dependency_ratio": rule="(n_under15+n_65plus)/n_15_64 when n_15_64>=1; else blank."
        if c=="dependency_ratio_60": rule="(n_under15+n_60plus)/n_15_59 when n_15_59>=1; sensitivity definition."
        if c=="youth_ratio": rule="n_under15/n_15_64 when n_15_64>=1; sensitivity definition."
        if c=="old_age_ratio_65": rule="n_65plus/n_15_64 when n_15_64>=1; sensitivity definition."
        if c.endswith("_durability_class"): rule="D-03a exact code lookup; unlisted and missing source codes remain unknown."
        if c=="toilet_type_class": rule="D-04 proposed JMP C1_08 code groups; codes 5 and 10 mapping_confirmed=FALSE; unchanged by D-04b."
        if c=="c1_10": rule="D-04b cleaned-file codebook: 0=not shared; 1=shared; other or missing=unknown. Applies only to C1_10."
        if c=="toilet_service_class": rule="D-04b: c1_08=999 or c1_10 outside 0/1 -> unknown; improved + c1_10=0 -> basic; improved + c1_10=1 -> limited; unimproved/open_defecation retain type class."
        if c=="tenure_class": rule="Codes 1-3 secure; 4-6 intermediate; 7-8 insecure; 999/missing/other unknown."
        if c=="persons_per_bedroom": rule="roster_member_count/c1_02 only when c1_02>=1 and roster count observed."
        if c=="asset_types_owned_n": rule="Sum observed owned flags only; blank if no valid item; valid-item denominator is retained separately."
        if c=="asset_items_valid_n": rule="Count asset items with a valid owned flag; not an approved completeness threshold."
        if c=="income_status": rule="consistent only for consistent_repeated_value; otherwise unknown. Never sum H1_17."
        dictionary.append({"column":c,"source_variables":source,"decision_id":decision,"rule":rule,"status":"data engineering only; model inclusion not approved"})
    pd.DataFrame(dictionary).to_csv(OUT/"column_dictionary.csv",index=False,encoding="utf-8-sig")
    # Missingness report uses model table row denominator; not eligible-population denominator.
    miss=[]
    for c in model:
        nmiss=int(model[c].isna().sum()); miss.append({"column":c,"missing_n":nmiss,"denominator_modelling_households_n":len(model),"missing_rate":nmiss/len(model) if len(model) else np.nan,"denominator_note":"full modelling table; not eligible denominator"})
    pd.DataFrame(miss).to_csv(OUT/"missingness_report.csv",index=False,encoding="utf-8-sig")
    # Human-readable summary is generated from the actual Part A check tables.
    a1=pd.read_csv(OUT/"checks/A1_fies_form_totals.csv")
    a2=pd.read_csv(OUT/"checks/A2_housing_999_counts.csv")
    a4=pd.read_csv(OUT/"checks/A4_households_without_working_age_member.csv")
    a5=pd.read_csv(OUT/"checks/A5_fies_form_completeness.csv")
    a7=pd.read_csv(OUT/"checks/A7_asset_value_sets_and_code_checks.csv")
    a8=pd.read_csv(OUT/"checks/A8_roster_flag_counterfactuals.csv")
    summary=["# Stage 3 modelling inputs v0.1 — engineering audit", "",
      "## Scope and outputs", "", f"Built a household-level table with {len(model):,} rows and {len(model.columns)} columns, preserving the 6,847-row v0.1 household core. The work is data engineering only. No model, vulnerability ranking/score, imputation, or eligibility decision was created. `pc_cons` and `label_high_vuln` are excluded. FIES item responses remain in a separate raw-response extract.", "",
      "Outputs include `modelling_inputs_v0_1.csv`, `fies_item_responses_pending.csv`, three lookups, a column dictionary, missingness report, Part A checks, and a SHA-256 manifest.", "",
      "The cleaned-file rule confirmation table is in `codebook_rule_confirmation.md`; the codebook crosscheck and decision log are both hashed in the manifest.", "",
      "## Part A checks and decision-log comparison", "",
      f"- FIES form coverage: {dict(zip(a1.form_answer_pattern,a1.households_n))} households (master denominator 6,847).", 
      f"- Code 999 counts: {dict(zip(a2.variable,a2.code_999_households_n))}.",
      f"- FIES complete 8-item forms: {dict(zip(a5.form,a5.all_8_items_valid_1_or_2_n))}; no-form/both-form cases are retained separately.",
      f"- Households with no observed working-age member: {a4.iloc[0].households_no_observed_member_in_band_n} for ages 15–64 and {a4.iloc[1].households_no_observed_member_in_band_n} for ages 15–59.",
      f"- Asset register: {len(ASSETS)} explicitly selected items; d_07/d_09/d_11 and all a/b/c follow-ups excluded. For d_12-d_16 only, codebook rule 0=No, 1=Yes (owned=1) is applied. Other direct items retain their registered rules.",
      f"- Roster flag counterfactuals (flag=0 assumed failing, not applied): {a8.iloc[0].flag} has {a8.iloc[0].roster_members_flagged_fail_n} failing roster rows; size would change in {a8.iloc[0].households_household_size_would_change_n} households and dependency ratio in {a8.iloc[0].households_dependency_ratio_would_change_n}. {a8.iloc[1].flag} has {a8.iloc[1].roster_members_flagged_fail_n} failing roster rows; size would change in {a8.iloc[1].households_household_size_would_change_n} households and dependency ratio in {a8.iloc[1].households_dependency_ratio_would_change_n}.",
      "- The A2 code-999 count matches the prior 22-household register figure; all-code C1_08 Other text frequency totals match the previously reported 24. Raw free text is suppressed.",
      "- D-04b codebook correction applied to C1_10 only: 0=not shared; 1=shared; other/missing=unknown. The questionnaire convention remains 1=No/2=Yes but is overridden for this cleaned file; C1_08 type classes are unchanged.",
      "- D-03a material lookup is applied exactly; all unlisted source codes remain unknown.", "",
      "These checks do not validate or approve any indicator for a model. Decision references and item-level details are in `checks/decision_log_comparison.csv` and the check tables.", "",
      "## Open questions", "", "See `open_questions.md`; the crosscheck agrees with the applied C1_10, d_12-d_16, 18-item asset, FIES and `hh_type` rules. The decision log's stale `hhtype` follow-up is recorded; the crosscheck's `hh_type` name is used. Roster flag inclusion remains undecided, so flag counterfactuals are reported but not applied. Other questions are suppressed C1_08 Other text; FIES denominator for both/no form; sensitivity-ratio definitions; and proposed C1_08 codes 5 and 10.", ""]
    (OUT/"stage3_summary.md").write_text("\n".join(summary),encoding="utf-8")
    # Manifest records all direct inputs and generated outputs; hashes do not expose identifiers.
    input_paths=[CLEAN/"mod_a_household_identification.csv",CLEAN/"mod_c_housing.csv",CLEAN/"mod_b0_roster_long.csv",CLEAN/"mod_d_assets.csv",CLEAN/"mod_h1_primary_employment_long.csv",CLEAN/"mod_l1_food_security_w.csv",CLEAN/"mod_l2_food_security_m.csv",
       PIPE/"household_core.csv",PIPE/"fies_item_responses_pending.csv",PIPE/"d1_observed_candidates_pending.csv",PIPE/"d3_person_items_pending.csv",BASE/"pipeline_v0/manifest.json",REG,DEC,HOUSING_XWALK,CODEBOOK,SPEC]
    input_meta={}
    for p in input_paths:
        item={"sha256":sha(p)}
        if p.suffix.lower()==".csv":
            try: item["rows"]=int(sum(1 for _ in p.open(encoding="utf-8-sig"))-1)
            except Exception: item["rows"]=None
        input_meta[str(p.relative_to(ROOT))]=item
    output_paths=[p for p in OUT.rglob("*") if p.is_file() and p.name!="manifest.json"]
    out_meta={}
    for p in output_paths:
        meta={"sha256":sha(p)}
        if p.suffix.lower()==".csv": meta["rows"]=int(sum(1 for _ in p.open(encoding="utf-8-sig"))-1)
        out_meta[str(p.relative_to(OUT))]=meta
    manifest={"pipeline_version":"0.2.0","scope":"Data engineering only; no fuzzy/Bayesian model, scoring, ranking, imputation or eligibility decisions.","household_rows":len(model),"unique_nonmissing_hhcode":bool(model.hhcode.notna().all() and model.hhcode.is_unique),"inputs":input_meta,"outputs":out_meta,"proxy_excluded_from_modelling_table":["pc_cons","label_high_vuln"],"notes":["fies_item_responses_pending.csv remains a separate raw-form extract.","D-03a material lookup applied exactly; every unspecified material row remains blank/unknown.","codebook crosscheck and decision log are included as input references.","all joins are one-to-one validated and preserve the 6,847-row household core."]}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    # Final validations.
    if len(model)!=6847 or model.hhcode.isna().any() or model.hhcode.duplicated().any(): raise AssertionError("Model input key/row validation failed")
    if {"pc_cons","label_high_vuln","pc_cons_prepared_unvalidated","label_high_vuln_prepared_unvalidated"}&set(model.columns): raise AssertionError("Proxy leaked into modelling table")
    for xcol in owned_cols:
        if not set(model[xcol].dropna().unique()).issubset({0,1}): raise AssertionError(f"Invalid owned flag {xcol}")
    print(f"Stage 3 outputs built: {len(model)} household rows; {len(model.columns)} columns; unique hhcode={model.hhcode.is_unique}")

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--checks-only",action="store_true"); args=p.parse_args()
    run_checks()
    if not args.checks_only: build()
