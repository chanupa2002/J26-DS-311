"""Research output - not an eligibility determination.

Build the v0.2 fuzzy leaves approved in decision-log Section 9. Does not build
the Bayesian Network or any O1 composite beyond approved mean severity.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'component1_audit'
OUT=BASE/'outputs'/'stage4b'
SENS=OUT/'sensitivity_v0_2'
S3=BASE/'outputs'/'stage3'
S3B=BASE/'outputs'/'stage3b'
S4=BASE/'outputs'/'stage4'
ADDENDUM=BASE/'docs'/'decision_log_section9_addendum (1).md'
ENGINE_DIR=BASE/'fuzzy_engine'
sys.path.insert(0,str(ENGINE_DIR)); sys.path.insert(0,str(S4))
import fuzzy_v0_1 as engine
from fuzzy_adapter import adapt, LABEL

STAGE3=S3/'modelling_inputs_v0_1.csv'
STAGE3B=S3B/'modelling_inputs_v0_2_additions.csv'
REF=S4/'reference_v0_1.json'

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def domain_mean(frame, columns):
    """Available-input mean and exact used-input count; all unknown remains unknown."""
    block=frame[columns].apply(pd.to_numeric,errors='coerce')
    return block.mean(axis=1,skipna=True).where(block.notna().any(axis=1)),block.notna().sum(axis=1)

def domain_max(frame, columns):
    """Available-input maximum; all unknown remains unknown."""
    block=frame[columns].apply(pd.to_numeric,errors='coerce')
    return block.max(axis=1,skipna=True).where(block.notna().any(axis=1)),block.notna().sum(axis=1)

def deprivation_binary(series, deprived_value):
    """Map a valid binary answer to deprivation direction, retaining invalids as NaN."""
    s=pd.to_numeric(pd.Series(series),errors='coerce')
    return s.map({0.0:float(deprived_value==0),1.0:float(deprived_value==1)}).astype(float)

def _load_refs():
    obj=json.loads(REF.read_text(encoding='utf-8'))
    if obj.get('model_version')!=engine.MODEL_VERSION: raise ValueError('Frozen Stage 4 model version mismatch')
    return {k:engine.Reference.from_json(json.dumps({'sorted':v})) for k,v in obj['references'].items()}

def _soft_add(frame, domain):
    soft=engine.soft_levels(frame[f'dom_{domain}'])
    for name in ['low','medium','high']: frame[f'soft_{domain}_{name}']=soft[name].to_numpy()

def main():
    OUT.mkdir(parents=True,exist_ok=True); SENS.mkdir(parents=True,exist_ok=True)
    s3=pd.read_csv(STAGE3,dtype={'hhcode':'string'},low_memory=False)
    s3b=pd.read_csv(STAGE3B,dtype={'hhcode':'string'},low_memory=False)
    if len(s3)!=6847 or s3.hhcode.isna().any() or s3.hhcode.duplicated().any(): raise ValueError('Stage 3 spine must contain 6,847 unique households')
    if len(s3b)!=6847 or s3b.hhcode.isna().any() or s3b.hhcode.duplicated().any(): raise ValueError('Stage 3b additions must contain 6,847 unique households')
    if {'label_high_vuln','pc_cons'} & (set(s3.columns)|set(s3b.columns)): raise ValueError('Forbidden proxy field in fuzzy input')
    d=s3.merge(s3b,on='hhcode',how='left',validate='one_to_one',suffixes=('','_stage3b'))
    engine_input,_=adapt(s3)
    refs=_load_refs()
    engine.MIN_VALID_ASSETS=18  # D-10a; no engine source file/default is modified.
    old=engine.score_households(engine_input.drop(columns='hhcode'),refs)
    out=pd.DataFrame({'research_label':LABEL,'hhcode':s3.hhcode})
    for c in old.columns: out[c]=old[c].to_numpy()
    # Approved 9.7 financial directions: bank no=deprived; debt yes=deprived.
    bank=pd.to_numeric(d.bank_account,errors='coerce')
    debt=pd.to_numeric(d.has_debt,errors='coerce')
    out['mu_bank_account']=deprivation_binary(bank,0).to_numpy()
    out['mu_has_debt']=deprivation_binary(debt,1).to_numpy()
    # H-01: the observed share is already on [0,1]; missing B3 denominator remains unknown.
    health=pd.to_numeric(d.share_chronic,errors='coerce')
    if ((health.dropna()<0)|(health.dropna()>1)).any(): raise ValueError('share_chronic outside [0,1]')
    out['mu_health']=health.to_numpy()
    out['health_status']=d.health_status.astype('string').fillna('missing').to_numpy()
    shock=pd.to_numeric(d.o1_mean_severity,errors='coerce')
    if ((shock.dropna()<0)|(shock.dropna()>1)).any(): raise ValueError('O1 mean severity outside [0,1]')
    out['mu_shock']=shock.to_numpy()
    out['n_o1_items_valid']=pd.to_numeric(d.n_o1_items_valid,errors='coerce').to_numpy()
    out['dom_shelter_quality'],out['dom_shelter_quality_n_used']=domain_mean(out,['mu_wall','mu_floor','mu_roof'])
    out['dom_shelter_quality_n_total']=3
    out['dom_sanitation']=pd.to_numeric(out.mu_toilet,errors='coerce')
    out['dom_sanitation_n_used']=out.dom_sanitation.notna().astype(int); out['dom_sanitation_n_total']=1
    out['dom_crowding_tenure'],out['dom_crowding_tenure_n_used']=domain_mean(out,['mu_crowding','mu_tenure'])
    out['dom_crowding_tenure_n_total']=2
    out['dom_financial_resilience'],out['dom_financial_resilience_n_used']=domain_mean(out,['mu_bank_account','mu_has_debt'])
    out['dom_financial_resilience_n_total']=2
    out['dom_health']=out.mu_health
    out['dom_health_n_used']=out.mu_health.notna().astype(int); out['dom_health_n_total']=1
    out['dom_exposure']=out.mu_shock
    out['dom_exposure_n_used']=out.n_o1_items_valid.fillna(0).astype(int); out['dom_exposure_n_total']=20
    # Preserve every O1 raw answer alongside the approved mean-severity input.
    o1cols=[f'o1_01_{i}' for i in range(1,21)]
    for c in o1cols: out[c]=d[c].to_numpy() if c in d else np.nan
    # Soft evidence for the v0.2 fuzzy leaves; higher state means more deprivation.
    soft_domains=['shelter_quality','sanitation','crowding_tenure','economic','food','demographic','health','financial_resilience','exposure']
    for dom in soft_domains: _soft_add(out,dom)
    scorefile=OUT/'fuzzy_scores_v0_2.csv'
    out.to_csv(scorefile,index=False,na_rep='',encoding='utf-8-sig')

    # Aggregate coverage and n_used distributions; no identifiers.
    report_domains={'legacy_housing':'dom_housing','economic':'dom_economic','food':'dom_food','demographic':'dom_demographic',
       'shelter_quality':'dom_shelter_quality','sanitation':'dom_sanitation','crowding_tenure':'dom_crowding_tenure',
       'health':'dom_health','financial_resilience':'dom_financial_resilience','exposure':'dom_exposure'}
    rows=[]
    for label,col in report_domains.items():
        ncol=f'{col}_n_used'; counts=out[ncol].value_counts().sort_index()
        rows.append({'research_label':LABEL,'domain_or_leaf':label,'known_degree_n':int(out[col].notna().sum()),'unknown_degree_n':int(out[col].isna().sum()),
           'n_used_distribution':'; '.join(f'{int(k)}:{int(v)}' for k,v in counts.items()),'n_total':int(out[f'{col}_n_total'].iloc[0])})
    pd.DataFrame(rows).to_csv(OUT/'domain_coverage_v0_2.csv',index=False,encoding='utf-8-sig')
    # Sensitivity scores: compare each named alternative with its primary subdomain.
    sens=[]
    def write_sensitivity(name, base_col, alt, n_used, n_total, note):
        base=pd.to_numeric(out[base_col],errors='coerce'); alt=pd.to_numeric(alt,errors='coerce')
        valid=base.notna()&alt.notna()
        rho=float(spearmanr(base[valid],alt[valid]).statistic) if valid.sum()>1 else np.nan
        delta=(alt[valid]-base[valid]).abs()
        frame=pd.DataFrame({'research_label':LABEL,'hhcode':out.hhcode,'baseline_degree':base,'sensitivity_degree':alt,
             'baseline_n_used':out[f'{base_col}_n_used'],'sensitivity_n_used':n_used,'sensitivity_n_total':n_total})
        frame.to_csv(SENS/f'{name}.csv',index=False,na_rep='',encoding='utf-8-sig')
        sens.append({'research_label':LABEL,'scenario':name,'subdomain':base_col.removeprefix('dom_'),'description':note,
             'spearman_vs_primary':rho,'comparison_n':int(valid.sum()),'mean_absolute_degree_change':float(delta.mean()) if len(delta) else np.nan,
             'changed_degree_n':int(delta.gt(0).sum()),'changed_degree_share':float(delta.gt(0).mean()) if len(delta) else np.nan})
    # Exclude each financial leaf; direction-reversal is also tested.
    write_sensitivity('financial_exclude_N01','dom_financial_resilience',out.mu_has_debt,out.mu_has_debt.notna().astype(int),1,'Exclude bank_account (N-01); debt only.')
    write_sensitivity('financial_exclude_N02','dom_financial_resilience',out.mu_bank_account,out.mu_bank_account.notna().astype(int),1,'Exclude has_debt (N-02); bank account only.')
    reverse_debt=1.0-out.mu_has_debt
    rev_mean,rev_n=domain_mean(pd.DataFrame({'bank':out.mu_bank_account,'debt_reversed':reverse_debt}),['bank','debt_reversed'])
    write_sensitivity('financial_reverse_N02','dom_financial_resilience',rev_mean,rev_n,2,'Reverse N-02 direction; debt no=deprived, yes=not deprived.')
    any_chronic=pd.to_numeric(d.n_chronic,errors='coerce').gt(0).astype(float).where(out.mu_health.notna())
    write_sensitivity('health_any_chronic_binary','dom_health',any_chronic,any_chronic.notna().astype(int),1,'Any chronic member binary; unknown when no valid B3 member.')
    shelter_max,shelter_n=domain_max(out,['mu_wall','mu_floor','mu_roof'])
    write_sensitivity('shelter_quality_max','dom_shelter_quality',shelter_max,shelter_n,3,'Replace the approved within-shelter mean with maximum.')
    ct_max,ct_n=domain_max(out,['mu_crowding','mu_tenure'])
    write_sensitivity('crowding_tenure_max','dom_crowding_tenure',ct_max,ct_n,2,'Replace the approved crowding/tenure mean with maximum.')
    pd.DataFrame(sens).to_csv(OUT/'sensitivity_comparison_v0_2.csv',index=False,encoding='utf-8-sig')

    hstatus=d.health_status.fillna('missing').value_counts()
    o1valid=pd.to_numeric(d.n_o1_items_valid,errors='coerce')
    n1tab=pd.read_csv(S3B/'checks'/'n1_0_by_any_source_flag.csv')
    agreement=int(n1tab.loc[(n1tab.n1_0.astype(str).eq('0')),'no source flag = 1'].sum()+n1tab.loc[(n1tab.n1_0.astype(str).eq('1')),'any source flag = 1'].sum())
    total=int(n1tab.loc[n1tab.n1_0.astype(str).isin(['0','1']),['any source flag = 1','no source flag = 1']].to_numpy().sum())
    questions=[
      'User assumption: all 20 O1 items refer to the past 12 months (item 20 states this explicitly; items 1-19 are covered by the assumption). Approved mean severity maps 1 severe=1, 2 moderate=0.5, 3 none=0 and averages valid answers only; no valid answers remains unknown.',
      f"H-01 uses b3_01-derived share_chronic. B3 status counts are valid={int(hstatus.get('valid',0))}, partial={int(hstatus.get('partial',0))}, missing={int(hstatus.get('missing',0))}; partial-coverage shares are included and flagged, as permitted by 9.6.",
      'N-02 has-debt direction follows the approved researcher judgement (yes=deprivation); exclusion and reversal sensitivities are reported.',
      'O2 coping remains conditional because code handling for 3, 4, 997 is unresolved. L3 energy and L5 water remain candidate-only pending evidence and scale/skip review; P wellbeing is descriptive only; livelihood remains deferred.',
      'This run produces fuzzy leaf memberships and domain degrees only. The hierarchical Bayesian Network in M-06/M-07, its CPTs, priors, and sensitivity runs have not been calculated here.',
      'Stage 4 v0.1 frozen income, asset and dependency references are reused. D-10a masks asset membership unless all 18 items are valid; current Stage 3 has all 18 valid for every household.',
      'A domain degree is the available-input mean; missing inputs remain unknown and are excluded from n_used. No cross-domain composite, overall vulnerability score, or ranking is produced.'
    ]
    (OUT/'open_questions_v0_2.md').write_text('# Stage 4b v0.2 open questions\n\n'+LABEL+'\n\n'+'\n'.join(f'- {q}' for q in questions)+'\n',encoding='utf-8')
    cmp=pd.DataFrame(sens)
    summary=['# Stage 4b v0.2 fuzzy integration','',LABEL,'',
      f'- Scored {len(out):,} unique households. D-10a all-18-valid is applied; current valid count is {int(pd.to_numeric(s3.asset_items_valid_n,errors="coerce").eq(18).sum()):,}/{len(s3):,}.',
      '- Integrated approved fuzzy leaves: exposure, legacy housing (for reference), economic, food, demographic, shelter quality, sanitation, crowding and tenure, health, and financial resilience.',
      '- Housing split uses the addendum rule: shelter=mean wall/floor/roof, sanitation=toilet, crowding/tenure=mean crowding/tenure. N-01 bank no and N-02 debt yes map to deprivation 1.',
      f'- N-01/N-02 flag agreement check: {agreement}/{total} household codes agree with the source-flag cross-tab.',
      f'- Health coverage status: valid {int(hstatus.get("valid",0)):,}; partial {int(hstatus.get("partial",0)):,}; missing {int(hstatus.get("missing",0)):,}.',
      f'- O1 all-20-valid households: {int(o1valid.eq(20).sum()):,}; all-20 validity is not required for the mean. User assumption applies the past-12-month period to all 20 items. Raw responses, valid-item count, and exposure mean severity are carried; no valid items yields unknown.',
      '- Domain coverage and n_used: `domain_coverage_v0_2.csv`. Sensitivity score comparisons: `sensitivity_comparison_v0_2.csv` and `sensitivity_v0_2/`.',
      '- This is a fuzzy-layer integration only. No Bayesian Network, CPT, vulnerability node, overall score, or ranking was produced.',
      '', '## Sensitivity results','', '| Scenario | Spearman vs primary | N | Mean absolute degree change | Changed N / share |','|---|---:|---:|---:|---:|']
    for _,r in cmp.iterrows(): summary.append(f"| {r.scenario} | {r.spearman_vs_primary:.6f} | {r.comparison_n} | {r.mean_absolute_degree_change:.6f} | {r.changed_degree_n} / {r.changed_degree_share:.3%} |")
    summary+=['','## Domain coverage','', '| Leaf/domain | Degree known | Degree unknown | n_used distribution |','|---|---:|---:|---|']
    for r in rows: summary.append(f"| {r['domain_or_leaf']} | {r['known_degree_n']} | {r['unknown_degree_n']} | {r['n_used_distribution']} |")
    summary+=['','## Open questions','']+[f'- {q}' for q in questions]
    (OUT/'stage4b_v0_2_summary.md').write_text('\n'.join(summary)+'\n',encoding='utf-8')

    input_paths=[STAGE3,STAGE3B,REF,ADDENDUM,ENGINE_DIR/'fuzzy_v0_1.py',S4/'fuzzy_adapter.py',S3B/'checks'/'n1_0_by_any_source_flag.csv',S3B/'checks'/'o1_all_items_valid.csv']
    inmeta=[]
    for p in input_paths:
      n=sum(1 for _ in p.open(encoding='utf-8-sig'))-1 if p.suffix.lower()=='.csv' else None
      inmeta.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'row_count':n})
    outpaths=[scorefile,OUT/'domain_coverage_v0_2.csv',OUT/'sensitivity_comparison_v0_2.csv',OUT/'open_questions_v0_2.md',OUT/'stage4b_v0_2_summary.md']+sorted(SENS.glob('*.csv'))
    manifest={'research_label':LABEL,'pipeline_version':'stage4b-v0.2.1','model_version':engine.MODEL_VERSION,
      'decision_source':str(ADDENDUM.relative_to(ROOT)),'asset_rule':'D-10a: all 18 asset items valid','inputs':inmeta,
      'outputs':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p),'row_count':sum(1 for _ in p.open(encoding='utf-8-sig'))-1 if p.suffix.lower()=='.csv' else None} for p in outpaths],
      'notes':['No proxy variables used.','No Bayesian Network or shock composite calculated.','CSV household-level outputs are ignored by .gitignore.']}
    (OUT/'manifest_v0_2.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Stage 4b v0.2 built for {len(out)} households; {len(sens)} sensitivity scenarios; O1 mean severity scored from valid answers.')

if __name__=='__main__': main()
