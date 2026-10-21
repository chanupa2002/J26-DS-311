"""Research output - not an eligibility determination.

Read-only diagnostics over the existing Stage 3 and Stage 4 files. New files are
written only under outputs/stage4b. No approved rule or engine default is changed.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'component1_audit'
OUT=BASE/'outputs'/'stage4b'
STAGE3=BASE/'outputs'/'stage3'
STAGE4=BASE/'outputs'/'stage4'
DATA=ROOT/'Data'/'processed'/'clean'
ENGINE_DIR=BASE/'fuzzy_engine'
sys.path.insert(0,str(ENGINE_DIR)); sys.path.insert(0,str(STAGE4))
import fuzzy_v0_1 as engine
from fuzzy_adapter import adapt, LABEL

STAGE3_FILE=STAGE3/'modelling_inputs_v0_1.csv'
FIES_FILE=STAGE3/'fies_item_responses_pending.csv'
HH_FILE=DATA/'mod_a_household_identification.csv'
SCORES=STAGE4/'fuzzy_scores_v0_1.csv'
REF_FILE=STAGE4/'reference_v0_1.json'
SENS=STAGE4/'sensitivity'

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def save_csv(frame,path):
    df=frame.copy()
    if 'research_label' not in df: df.insert(0,'research_label',LABEL)
    df.to_csv(path,index=False,na_rep='',encoding='utf-8-sig')

def complete_fies_score(items):
    vals=pd.to_numeric(pd.Series(items),errors='coerce')
    if len(vals)!=8 or not vals.isin([1,2]).all(): return np.nan
    return int(vals.eq(1).sum())

def fies_form_stats(items, form_name, hh_type, form_group):
    rows=[]
    for idx,col in enumerate(items,1):
        vals=pd.to_numeric(form_group[col],errors='coerce')
        valid=vals.isin([1,2]); endorsed=vals.eq(1)
        rows.append({'research_label':LABEL,'hh_type':hh_type,'form':form_name,'item':col,
                     'eligible_form_households':len(form_group),'valid_n':int(valid.sum()),
                     'unknown_or_out_of_set_n':int((~valid).sum()),'endorsed_1_n':int(endorsed.sum()),
                     'endorsement_rate':float(endorsed.sum()/valid.sum()) if valid.any() else np.nan})
    return rows

def rank_biserial_l1_vs_l2(l1,l2):
    a=pd.to_numeric(pd.Series(l1),errors='coerce').dropna().to_numpy(float)
    b=pd.to_numeric(pd.Series(l2),errors='coerce').dropna().to_numpy(float)
    if len(a)<1 or len(b)<1: return np.nan,np.nan,len(a),len(b)
    u=float(mannwhitneyu(a,b,alternative='two-sided',method='asymptotic').statistic)
    return u,2*u/(len(a)*len(b))-1,len(a),len(b)

def soft_level(degree):
    s=engine.soft_levels(pd.Series(degree))
    arr=s[['low','medium','high']].to_numpy(float)
    names=np.array(['low','medium','high'],dtype=object)
    return pd.Series(names[np.nanargmax(arr,axis=1)],index=s.index)

def load_refs():
    obj=json.loads(REF_FILE.read_text(encoding='utf-8'))
    if obj.get('model_version')!=engine.MODEL_VERSION: raise ValueError('Frozen reference model version mismatch')
    return {k:engine.Reference.from_json(json.dumps({'sorted':v})) for k,v in obj['references'].items()}

def fies_diagnostics(stage3):
    forms=pd.read_csv(FIES_FILE,dtype={'hhcode':'string'},low_memory=False)
    types=pd.read_csv(HH_FILE,usecols=['hhcode','hh_type'],dtype={'hhcode':'string'},low_memory=False)
    if types.hhcode.duplicated().any() or forms.hhcode.duplicated().any(): raise ValueError('FIES or household type keys are not unique')
    d=stage3[['hhcode']].merge(forms,on='hhcode',how='left',validate='one_to_one').merge(types,on='hhcode',how='left',validate='one_to_one')
    l1=[f'l1_{i:02d}' for i in range(1,9)]; l2=[f'l2_{i:02d}' for i in range(1,9)]
    missing=[c for c in l1+l2+['l1_answered','l2_answered','hh_type'] if c not in d]
    if missing: raise ValueError(f'Missing FIES diagnostic fields: {missing}')
    a=pd.to_numeric(d.l1_answered,errors='coerce').eq(1); b=pd.to_numeric(d.l2_answered,errors='coerce').eq(1)
    d['form_group']=np.select([a&~b,b&~a],['L1_only','L2_only'],default='both_or_neither')
    formrows=[]; itemrows=[]; tests=[]
    for ht in [1,2]:
        block=d[pd.to_numeric(d.hh_type,errors='coerce').eq(ht)]
        x=block[block.form_group.eq('L1_only')].copy(); y=block[block.form_group.eq('L2_only')].copy()
        x['raw_score']=x[l1].apply(complete_fies_score,axis=1); y['raw_score']=y[l2].apply(complete_fies_score,axis=1)
        for group,form,z in [('L1_only','L1',x),('L2_only','L2',y)]:
            q=pd.to_numeric(z.raw_score,errors='coerce').dropna()
            formrows.append({'research_label':LABEL,'hh_type':ht,'form_group':group,'households_n':len(z),'complete_8_item_score_n':len(q)})
            formrows[-1].update({'score_mean':float(q.mean()) if len(q) else np.nan,'score_median':float(q.median()) if len(q) else np.nan,
              'score_sd':float(q.std(ddof=1)) if len(q)>1 else np.nan,'share_score_0':float(q.eq(0).mean()) if len(q) else np.nan,
              'share_score_8':float(q.eq(8).mean()) if len(q) else np.nan})
        for form,cols,z in [('L1',l1,x),('L2',l2,y)]: itemrows.extend(fies_form_stats(cols,form,ht,z))
        u,r,n1,n2=rank_biserial_l1_vs_l2(x.raw_score,y.raw_score)
        tests.append({'research_label':LABEL,'hh_type':ht,'comparison':'L1-only vs L2-only complete raw score',
          'l1_complete_n':n1,'l2_complete_n':n2,'mann_whitney_u_l1':u,'two_sided_p':float(mannwhitneyu(x.raw_score.dropna(),y.raw_score.dropna(),alternative='two-sided',method='asymptotic').pvalue) if n1 and n2 else np.nan,
          'rank_biserial_l1_vs_l2':r,'rank_biserial_formula':'2*U_L1/(n_L1*n_L2)-1; positive means higher L1 ranks'})
    # Type 3 only uses L1; report per-item rates for context only.
    z=d[pd.to_numeric(d.hh_type,errors='coerce').eq(3)].copy(); z['raw_score']=z[l1].apply(complete_fies_score,axis=1)
    formrows.append({'research_label':LABEL,'hh_type':3,'form_group':'L1_only_context','households_n':len(z),'complete_8_item_score_n':int(z.raw_score.notna().sum())})
    itemrows.extend(fies_form_stats(l1,'L1',3,z))
    save_csv(pd.DataFrame(formrows),OUT/'fies_score_distributions.csv')
    save_csv(pd.DataFrame(itemrows),OUT/'fies_item_endorsement_rates.csv')
    save_csv(pd.DataFrame(tests),OUT/'fies_rank_tests.csv')
    save_csv(d.groupby(['hh_type','form_group'],dropna=False).size().rename('households_n').reset_index(),OUT/'fies_form_by_hh_type_counts.csv')
    return pd.DataFrame(formrows),pd.DataFrame(itemrows),pd.DataFrame(tests)

def housing_sensitivity(stage3,scores,refs):
    zero=pd.to_numeric(stage3.c1_02,errors='coerce').eq(0)
    size=pd.to_numeric(stage3.roster_member_count,errors='coerce')
    bedroom_dist=(pd.DataFrame({'household_size':size[zero]}).value_counts(dropna=False).rename('households_n').reset_index())
    save_csv(bedroom_dist,OUT/'zero_bedroom_household_size_distribution.csv')
    adapted,_=adapt(stage3)
    alt=adapted.drop(columns='hhcode').copy()
    alt.loc[zero,'persons_per_bedroom']=size[zero] # sensitivity: c1_02=0 -> 1 bedroom
    alt_score=engine.score_households(alt,refs)
    base=scores.set_index('hhcode'); new=alt_score.copy(); new['hhcode']=stage3.hhcode.to_numpy(); new=new.set_index('hhcode')
    doms=engine.soft_levels(base.dom_housing); doms.columns=[f'base_{c}' for c in doms]
    altlv=engine.soft_levels(new.dom_housing); altlv.columns=[f'alt_{c}' for c in altlv]
    comp=pd.DataFrame({'mu_crowding_before':base.mu_crowding,'mu_crowding_after':new.mu_crowding,
       'dom_housing_before':base.dom_housing,'dom_housing_after':new.dom_housing})
    comp['mu_crowding_change']=comp.mu_crowding_after-comp.mu_crowding_before
    comp['dom_housing_change']=comp.dom_housing_after-comp.dom_housing_before
    comp['housing_level_before']=soft_level(base.dom_housing); comp['housing_level_after']=soft_level(new.dom_housing)
    comp['housing_level_changed']=comp.housing_level_before.ne(comp.housing_level_after)
    groups={'zero_bedroom_households':zero.to_numpy(),'whole_file':np.ones(len(stage3),dtype=bool)}
    rows=[]
    for group,mask in groups.items():
        c=comp.iloc[np.where(mask)[0]]
        for var in ['mu_crowding_change','dom_housing_change']:
            before_col='mu_crowding_before' if var.startswith('mu_') else 'dom_housing_before'
            after_col='mu_crowding_after' if var.startswith('mu_') else 'dom_housing_after'
            before=c[before_col]; after=c[after_col]; paired=before.notna()&after.notna(); s=c.loc[paired,var].dropna(); after_known=after.dropna()
            rows.append({'research_label':LABEL,'sensitivity':'UNAPPROVED: c1_02=0 treated as 1 bedroom','group':group,'measure':var,
              'households_n':len(c),'baseline_known_n':int(before.notna().sum()),'sensitivity_known_n':int(after.notna().sum()),
              'unknown_to_known_n':int((before.isna()&after.notna()).sum()),'known_to_unknown_n':int((before.notna()&after.isna()).sum()),
              'paired_delta_n':int(paired.sum()),'mean_change':float(s.mean()) if len(s) else np.nan,
              'mean_absolute_change':float(s.abs().mean()) if len(s) else np.nan,'median_change':float(s.median()) if len(s) else np.nan,
              'min_change':float(s.min()) if len(s) else np.nan,'max_change':float(s.max()) if len(s) else np.nan,
              'sensitivity_value_mean':float(after_known.mean()) if len(after_known) else np.nan,
              'sensitivity_value_min':float(after_known.min()) if len(after_known) else np.nan,
              'sensitivity_value_max':float(after_known.max()) if len(after_known) else np.nan})
        rows.append({'research_label':LABEL,'sensitivity':'UNAPPROVED: c1_02=0 treated as 1 bedroom','group':group,'measure':'housing_level_changed',
          'n':len(c),'changed_n':int(c.housing_level_changed.sum()),'changed_share':float(c.housing_level_changed.mean()) if len(c) else np.nan})
    sens_summary=pd.DataFrame(rows)
    save_csv(sens_summary,OUT/'zero_bedroom_sensitivity_summary.csv')
    # Aggregate category transitions only; no household identifiers exported.
    trans=[]
    for group,mask in groups.items():
        tab=pd.crosstab(comp.loc[mask,'housing_level_before'],comp.loc[mask,'housing_level_after'],dropna=False)
        tab=tab.rename_axis('level_before').reset_index().melt(id_vars='level_before',var_name='level_after',value_name='households_n')
        tab.insert(0,'group',group); trans.append(tab)
    save_csv(pd.concat(trans,ignore_index=True),OUT/'housing_level_transition_counts.csv')
    return comp,zero,sens_summary

def extend_sensitivity_comparisons():
    comparison=pd.read_csv(SENS/'sensitivity_comparison.csv',low_memory=False)
    base=pd.read_csv(SCORES,dtype={'hhcode':'string'},low_memory=False)
    filemap={
      'crowding_mid3_half0.5':'crowding_mid3_half0.5.csv','crowding_mid3_half1.5':'crowding_mid3_half1.5.csv',
      'crowding_mid4_half0.5':'crowding_mid4_half0.5.csv','crowding_mid4_half1.5':'crowding_mid4_half1.5.csv',
      'age_cutoff_60plus':'age_cutoff_60plus.csv','tenure_codes_7_8_insecure':'tenure_codes_7_8_insecure.csv',
      'wall_cabook_durable':'wall_cabook_durable.csv','roof_codes4_5_durable':'roof_codes4_5_durable.csv',
      'toilet_type_only':'toilet_type_only.csv','domain_min':'domain_min.csv','domain_max':'domain_max.csv'}
    outputs=[]
    soft_cols={d:[f'soft_{d}_{lev}' for lev in ['low','medium','high']] for d in engine.DOMAINS}
    for _,row in comparison.iterrows():
        scenario=row.scenario; d=row.domain; file=filemap.get(scenario)
        n=0; mae=np.nan
        if file and (SENS/file).is_file():
            alt=pd.read_csv(SENS/file,dtype={'hhcode':'string'},low_memory=False)
            cols=soft_cols[d]
            joined=base[['hhcode']+cols].merge(alt[['hhcode']+cols],on='hhcode',how='inner',suffixes=('_base','_alt'),validate='one_to_one')
            arr=np.column_stack([np.abs(joined[f'{c}_base'].to_numpy(float)-joined[f'{c}_alt'].to_numpy(float)) for c in cols])
            valid=np.isfinite(arr).all(axis=1); n=int(valid.sum())
            mae=float(arr[valid].mean()) if n else np.nan
        result=row.to_dict(); result['mean_abs_soft_membership_change']=mae; result['soft_membership_comparison_n']=n
        if file is None: result['soft_membership_status']='not run; no scored sensitivity file'
        elif n==0: result['soft_membership_status']='not comparable'
        else: result['soft_membership_status']='run using existing scores'
        outputs.append(result)
    save_csv(pd.DataFrame(outputs),OUT/'sensitivity_comparison_with_soft_mae.csv')
    return pd.DataFrame(outputs)

def dependency_tie(stage3,scores):
    ratio=pd.to_numeric(stage3.dependency_ratio,errors='coerce')
    base=pd.to_numeric(scores.mu_dependency,errors='coerce')
    tie=ratio.eq(0)&base.notna()
    if not tie.any(): raise ValueError('No ratio=0 dependency tie exists')
    lower=float(base[tie].min())
    if not np.isclose(base[tie].max(),lower): raise ValueError('Ratio=0 rows do not share a single lowest-tie membership')
    new=((base-lower)/(1-lower)).clip(0,1)
    new.loc[tie]=0.0
    newlevel=soft_level(new); oldlevel=soft_level(base)
    valid=base.notna()&new.notna()
    rho=float(spearmanr(base[valid],new[valid]).statistic) if valid.sum()>1 else np.nan
    result={'research_label':LABEL,'sensitivity':'UNAPPROVED: zero-ratio lowest-tie rescaled to 0','ratio_zero_households':int(tie.sum()),
      'baseline_lowest_tie_membership':lower,'spearman_mu_dependency_baseline_vs_sensitivity':rho,
      'spearman_demographic_domain_baseline_vs_sensitivity':rho,'spearman_n':int(valid.sum()),
      'demographic_level_changed_n':int((oldlevel[valid]!=newlevel[valid]).sum()),
      'demographic_level_changed_share':float((oldlevel[valid]!=newlevel[valid]).mean()),
      'level_comparison_n':int(valid.sum()),'rescale_rule':'(baseline membership - lowest ratio=0 membership)/(1 - lowest ratio=0 membership); ratio=0 explicitly set to 0'}
    save_csv(pd.DataFrame([result]),OUT/'dependency_tie_sensitivity.csv')
    return result

def housing_dilution(scores):
    cols=engine.DOMAINS['housing']; block=scores[cols]
    max_input=block.max(axis=1,skipna=True); mean=scores.dom_housing
    mask=max_input.ge(.75)&mean.lt(.25)
    low=pd.cut(max_input,[-0.0000001,.25,.5,.75,1.0000001],labels=['[0,.25]','(.25,.50]','(.50,.75]','(.75,1]'],include_lowest=True)
    means=pd.cut(mean,[-0.0000001,.25,.5,.75,1.0000001],labels=['[0,.25]','(.25,.50]','(.50,.75]','(.75,1]'],include_lowest=True)
    tab=pd.crosstab(low,means,dropna=False).rename_axis('max_single_input_membership_bin').reset_index()
    save_csv(tab,OUT/'housing_max_vs_domain_mean_bins.csv')
    summary=pd.DataFrame([
      {'research_label':LABEL,'measure':'housing dilution condition','n':len(scores),'households_n':int(mask.sum()),'share':float(mask.mean()),'detail':'any known housing input membership >= 0.75 and domain mean < 0.25'},
      {'research_label':LABEL,'measure':'maximum single housing input membership','n':int(max_input.notna().sum()),'households_n':np.nan,'share':np.nan,'detail':f'mean={max_input.mean():.6f}; median={max_input.median():.6f}; p25={max_input.quantile(.25):.6f}; p75={max_input.quantile(.75):.6f}'},
      {'research_label':LABEL,'measure':'housing domain mean','n':int(mean.notna().sum()),'households_n':np.nan,'share':np.nan,'detail':f'mean={mean.mean():.6f}; median={mean.median():.6f}; p25={mean.quantile(.25):.6f}; p75={mean.quantile(.75):.6f}'},
    ])
    save_csv(summary,OUT/'housing_dilution_summary.csv')
    return summary,tab

def asset_valid_mask(valid_n, minimum=18):
    """Whether the recorded asset summary meets a diagnostic completeness threshold."""
    n=pd.to_numeric(pd.Series(valid_n),errors='coerce')
    return n.ge(minimum)

def economic_from_memberships(income, assets):
    """Stage 4 equal mean over available economic memberships, retaining unknowns."""
    block=pd.concat([pd.to_numeric(pd.Series(income),errors='coerce').reset_index(drop=True),
                     pd.to_numeric(pd.Series(assets),errors='coerce').reset_index(drop=True)],axis=1)
    return block.mean(axis=1,skipna=True).where(block.notna().any(axis=1)),block.notna().sum(axis=1)

def asset_share(owned_n, valid_n):
    owned=pd.to_numeric(pd.Series(owned_n),errors='coerce')
    valid=pd.to_numeric(pd.Series(valid_n),errors='coerce')
    return owned.div(valid.where(valid.gt(0)))

def asset_completeness(stage3,scores):
    """D-10a primary diagnostic and explicitly unapproved asset-summary alternatives."""
    valid_n=pd.to_numeric(stage3.asset_items_valid_n,errors='coerce')
    owned=pd.to_numeric(stage3.asset_types_owned_n,errors='coerce')
    inc=pd.to_numeric(scores.mu_income,errors='coerce').reset_index(drop=True)
    old_assets=pd.to_numeric(scores.mu_assets,errors='coerce').reset_index(drop=True)
    d10a_assets=old_assets.where(asset_valid_mask(valid_n,18).reset_index(drop=True))
    base_dom,base_n=economic_from_memberships(inc,d10a_assets)
    old_dom=pd.to_numeric(scores.dom_economic,errors='coerce').reset_index(drop=True)
    old_n=pd.to_numeric(scores.dom_economic_n_used,errors='coerce').reset_index(drop=True)
    min15_assets=old_assets.where(asset_valid_mask(valid_n,15).reset_index(drop=True))
    min15_dom,min15_n=economic_from_memberships(inc,min15_assets)
    share=asset_share(owned,valid_n)
    share_ref=engine.Reference(share)
    share_mu=(1.0-share_ref.cdf(share)).reset_index(drop=True)
    share_dom,share_n=economic_from_memberships(inc,share_mu)

    completeness=pd.DataFrame([
      {'research_label':LABEL,'rule':'Old rule: MIN_VALID_ASSETS=None','valid_asset_summary_households':int(old_assets.notna().sum()),'unknown_asset_summary_households':int(old_assets.isna().sum()),'valid_item_threshold':0},
      {'research_label':LABEL,'rule':'D-10a primary: all 18 asset items valid','valid_asset_summary_households':int(d10a_assets.notna().sum()),'unknown_asset_summary_households':int(d10a_assets.isna().sum()),'valid_item_threshold':18},
    ])
    nrows=[]
    for rule,nseries in [('Old Stage 4 rule: MIN_VALID_ASSETS=None',old_n),('D-10a primary: all 18 valid',base_n)]:
      for k,count in nseries.value_counts(dropna=False).sort_index().items():
        nrows.append({'research_label':LABEL,'rule':rule,'economic_n_used':int(k),'households_n':int(count),'n_total':2})
    fully_unknown=int((inc.isna()&d10a_assets.isna()).sum())
    unknowns=pd.DataFrame([{'research_label':LABEL,'rule':'D-10a primary: all 18 valid','economic_domain_entirely_unknown_n':fully_unknown,
       'income_unknown_n':int(inc.isna().sum()),'asset_summary_unknown_n':int(d10a_assets.isna().sum()),'households_n':len(stage3)}])
    scenarios=[('D-10a primary: all 18 valid',base_dom,'primary'),('UNAPPROVED: share owned among valid items',share_dom,'unapproved'),('UNAPPROVED: minimum 15 valid items',min15_dom,'unapproved')]
    corr=[]
    for name,series,status in scenarios:
      valid=base_dom.notna()&series.notna()
      rho=float(spearmanr(base_dom[valid],series[valid]).statistic) if valid.sum()>1 else np.nan
      corr.append({'research_label':LABEL,'scenario':name,'status':status,'spearman_economic_domain_vs_D10a':rho,'common_households_n':int(valid.sum()),
         'valid_asset_summary_households':int((share.notna() if name.startswith('UNAPPROVED: share') else (min15_assets.notna() if name.startswith('UNAPPROVED: minimum') else d10a_assets.notna())).sum()),
         'asset_reference':'Option-specific empirical rank reference fit to observed owned-share values' if name.startswith('UNAPPROVED: share') else 'Existing frozen Stage 4 asset reference'})
    save_csv(completeness,OUT/'asset_completeness_counts.csv')
    save_csv(pd.DataFrame(nrows),OUT/'economic_n_used_before_after.csv')
    save_csv(unknowns,OUT/'economic_fully_unknown_counts.csv')
    save_csv(pd.DataFrame(corr),OUT/'asset_completeness_sensitivity_correlations.csv')
    return completeness,pd.DataFrame(nrows),unknowns,pd.DataFrame(corr),{'old_dom':old_dom,'d10a_dom':base_dom,'share_dom':share_dom,'min15_dom':min15_dom}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    stage3=pd.read_csv(STAGE3_FILE,dtype={'hhcode':'string'},low_memory=False)
    if len(stage3)!=6847 or stage3.hhcode.isna().any() or stage3.hhcode.duplicated().any(): raise ValueError('Expected 6,847 unique Stage 3 households')
    if {'label_high_vuln','pc_cons'} & set(stage3.columns): raise ValueError('Proxy columns forbidden in Stage 3 input')
    scores=pd.read_csv(SCORES,dtype={'hhcode':'string'},low_memory=False)
    if len(scores)!=6847 or scores.hhcode.duplicated().any(): raise ValueError('Expected 6,847 unique Stage 4 scores')
    if {'label_high_vuln','pc_cons'} & set(scores.columns): raise ValueError('Proxy columns forbidden in Stage 4 score input')
    refs=load_refs()
    fies_summary,fies_items,fies_tests=fies_diagnostics(stage3)
    zero_comp,zero,zero_sens=housing_sensitivity(stage3,scores,refs)
    extended=extend_sensitivity_comparisons()
    dep=dependency_tie(stage3,scores)
    dil,dilbins=housing_dilution(scores)
    asset_counts,asset_n,asset_unknown,asset_corr,asset_domains=asset_completeness(stage3,scores)
    questions=[
      'The cleaned Codebook.zip is not part of the diagnostic inputs. FIES scoring follows existing Stage 3 D-01 complete-eight-item logic; this diagnostic reports observed valid/unknown counts and does not pool forms.',
      'The c1_02=0 to one-bedroom run is explicitly UNAPPROVED and diagnostic only; it does not alter Stage 3, Stage 4, or the frozen reference file.',
      'Dependency tie sensitivity is explicitly UNAPPROVED. Its linear rescaling maps the ratio=0 membership tie to 0 and preserves the top membership at 1; alternative rescaling conventions were not evaluated.',
      'Weighted-maximum operator was not run. No approved weights or exact weighted-maximum formula are specified; choosing weights would introduce a new decision.',
      'Soft-membership MAE is averaged over households with all three domain soft memberships known in both baseline and the existing sensitivity score. Sensitivity files without an existing scored file are marked not run.',
      'Mann-Whitney rank-biserial sign convention is r_rb=2*U_L1/(n_L1*n_L2)-1, so positive values indicate higher L1 ranks. Tests use complete eight-item scores only; no conclusion about pooling is made.',
      'Low/medium/high hard labels use the largest soft membership; exact ties follow low, then medium, then high (first maximum), matching the existing Stage 4 comparison convention.',
      'D-10a is applied only in the Stage 4b diagnostic: the existing frozen asset membership is masked unless all 18 recorded items are valid; Stage 4 files and references remain unchanged.',
      'UNAPPROVED share-owned sensitivity fits a separate empirical reference to the observed owned-share values because the approved frozen asset reference is defined on owned-item counts, not shares.',
      'UNAPPROVED minimum-15-valid sensitivity applies the existing frozen asset reference to households with at least 15 valid items; this is a diagnostic threshold only.',
    ]
    (OUT/'open_questions.md').write_text('# Stage 4b open questions\n\n'+LABEL+'\n\n'+'\n'.join(f'- {q}' for q in questions)+'\n',encoding='utf-8')
    raw=fies_summary[fies_summary.hh_type.isin([1,2])]
    context=fies_summary[fies_summary.hh_type.eq(3)].iloc[0]
    score_lines=['| hh_type | form | complete n | mean | median | SD | share at 0 | share at 8 |','|---:|---|---:|---:|---:|---:|---:|---:|']
    for _,r in raw.iterrows(): score_lines.append(f"| {int(r.hh_type)} | {r.form_group} | {int(r.complete_8_item_score_n)} | {r.score_mean:.4f} | {r.score_median:.4f} | {r.score_sd:.4f} | {r.share_score_0:.4f} | {r.share_score_8:.4f} |")
    test_lines=['| hh_type | L1 complete n | L2 complete n | U (L1) | two-sided p | rank-biserial |','|---:|---:|---:|---:|---:|---:|']
    for _,r in fies_tests.iterrows(): test_lines.append(f"| {int(r.hh_type)} | {r.l1_complete_n} | {r.l2_complete_n} | {r.mann_whitney_u_l1:.1f} | {r.two_sided_p:.6g} | {r.rank_biserial_l1_vs_l2:.6f} |")
    bedroom=pd.read_csv(OUT/'zero_bedroom_household_size_distribution.csv')
    bedroom_text=', '.join(f"size {int(r.household_size)}: {int(r.households_n)}" for _,r in bedroom.iterrows())
    z_mu=zero_sens[(zero_sens.group=='zero_bedroom_households')&(zero_sens.measure=='mu_crowding_change')].iloc[0]
    z_dom=zero_sens[(zero_sens.group=='zero_bedroom_households')&(zero_sens.measure=='dom_housing_change')].iloc[0]
    z_lvl=zero_sens[(zero_sens.group=='zero_bedroom_households')&(zero_sens.measure=='housing_level_changed')].iloc[0]
    w_mu=zero_sens[(zero_sens.group=='whole_file')&(zero_sens.measure=='mu_crowding_change')].iloc[0]
    w_dom=zero_sens[(zero_sens.group=='whole_file')&(zero_sens.measure=='dom_housing_change')].iloc[0]
    w_lvl=zero_sens[(zero_sens.group=='whole_file')&(zero_sens.measure=='housing_level_changed')].iloc[0]
    mae_n=int(extended.mean_abs_soft_membership_change.notna().sum())
    summary_lines=[f'# Stage 4b summary\n\n{LABEL}\n','',f'- Read-only diagnostic inputs: 6,847 unique Stage 3 households and 6,847 existing Stage 4 score rows. Proxy fields were excluded.',
      '- No existing Stage 3/Stage 4 file, rule, default, or score was changed. No imputation or score ranking was added.',
      '', '## FIES form diagnostic','',
      'Complete eight-item raw-score distributions (no form-pooling conclusion):','',*score_lines,'',
      'Mann-Whitney tests and rank-biserial effects (positive means L1 ranks tend higher):','',*test_lines,'',
      f"hh_type=3 L1-only context: {int(context.households_n):,} households; {int(context.complete_8_item_score_n):,} complete eight-item scores. Per-item rates for all three hh_type groups are in `fies_item_endorsement_rates.csv`.",
      '', '## Zero-bedroom sensitivity','',
      f"c1_02=0: {int(zero.sum())} households. Household-size distribution: {bedroom_text}.",
      f"UNAPPROVED c1_02=0 to 1 bedroom: mu_crowding baseline known {int(z_mu.baseline_known_n)}/{int(z_mu.households_n)}, sensitivity known {int(z_mu.sensitivity_known_n)}/{int(z_mu.households_n)}, unknown-to-known {int(z_mu.unknown_to_known_n)}; sensitivity mean {z_mu.sensitivity_value_mean:.6f}.",
      f"Housing degree for zero-bedroom households: mean change {z_dom.mean_change:.6f}, mean absolute change {z_dom.mean_absolute_change:.6f}; housing level changed for {int(z_lvl.changed_n)}/{int(z_lvl.n)} ({z_lvl.changed_share:.6%}).",
      f"Whole file: mu_crowding known {int(w_mu.baseline_known_n)} -> {int(w_mu.sensitivity_known_n)}; {int(w_mu.unknown_to_known_n)} became known; mean absolute delta among {int(w_mu.paired_delta_n)} comparable households {w_mu.mean_absolute_change:.3g}. Housing degree mean change {w_dom.mean_change:.6f}, mean absolute change {w_dom.mean_absolute_change:.6f}; housing level changed for {int(w_lvl.changed_n)}/{int(w_lvl.n)} ({w_lvl.changed_share:.6%}).",
      '', '## Sensitivity and dilution diagnostics','',
      f"Existing sensitivity comparison extended with mean absolute soft-membership change across low/medium/high: {len(extended)} scenario-domain rows; {mae_n} have a scored comparison. See `sensitivity_comparison_with_soft_mae.csv`.",
      f"UNAPPROVED dependency tie rescaling: ratio=0 households {dep['ratio_zero_households']}; baseline lowest membership {dep['baseline_lowest_tie_membership']:.6f}; Spearman rho {dep['spearman_mu_dependency_baseline_vs_sensitivity']:.6f}; demographic level changed {dep['demographic_level_changed_n']}/{dep['level_comparison_n']} ({dep['demographic_level_changed_share']:.6%}).",
      f"Housing dilution condition: {int(dil.iloc[0].households_n)}/{int(dil.iloc[0].n)} ({float(dil.iloc[0].share):.6%}). Max single-input membership: {dil.iloc[1]['detail']}. Domain mean: {dil.iloc[2]['detail']}. Weighted maximum was not run.",
      '', '## Asset completeness diagnostic (D-10a)','',
      f"Valid asset summaries: old MIN_VALID_ASSETS=None {int(asset_counts.iloc[0].valid_asset_summary_households):,}/{int(asset_counts.iloc[0].valid_asset_summary_households+asset_counts.iloc[0].unknown_asset_summary_households):,}; D-10a all 18 valid {int(asset_counts.iloc[1].valid_asset_summary_households):,}/{int(asset_counts.iloc[1].valid_asset_summary_households+asset_counts.iloc[1].unknown_asset_summary_households):,}.",
      'Economic-domain n_used distributions before (existing Stage 4) and after D-10a are in `economic_n_used_before_after.csv`.',
      f"Under D-10a, economic domain entirely unknown (income and assets both unknown): {int(asset_unknown.iloc[0].economic_domain_entirely_unknown_n)}/{int(asset_unknown.iloc[0].households_n)} households.",
      'Economic-domain Spearman comparisons against D-10a baseline are in `asset_completeness_sensitivity_correlations.csv`; share-owned and minimum-15 are UNAPPROVED sensitivities. The share-owned option uses its own empirical reference distribution.',
      '', 'See the diagnostic CSVs for complete per-item rates, form counts, and binned housing distributions. No pooling conclusion or approved decision is made.','', '## Open questions','']
    summary_lines += [f'- {q}' for q in questions]
    (OUT/'stage4b_summary.md').write_text('\n'.join(summary_lines)+'\n',encoding='utf-8')
    inputs=[STAGE3_FILE,FIES_FILE,HH_FILE,SCORES,REF_FILE,STAGE4/'sensitivity'/'sensitivity_comparison.csv',
      STAGE4/'sensitivity'/'crowding_mid3_half0.5.csv',STAGE4/'sensitivity'/'crowding_mid3_half1.5.csv',STAGE4/'sensitivity'/'crowding_mid4_half0.5.csv',STAGE4/'sensitivity'/'crowding_mid4_half1.5.csv',
      STAGE4/'sensitivity'/'age_cutoff_60plus.csv',STAGE4/'sensitivity'/'tenure_codes_7_8_insecure.csv',STAGE4/'sensitivity'/'wall_cabook_durable.csv',
      STAGE4/'sensitivity'/'roof_codes4_5_durable.csv',STAGE4/'sensitivity'/'toilet_type_only.csv',STAGE4/'sensitivity'/'domain_min.csv',STAGE4/'sensitivity'/'domain_max.csv',
      ENGINE_DIR/'fuzzy_v0_1.py',STAGE4/'fuzzy_adapter.py',BASE/'docs'/'spec_v0_1_decision_log.md']
    inmeta=[]
    for p in inputs:
      if not p.exists(): inmeta.append({'path':str(p.relative_to(ROOT)),'status':'missing'}); continue
      rows=sum(1 for _ in p.open(encoding='utf-8-sig'))-1 if p.suffix.lower()=='.csv' else None
      inmeta.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'row_count':rows})
    outmeta=[]
    for p in sorted(OUT.rglob('*')):
      if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts and p.suffix!='.pyc':
        rows=sum(1 for _ in p.open(encoding='utf-8-sig'))-1 if p.suffix.lower()=='.csv' else None
        outmeta.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'row_count':rows})
    manifest={'research_label':LABEL,'pipeline_version':'4b.0.1','inputs':inmeta,'outputs':outmeta,'notes':['No Stage 3 or Stage 4 file was written.','No imputation, rule changes, or model approval.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Stage 4b diagnostics built: {len(stage3)} rows; {len(outmeta)} output hashes')

if __name__=='__main__': main()
