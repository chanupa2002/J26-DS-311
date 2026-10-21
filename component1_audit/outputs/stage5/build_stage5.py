"""Research output - not an eligibility determination.

Run the interim v0.2 Bayesian Network from the approved Stage 9 structure.
All generated files are written only to outputs/stage5.
"""
from __future__ import annotations
import hashlib, itertools, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'component1_audit'
OUT=BASE/'outputs'/'stage5'
SENS=OUT/'sensitivity'
S4=BASE/'outputs'/'stage4b'/'fuzzy_scores_v0_2.csv'
BN_DIR=BASE/'bn_engine'
S3=BASE/'outputs'/'stage3'/'modelling_inputs_v0_1.csv'
HOUSEHOLD=ROOT/'Data'/'processed'/'clean'/'mod_a_household_identification.csv'
O1=ROOT/'Data'/'processed'/'clean'/'mod_o1_shocks.csv'
F1=ROOT/'Data'/'processed'/'clean'/'mod_f1_ag_seasons.csv'
G1=ROOT/'Data'/'processed'/'clean'/'mod_g1_livestock.csv'
G2=ROOT/'Data'/'processed'/'clean'/'mod_g2_fish.csv'
I1=ROOT/'Data'/'processed'/'clean'/'mod_i_nonfarm_business.csv'
QUESTIONNAIRE=ROOT/'Data'/'BRIGHT_questionnaire_English.pdf'
ADDENDUM=BASE/'docs'/'decision_log_section9_addendum (1).md'
CODEBOOK=BASE/'docs'/'codebook_crosscheck_v0_1.md'
LABEL='Research output - not an eligibility determination'
LEAVES=('shelter_quality','sanitation','crowding_tenure','food','demographic','health','economic','financial_resilience')
STATES=('low','medium','high')
O1_COLS=[f'o1_01_{i}' for i in range(1,21)]

sys.dont_write_bytecode=True
sys.path.insert(0,str(BN_DIR))
import bn_v0_1 as bn

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def save_csv(frame,path):
    d=frame.copy()
    if 'research_label' not in d: d.insert(0,'research_label',LABEL)
    d.to_csv(path,index=False,na_rep='',encoding='utf-8-sig')

def make_network_input(scores, leaves=LEAVES):
    """Whitelist only BN leaf evidence; legacy housing and exposure are excluded by default."""
    required=['hhcode']
    for leaf in leaves:
        required += [f'soft_{leaf}_{state}' for state in STATES]
        required += [f'dom_{leaf}_n_used',f'dom_{leaf}_n_total']
    missing=[c for c in required if c not in scores]
    if missing: raise KeyError(f'Missing BN adapter columns: {missing}')
    if {'label_high_vuln','pc_cons'} & set(scores.columns): raise ValueError('Forbidden proxy column in BN scoring file')
    return scores[required].copy()

def adapter_checks(scores):
    rows=[]
    for leaf in LEAVES:
        soft=[f'soft_{leaf}_{s}' for s in STATES]
        counts=[f'dom_{leaf}_n_used',f'dom_{leaf}_n_total']
        softv=scores[soft].apply(pd.to_numeric,errors='coerce')
        complete=softv.notna().all(axis=1)
        sums=softv.sum(axis=1,min_count=3)
        bad=int((complete & (sums.sub(1).abs().gt(1e-6))).sum())
        partial=int(softv.notna().any(axis=1).sum()-complete.sum())
        used=pd.to_numeric(scores[counts[0]],errors='coerce')
        total=pd.to_numeric(scores[counts[1]],errors='coerce')
        bad_counts=int((used.isna()|total.isna()|used.lt(0)|total.lt(0)|used.gt(total)).sum())
        rows.append({'research_label':LABEL,'leaf':leaf,'soft_columns_present':all(c in scores for c in soft),
          'n_used_total_columns_present':all(c in scores for c in counts),'soft_complete_rows':int(complete.sum()),
          'soft_sum_bad_rows':bad,'soft_partial_rows':partial,'coverage_count_bad_rows':bad_counts,
          'observed_leaf_rows':int((complete&used.gt(0)).sum()),'n_used_total_distribution':'; '.join(f'{int(k)}/{int(v)}:{int(n)}' for (k,v),n in pd.DataFrame({'used':used,'total':total}).value_counts().sort_index().items())})
    return pd.DataFrame(rows)

def _safe_rho(a,b):
    a=pd.to_numeric(pd.Series(a),errors='coerce'); b=pd.to_numeric(pd.Series(b),errors='coerce')
    mask=a.notna()&b.notna()
    if mask.sum()<2 or a[mask].nunique()<2 or b[mask].nunique()<2: return np.nan,np.nan,int(mask.sum())
    r=spearmanr(a[mask],b[mask]); return float(r.statistic),float(r.pvalue),int(mask.sum())

def vulnerability_levels(scored):
    """Comparable 3-level MAP classes; 5-state runs collapse outer states to low/high."""
    if 'bn_vulnerability_very_low' in scored:
        block=pd.DataFrame({'low':scored.bn_vulnerability_very_low+scored.bn_vulnerability_low,
           'medium':scored.bn_vulnerability_medium,
           'high':scored.bn_vulnerability_high+scored.bn_vulnerability_very_high},index=scored.index)
    else:
        block=scored[[f'bn_vulnerability_{s}' for s in STATES]].copy(); block.columns=list(STATES)
    return pd.Series(np.asarray(STATES,dtype=object)[np.argmax(block.to_numpy(float),axis=1)],index=scored.index)

def _node(cfg,name):
    return next(n for n in cfg.nodes if n.name==name)

def with_weights(cfg,weight_map):
    nodes=tuple(bn.NodeSpec(n.name,n.parents,weight_map.get(n.name,n.weights)) for n in cfg.nodes)
    return bn.BNConfig(leaves=cfg.leaves,nodes=nodes,n_states=cfg.n_states,sigma=cfg.sigma,
        blend=cfg.blend,min_coverage=cfg.min_coverage,priors=cfg.priors)

def flat_config(base):
    """Approved sensitivity alternative with six sensitivity leaves directly connected."""
    return bn.BNConfig(leaves=base.leaves,nodes=(
      bn.NodeSpec('sensitivity',['shelter_quality','sanitation','crowding_tenure','food','demographic','health']),
      bn.NodeSpec('adaptive_capacity',['economic','financial_resilience']),
      bn.NodeSpec('vulnerability',['sensitivity','adaptive_capacity'])),n_states=base.n_states,sigma=base.sigma,
      blend=base.blend,min_coverage=base.min_coverage,priors=base.priors)

def make_configs(base,network):
    configs=[]
    configs += [('sigma_0.08',bn.BNConfig(**{**base.__dict__,'sigma':0.08}),'approved sensitivity')]
    configs += [('sigma_0.25',bn.BNConfig(**{**base.__dict__,'sigma':0.25}),'approved sensitivity')]
    configs += [('n_states_5',bn.BNConfig(**{**base.__dict__,'n_states':5}),'approved sensitivity')]
    configs += [('weights_economic_food_doubled',with_weights(base,{
       'sensitivity':{'living_conditions':1,'food':2,'demographic':1,'health':1},
       'adaptive_capacity':{'economic':2,'financial_resilience':1},
       'vulnerability':{'sensitivity':1,'adaptive_capacity':2}}),'approved sensitivity; economic/food pathways doubled')]
    configs += [('weights_demographic_doubled',with_weights(base,{
       'sensitivity':{'living_conditions':1,'food':1,'demographic':2,'health':1},
       'vulnerability':{'sensitivity':2,'adaptive_capacity':1}}),'approved sensitivity; demographic pathway doubled at sensitivity and top node')]
    configs += [('blend_none',bn.BNConfig(**{**base.__dict__,'blend':'none'}),'approved sensitivity')]
    configs += [('blend_min_coverage_0.5',bn.BNConfig(**{**base.__dict__,'blend':'min_coverage','min_coverage':0.5}),'approved sensitivity')]
    priors={}
    for leaf in LEAVES:
        mat=network[[f'soft_{leaf}_{s}' for s in STATES]].to_numpy(float)
        observed=np.isfinite(mat).all(axis=1)
        prior=mat[observed].mean(axis=0)
        priors[leaf]=(prior/prior.sum()).tolist()
    configs += [('empirical_priors',bn.BNConfig(**{**base.__dict__,'priors':priors}),'approved sensitivity')]
    # Flat alternative: six sensitivity leaves directly parent sensitivity.
    configs += [('flat_sensitivity_structure',flat_config(base),'approved sensitivity')]
    # Each leave-one-domain-out run uses engine.drop_leaf, exactly as specified.
    for leaf in LEAVES: configs.append((f'drop_{leaf}',bn.drop_leaf(base,leaf),'approved leave-one-domain-out'))
    configs += [('include_exposure',bn.config_v02_interim(include_exposure=True),'UNAPPROVED sensitivity')]
    for name,cfg,status in configs: cfg.validate()
    return configs

def sensitivity_runs(scores,network,baseline,basecfg):
    rows=[]; outdir=SENS
    outdir.mkdir(parents=True,exist_ok=True)
    baseline_level=vulnerability_levels(baseline)
    for name,cfg,status in make_configs(basecfg,network):
        scored=bn.score(make_network_input(scores,cfg.leaves),cfg)
        scored.insert(0,'bn_scenario_status',status)
        scored.insert(0,'bn_scenario',name)
        save_csv(scored,outdir/f'{name}.csv')
        rho,_,n=_safe_rho(baseline.bn_expected_vulnerability,scored.bn_expected_vulnerability)
        common=baseline.bn_p_high.notna()&scored.bn_p_high.notna()
        delta=(baseline.loc[common,'bn_p_high']-scored.loc[common,'bn_p_high']).abs()
        level=vulnerability_levels(scored)
        changed=baseline_level[common].ne(level[common])
        rows.append({'research_label':LABEL,'scenario':name,'status':status,'spearman_expected_vulnerability_vs_baseline':rho,
          'rank_correlation_n':n,'mean_absolute_bn_p_high_change':float(delta.mean()) if len(delta) else np.nan,
          'p_high_comparison_n':int(common.sum()),'most_probable_vulnerability_level_changed_n':int(changed.sum()),
          'most_probable_vulnerability_level_changed_share':float(changed.mean()) if len(changed) else np.nan,
          'alternative_leaf_count':len(cfg.leaves),'n_states':cfg.n_states,'sigma':cfg.sigma,'blend':cfg.blend})
    return pd.DataFrame(rows)

def _markdown_table(df):
    cols=[str(c) for c in df.columns]
    vals=[[str(v) for v in row] for row in df.itertuples(index=False,name=None)]
    lines=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    lines += ['| '+' | '.join(r)+' |' for r in vals]
    return '\n'.join(lines)

def exposure_audit(scores):
    # Raw item values were carried forward into the Stage 4b v0.2 file from Stage 3b.
    blankrows=[]
    for c in O1_COLS:
        s=scores[c]
        blank=s.isna()|s.astype('string').str.strip().eq('').fillna(False)
        valid=pd.to_numeric(s,errors='coerce').isin([1,2,3])
        blankrows.append({'item':c,'blank_n':int(blank.sum()),'blank_rate':float(blank.mean()),
          'valid_n':int(valid.sum()),'out_of_set_n':int((~blank&~valid).sum())})
    # Match item-specific blanks to questionnaire eligibility flags.
    flags=pd.read_csv(F1,usecols=['hhcode','f1_00a'],dtype={'hhcode':'string'},low_memory=False)
    g1=pd.read_csv(G1,usecols=['hhcode','g1_00a'],dtype={'hhcode':'string'},low_memory=False)
    g2=pd.read_csv(G2,usecols=['hhcode','g2_00'],dtype={'hhcode':'string'},low_memory=False)
    i1=pd.read_csv(I1,usecols=['hhcode','i_01'],dtype={'hhcode':'string'},low_memory=False)
    o1=pd.read_csv(O1,usecols=['hhcode']+O1_COLS,dtype={'hhcode':'string'},low_memory=False)
    if o1.hhcode.duplicated().any(): raise ValueError('O1 source keys are not unique')
    d=scores[['hhcode']+O1_COLS].merge(o1,on='hhcode',how='left',validate='one_to_one',suffixes=('_s4','_raw'))
    # Prove the source and carried columns have the same blank pattern.
    source_blank_diffs=[]
    for c in O1_COLS:
        source_blank_diffs.append(int(d[f'{c}_s4'].isna().ne(d[f'{c}_raw'].isna()).sum()))
    d=d[['hhcode']+[f'{c}_raw' for c in O1_COLS]].rename(columns={f'{c}_raw':c for c in O1_COLS})
    d=d.merge(flags,on='hhcode',how='left',validate='one_to_one').merge(g1,on='hhcode',how='left',validate='one_to_one').merge(g2,on='hhcode',how='left',validate='one_to_one').merge(i1,on='hhcode',how='left',validate='one_to_one')
    skiprows=[]
    item_specs={11:('f1_00a','1'),12:('f1_00a','1'),13:('f1_00a','1'),14:('g1_00a','1'),15:('g2_00','1'),16:('f1_00a','1'),17:('f1_00a','1')}
    for item,(flag,code) in item_specs.items():
        s=pd.to_numeric(d[flag],errors='coerce'); blank=d[f'o1_01_{item}'].isna(); eligible=s.eq(float(code)); ineligible=s.notna()&~eligible
        skiprows.append({'item':f'o1_01_{item}','eligibility_rule':f'{flag} == {code}','eligible_n':int(eligible.sum()),
          'eligible_blank_n':int((eligible&blank).sum()),'eligible_answered_n':int((eligible&~blank).sum()),
          'ineligible_n':int(ineligible.sum()),'ineligible_blank_n':int((ineligible&blank).sum()),'ineligible_answered_n':int((ineligible&~blank).sum()),
          'eligibility_unknown_n':int(s.isna().sum())})
    f=pd.to_numeric(d.f1_00a,errors='coerce'); i=pd.to_numeric(d.i_01,errors='coerce')
    eligible=f.eq(1)|i.eq(1); known=f.notna()&i.notna(); blank=d.o1_01_18.isna()
    skiprows.append({'item':'o1_01_18','eligibility_rule':'f1_00a == 1 OR i_01 == 1','eligible_n':int(eligible.sum()),
      'eligible_blank_n':int((eligible&blank).sum()),'eligible_answered_n':int((eligible&~blank).sum()),
      'ineligible_n':int((known&~eligible).sum()),'ineligible_blank_n':int((known&~eligible&blank).sum()),'ineligible_answered_n':int((known&~eligible&~blank).sum()),
      'eligibility_unknown_n':int((~known).sum())})
    patterns=d[O1_COLS].isna().apply(lambda r:','.join(f'o1_01_{i+1}' for i,v in enumerate(r) if v) or '[no blanks]',axis=1)
    common=patterns.value_counts().head(10)
    return pd.DataFrame(blankrows),pd.DataFrame(skiprows),common,source_blank_diffs

def write_exposure_audit(scores):
    item,skip,patterns,blankdiff=exposure_audit(scores)
    exposure_n=pd.to_numeric(scores.dom_exposure_n_used,errors='coerce').value_counts().sort_index()
    total=pd.to_numeric(scores.dom_exposure_n_total,errors='coerce').value_counts().sort_index()
    dist=pd.DataFrame({'n_used':exposure_n.index.astype(int),'households_n':exposure_n.values})
    dist['n_total']=20
    lines=['# Stage 5 O1 / exposure audit','',LABEL,'',
      '## Score derivation and baseline handling','',
      '- `component1_audit/outputs/stage4b/build_stage4b_v0_2.py:85-86` sets `mu_shock` from Stage 3b `o1_mean_severity` after numeric parsing. Stage 3b `build_stage3b.py:62-66` maps valid O1 codes 1→1 (severe), 2→0.5 (moderate), 3→0 (none), then averages valid responses; all invalid/blank means unknown. The item count is retained in `n_o1_items_valid`.',
      '- `component1_audit/outputs/stage4b/build_stage4b_v0_2.py:98-99` sets `dom_exposure = mu_shock`, with `n_used = n_o1_items_valid` and `n_total = 20`.',
      '- Stage 5 baseline excludes the exposure leaf as required. Exposure is used only in the UNAPPROVED `include_exposure` sensitivity.',
      '- The past-12-month reference period for all 20 items follows the researcher assumption; questionnaire printed page 203 explicitly states this period only for O1_01_20.',
      '', '## Per-item blank rates','',_markdown_table(item.assign(blank_rate=item.blank_rate.map(lambda x:f'{x:.3%}'))),
      '', '## Most common blank patterns','',_markdown_table(pd.DataFrame({'blank_items':patterns.index,'households_n':patterns.values})),
      '', '## Questionnaire skip-logic check','',
      'The English questionnaire, printed page 202, conditions O1_01_11–13, 16, and 17 on F1_00a=1; O1_01_14 on G1_00a=1; O1_01_15 on G2_00=1; and O1_01_18 on F1_00a=1 or I_01=1. Items 1–10, 19, and 20 have no skip condition printed on pages 201–203. The cleaned codebook crosscheck does not state O1 routing rules, so this check uses the questionnaire.',
      '',_markdown_table(skip),
      '',f"The 5 F1-routed items (11–13, 16–17) have no blanks among 3,642 eligible households. Among 3,205 ineligible households, 3,185 have the expected blanks; 20 have answers despite the skip condition. Items 14 and 15 match their skip flags exactly (respectively 5,981 and 6,615 ineligible blanks; no eligible blanks). Item 18 has 66 blanks among 3,727 eligible households and 19 answers among 3,120 known-ineligible households. The pattern is mostly consistent with structured skips, with exceptions; it is not evidence that the remaining blanks are random.",
      f'- Stage 4 carried-item blank patterns match the raw O1 source blank patterns: {sum(blankdiff)} discrepant item-household blank statuses across {len(blankdiff)} items.',
      '', '## Exposure coverage','',_markdown_table(dist),
      '', 'Questionnaire source: `Data/BRIGHT_questionnaire_English.pdf`, printed pages 201–203. The inspected skip conditions are on printed page 202.']
    (OUT/'exposure_audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return item,skip,patterns,dist

def score_summary(scored):
    prob_cols=[c for c in scored.columns if c.startswith('bn_') and c.rsplit('_',1)[-1] in STATES and c not in {'bn_p_high'}]
    # Restrict to posterior node state columns by an explicit pattern.
    node_cols=[c for c in prob_cols if c.startswith(('bn_living_conditions_','bn_sensitivity_','bn_adaptive_capacity_','bn_vulnerability_'))]
    node_groups={}
    for col in node_cols:
        node=col.rsplit('_',1)[0]
        node_groups.setdefault(node,[]).append(col)
    pcheck=[]
    for node,cols in node_groups.items():
        x=scored[cols].to_numpy(float)
        pcheck.extend(x.ravel().tolist())
    arr=np.asarray(pcheck,float)
    if not np.isfinite(arr).all() or (arr< -1e-12).any() or (arr>1+1e-12).any(): raise ValueError('BN probabilities outside [0,1] or non-finite')
    for node,cols in node_groups.items():
        if not np.allclose(scored[cols].sum(axis=1),1.0,atol=1e-9): raise ValueError(f'Posterior rows for {node} fail sum-to-one')
    for col in ['bn_p_high','bn_expected_vulnerability','bn_uncertainty_entropy']:
        if not pd.to_numeric(scored[col],errors='coerce').between(0,1).all(): raise ValueError(f'{col} outside [0,1]')
    return node_groups

def validation_report(scores,network,baseline,cfg,adcheck):
    node_groups=score_summary(baseline)
    # Exact independent scoring for 50 reproducibly sampled households.
    sample=network.sample(n=50,random_state=20261021)
    comparable=[c for c in baseline if c not in {'research_label','hhcode','bn_model_version','bn_blend'}]
    maxdiff=0.0
    for idx,row in sample.iterrows():
        alone=bn.score(network.loc[[idx]],cfg).iloc[0]
        dif=np.abs(pd.to_numeric(alone[comparable],errors='coerce').to_numpy(float)-pd.to_numeric(baseline.loc[idx,comparable],errors='coerce').to_numpy(float))
        maxdiff=max(maxdiff,float(np.nanmax(dif)))
    if maxdiff>1e-12: raise ValueError(f'Single vs batch score mismatch: {maxdiff}')
    stats=[]
    for col in ['bn_p_high','bn_expected_vulnerability','bn_uncertainty_entropy']:
        s=pd.to_numeric(baseline[col],errors='coerce')
        stats.append({'measure':col,'n':int(s.notna().sum()),'min':float(s.min()),'q1':float(s.quantile(.25)),
          'median':float(s.median()),'q3':float(s.quantile(.75)),'max':float(s.max()),
          'share_gt_0.3':float(s.gt(.3).mean()) if col=='bn_p_high' else np.nan,
          'share_gt_0.5':float(s.gt(.5).mean()) if col=='bn_p_high' else np.nan})
    leaves=baseline.bn_leaves_observed.value_counts().sort_index()
    table=pd.DataFrame(stats)
    leaf_table=pd.DataFrame({'bn_leaves_observed':leaves.index,'households_n':leaves.values})
    cpt_nodes=['living_conditions','sensitivity','adaptive_capacity','vulnerability']
    cpt_text=[]
    for node in cpt_nodes:
        t=bn.cpt_table(node,cfg)
        cpt_text.extend([f'### {node} ({len(t)} rows)','',_markdown_table(t),''])
    lines=['# Stage 5 Bayesian Network validation','',LABEL,'',
      f'- Input rows: {len(scores):,}; scored rows: {len(baseline):,}; unique scored keys: {baseline.hhcode.nunique():,}.',
      '- Baseline: `config_v02_interim()`; eight leaves exactly as M-07 specifies. Exposure and legacy housing columns are excluded from the input whitelist.',
      f'- Probability validation: {sum(len(v) for v in node_groups.values())} node-posterior columns checked; all in [0,1] and each node distribution sums to 1 within 1e-9.',
      f'- Scoring one household at a time matched batch scoring for 50 random households (seed 20261021); maximum absolute difference = {maxdiff:.3g}.',
      '', '## Adapter column check','',_markdown_table(adcheck),
      '', '## Baseline score distributions','',_markdown_table(table.assign(**{c:table[c].map(lambda x:'' if pd.isna(x) else f'{x:.6f}') for c in ['min','q1','median','q3','max','share_gt_0.3','share_gt_0.5']})),
      '', '## Households by observed BN leaves','',_markdown_table(leaf_table),
      '', '## Conditional probability tables','']+cpt_text
    (OUT/'bn_validation.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return table,leaf_table,maxdiff

def coverage_diagnostics(network,baseline):
    coverage=[]
    for leaf in LEAVES:
        used=pd.to_numeric(network[f'dom_{leaf}_n_used'],errors='coerce')
        total=pd.to_numeric(network[f'dom_{leaf}_n_total'],errors='coerce')
        coverage.append((used/total).where(total.gt(0),0.0))
    mean_coverage=pd.concat(coverage,axis=1).mean(axis=1)
    rows=[]
    for score in ['bn_expected_vulnerability','bn_uncertainty_entropy']:
        for driver,series in [('bn_leaves_observed',baseline.bn_leaves_observed),('mean_leaf_coverage',mean_coverage)]:
            rho,p,n=_safe_rho(baseline[score],series)
            rows.append({'research_label':LABEL,'score':score,'coverage_measure':driver,'spearman_rho':rho,'p_value':p,'n':n})
    frame=pd.DataFrame(rows); save_csv(frame,OUT/'coverage_correlations.csv')
    return frame,mean_coverage

def comparison_baseline(scores,network,baseline):
    domains=[f'dom_{l}' for l in LEAVES]
    degrees=scores[domains].apply(pd.to_numeric,errors='coerce')
    additive=degrees.mean(axis=1,skipna=True).where(degrees.notna().any(axis=1))
    rho,p,n=_safe_rho(baseline.bn_expected_vulnerability,additive)
    mask=baseline.bn_expected_vulnerability.notna()&additive.notna()
    bn_rank=baseline.loc[mask,'bn_expected_vulnerability'].rank(method='average',pct=True)
    add_rank=additive[mask].rank(method='average',pct=True)
    diff=(bn_rank-add_rank).abs()
    out=pd.DataFrame([{'research_label':LABEL,'comparison':'8-leaf available-case additive index','spearman_with_bn_expected_vulnerability':rho,
      'spearman_p_value':p,'n':n,'percentile_difference_gt_20_points_n':int(diff.gt(.2).sum()),
      'percentile_difference_gt_20_points_share':float(diff.gt(.2).mean()),'mean_absolute_percentile_difference':float(diff.mean())}])
    save_csv(out,OUT/'additive_comparison.csv')
    return out

def geographic_summaries(baseline):
    loc=pd.read_csv(HOUSEHOLD,usecols=['hhcode','a_01_province','a_02_district'],dtype={'hhcode':'string'},low_memory=False)
    if loc.hhcode.isna().any() or loc.hhcode.duplicated().any(): raise ValueError('Geographic table has missing or duplicate keys')
    joined=baseline[['hhcode','bn_p_high','bn_expected_vulnerability','bn_uncertainty_entropy']].merge(loc,on='hhcode',how='left',validate='one_to_one')
    if len(joined)!=6847 or joined[['a_01_province','a_02_district']].isna().any().any(): raise ValueError('Geo join did not preserve 6,847 complete keys')
    def summarize(keys):
        return joined.groupby(keys,dropna=False).agg(households_n=('hhcode','size'),mean_bn_p_high=('bn_p_high','mean'),
          mean_bn_expected_vulnerability=('bn_expected_vulnerability','mean'),mean_bn_uncertainty_entropy=('bn_uncertainty_entropy','mean')).reset_index()
    save_csv(summarize(['a_01_province']),OUT/'by_province.csv')
    save_csv(summarize(['a_01_province','a_02_district']),OUT/'by_district.csv')
    return int(len(joined)),int(joined.a_01_province.nunique()),int(joined.a_02_district.nunique())

def _row_count(path):
    if path.suffix.lower()!='.csv': return None
    with open(path,encoding='utf-8-sig') as f: return max(0,sum(1 for _ in f)-1)

def main():
    OUT.mkdir(parents=True,exist_ok=True); SENS.mkdir(parents=True,exist_ok=True)
    scores=pd.read_csv(S4,dtype={'hhcode':'string'},low_memory=False)
    if len(scores)!=6847 or scores.hhcode.isna().any() or scores.hhcode.duplicated().any(): raise ValueError('Expected 6,847 unique fuzzy score rows')
    # Build adapter check over all leaves; then construct the explicit baseline whitelist.
    all_leaves=LEAVES+('exposure',)
    adcheck=adapter_checks_for_leaves(scores,all_leaves)
    if adcheck.soft_sum_bad_rows.sum() or adcheck.soft_partial_rows.sum() or adcheck.coverage_count_bad_rows.sum(): raise ValueError('Fuzzy adapter check failed')
    network=make_network_input(scores)
    cfg=bn.config_v02_interim()
    baseline=bn.score(network,cfg)
    save_csv(baseline,OUT/'bn_scores_v0_2_interim.csv')
    flat_cpt=bn.cpt_table('sensitivity',flat_config(cfg))
    if len(flat_cpt)!=729: raise ValueError(f'Expected a 729-row flat sensitivity CPT, got {len(flat_cpt)}')
    save_csv(flat_cpt,OUT/'flat_sensitivity_cpt_729.csv')
    validation_report(scores,network,baseline,cfg,adcheck[adcheck.leaf.isin(LEAVES)])
    coverage_diagnostics(network,baseline)
    compare=comparison_baseline(scores,network,baseline)
    sens=sensitivity_runs(scores,network,baseline,cfg)
    save_csv(sens,OUT/'sensitivity_comparison.csv')
    geo_n,nprov,ndist=geographic_summaries(baseline)
    # Exposure audit separately uses the descriptive/raw O1 inputs and is not passed to baseline BN.
    item,skip,patterns,exposure_dist=write_exposure_audit(scores)
    proxy_text=('## Separate descriptive proxy check\n\n'+LABEL+'\n\nNot run: the Stage 4 fuzzy score input does not contain target/proxy fields. No proxy data were read for this stage.\n')
    (OUT/'proxy_descriptive_check.md').write_text(proxy_text,encoding='utf-8')
    questions=[
      'Exposure is excluded from baseline exactly as required. The separate include_exposure BN run is UNAPPROVED and does not change baseline outputs.',
      'Stage 4b O1 mean severity uses researcher-approved equal spacing (1 severe=1, 2 moderate=0.5, 3 none=0) and the assumed 12-month reference period for all items. This Stage 5 network still excludes exposure from baseline per the task rule.',
      'B-02 sensitivity weights were operationalized as two explicit scenarios: economic+food pathways doubled and demographic pathway doubled, with the corresponding group weight doubled at the top node. Alternative interpretations of “doubled” were not run.',
      'For n_states=5, the most-probable-level comparison collapses very_low+low to low, keeps medium, and combines high+very_high to high, so level-change shares are comparable with the 3-state baseline.',
      'Province and district aggregates use the one-to-one household identification join because geography is not a column in the Stage 4 fuzzy file; only aggregate rows are written.',
      'Conditional tables follow the expert-specified ranked-nodes method. They are not learned from outcome labels or data; scores are research composites and are not validated for decision use.',
      'Domains are treated as independent evidence in this tree even though they may be correlated; ranked-node smoothing pulls estimates toward the middle. Alternative combination functions remain for a later round.'
    ]
    (OUT/'open_questions.md').write_text('# Stage 5 open questions\n\n'+LABEL+'\n\n'+'\n'.join(f'- {q}' for q in questions)+'\n',encoding='utf-8')
    # Summary numbers and aggregate-only geographic output.
    st=baseline.bn_expected_vulnerability.describe(percentiles=[.25,.5,.75])
    p30=float(baseline.bn_p_high.gt(.3).mean()); p50=float(baseline.bn_p_high.gt(.5).mean())
    leaves_dist=baseline.bn_leaves_observed.value_counts().sort_index()
    leaf_text=', '.join(f'{int(i)} leaves: {int(n)}' for i,n in leaves_dist.items())
    expos_known=int(scores.dom_exposure.notna().sum())
    summary=[f'# Stage 5 summary\n\n{LABEL}\n','',
      f'- Baseline BN scored {len(baseline):,} households with `config_v02_interim()` and the eight M-07 leaves. Exposure and legacy housing degree were excluded from baseline input.',
      f'- Expected vulnerability: mean {st["mean"]:.4f}; median {st["50%"]:.4f}; range {st["min"]:.4f}–{st["max"]:.4f}. `bn_p_high` exceeds 0.3 for {p30:.2%} and 0.5 for {p50:.2%}.',
      f'- Observed BN leaf count distribution: {leaf_text}.',
      '- Validation and printed CPTs: `bn_validation.md`; coverage correlations: `coverage_correlations.csv`.',
      f'- Additive 8-leaf index correlation with BN expected vulnerability: {compare.iloc[0].spearman_with_bn_expected_vulnerability:.4f}; percentile ranks differ by >20 points for {int(compare.iloc[0].percentile_difference_gt_20_points_n):,}/{int(compare.iloc[0].n):,} households.',
      f'- Sensitivity scenarios run: {len(sens)} (individual outputs under `sensitivity/`); compare table: `sensitivity_comparison.csv`. Flat alternative CPT: `flat_sensitivity_cpt_729.csv` ({len(flat_cpt)} rows).',
      f'- Province/district join: {geo_n:,} rows preserved; {nprov} province codes and {ndist} district codes. Only aggregate tables are provided.',
      f'- Exposure audit found {expos_known:,} fuzzy exposure degrees in the Stage 4 input; baseline excluded them. The UNAPPROVED exposure-included sensitivity is reported separately.',
      '- No score is validated for decision use; BN outputs are expert-specified research composites, not eligibility decisions or calibrated probabilities of vulnerability.',
      '', '## Open questions','']+[f'- {q}' for q in questions]
    (OUT/'stage5_summary.md').write_text('\n'.join(summary)+'\n',encoding='utf-8')
    # Hash inputs and every stage5 artifact except the manifest itself.
    inputs=[S4,BN_DIR/'bn_v0_1.py',BN_DIR/'test_bn_v0_1.py',ADDENDUM,CODEBOOK,QUESTIONNAIRE,O1,F1,G1,G2,I1,HOUSEHOLD,S3]
    inmeta=[]
    for p in inputs:
        if not p.exists(): inmeta.append({'path':str(p.relative_to(ROOT)),'status':'missing'}); continue
        inmeta.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'row_count':_row_count(p)})
    outmeta=[]
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts:
            outmeta.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'row_count':_row_count(p)})
    manifest={'research_label':LABEL,'pipeline_version':'stage5-v0.2.0','bn_model_version':bn.MODEL_VERSION,
      'baseline_config':'config_v02_interim()','baseline_leaves':list(LEAVES),'exposure_baseline':'excluded',
      'inputs':inmeta,'outputs':outmeta,'notes':['No BN engine code/default modified.','No imputation.','No household-level geography report.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Stage 5 complete: {len(baseline)} baseline rows; {len(sens)} sensitivities; exposure excluded from baseline.')

def adapter_checks_for_leaves(scores,leaves):
    rows=[]
    for leaf in leaves:
        soft=[f'soft_{leaf}_{s}' for s in STATES]; counts=[f'dom_{leaf}_n_used',f'dom_{leaf}_n_total']
        missing=[c for c in soft+counts if c not in scores]
        if missing: raise KeyError(f'{leaf}: missing {missing}')
        sv=scores[soft].apply(pd.to_numeric,errors='coerce'); complete=sv.notna().all(axis=1)
        sums=sv.sum(axis=1,min_count=3); used=pd.to_numeric(scores[counts[0]],errors='coerce'); total=pd.to_numeric(scores[counts[1]],errors='coerce')
        bad=int((complete&sums.sub(1).abs().gt(1e-6)).sum())
        partial=int((sv.notna().any(axis=1)&~complete).sum())
        bad_counts=int((used.isna()|total.isna()|used.lt(0)|total.lt(0)|used.gt(total)).sum())
        dist=pd.DataFrame({'u':used,'t':total}).value_counts().sort_index()
        rows.append({'research_label':LABEL,'leaf':leaf,'soft_columns_present':True,'n_used_total_columns_present':True,
          'soft_complete_rows':int(complete.sum()),'soft_sum_bad_rows':bad,'soft_partial_rows':partial,'coverage_count_bad_rows':bad_counts,
          'observed_leaf_rows':int((complete&used.gt(0)).sum()),'n_used_total_distribution':'; '.join(f'{int(u)}/{int(t)}:{int(n)}' for (u,t),n in dist.items())})
    return pd.DataFrame(rows)

if __name__=='__main__': main()
