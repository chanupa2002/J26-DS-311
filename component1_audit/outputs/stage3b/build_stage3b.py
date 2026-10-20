"""Research output - not an eligibility determination.
Build Stage 3b descriptive checks and additions. No scores or imputations.
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'component1_audit'
OUT = BASE / 'outputs' / 'stage3b'
CHECKS = OUT / 'checks'
LABEL = 'Research output - not an eligibility determination'
SPINE_PATH = BASE / 'outputs' / 'pipeline_v0' / 'household_core.csv'
DATA = ROOT / 'Data' / 'processed' / 'clean'
USER_QUESTIONNAIRE = Path(r'C:\Users\ishin\Downloads\dataverse_files\Documentation\BRIGHT_questionnaire_English.pdf')
MODULES = {
 'N1':'mod_n1_debt.csv','N2':'mod_n2_savings.csv','B3':'mod_b3_roster_long.csv',
 'O1':'mod_o1_shocks.csv','O2':'mod_o2_coping.csv','L3':'mod_l3_energy_insecurity.csv',
 'L5':'mod_l5_water_security.csv'}

def clean(x):
    if pd.isna(x) or str(x).strip() == '': return None
    s=str(x).strip()
    # CSV numeric columns are commonly parsed as floats (e.g. code 1 -> "1.0").
    # Normalize only integral numeric representations; never alter textual codes.
    try:
        f=float(s)
        if np.isfinite(f) and f.is_integer(): return str(int(f))
    except (ValueError,TypeError): pass
    return s

def counts(df, cols, module, source, codebook_values=None):
    rows=[]
    for c in cols:
        if c not in df: continue
        vals=df[c].map(clean)
        for v,n in vals.value_counts(dropna=False).items():
            v=clean(v); invalid = (v is not None and codebook_values is not None and v not in codebook_values)
            rows.append({'research_label':LABEL,'module':module,'variable':c,'value':'[BLANK]' if v is None else v,
                         'count':int(n),'codebook_status':('outside supplied value set' if invalid else 'within supplied value set') if codebook_values is not None and v is not None else ('blank' if v is None else 'not verified; Codebook.zip unavailable'),
                         'value_set_source':source})
    return rows

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def binary_answer(value, allowed=('0','1')):
    """Strict binary mapping: blanks and out-of-set codes stay missing."""
    v=clean(value)
    return {'0':0,'1':1}.get(v) if v in set(allowed) else None

def count_valid_o1(values):
    """Count only observed O1 responses in the task-specified set."""
    return sum(clean(x) in {'1','2','3'} for x in values)

def validate_unique_household_key(df, module):
    if df.hhcode.duplicated().any(): raise ValueError(f'{module} has duplicate household keys; refusing join')

def health_aggregate(spine, roster, b3):
    """Aggregate only valid b3_01 responses; no b3_03/b3_04 use."""
    if b3.duplicated(['hhcode','pid']).any(): raise ValueError('B3 duplicate hhcode+pid; refusing member aggregation')
    base=spine[['hhcode']].copy()
    roster_keys=set(zip(roster.hhcode.astype(str),roster.pid.astype(str)))
    in_roster=b3.apply(lambda r:(str(r.hhcode),str(r.pid)) in roster_keys,axis=1)
    valid=b3[in_roster & b3.b3_01.map(lambda x:clean(x) in {'0','1'} if clean(x) is not None else False)].copy()
    valid['_chronic']=valid.b3_01.map(lambda x:int(clean(x)=='1'))
    agg=valid.groupby('hhcode',as_index=False).agg(n_members_b3_valid=('pid','size'),n_chronic=('_chronic','sum'))
    base=base.merge(agg,on='hhcode',how='left',validate='one_to_one')
    base['n_members_b3_valid']=base.n_members_b3_valid.fillna(0).astype(int); base['n_chronic']=base.n_chronic.fillna(0).astype(int)
    base['share_chronic']=base.n_chronic.div(base.n_members_b3_valid.where(base.n_members_b3_valid>0))
    roster_n=roster.groupby('hhcode').pid.nunique()
    base['_roster_n']=base.hhcode.map(roster_n).fillna(0).astype(int)
    base['health_status']=np.select([base.n_members_b3_valid.eq(0),base.n_members_b3_valid.ge(base._roster_n)],['missing','valid'],default='partial')
    return base.drop(columns='_roster_n')

def main():
    OUT.mkdir(parents=True,exist_ok=True); CHECKS.mkdir(parents=True,exist_ok=True)
    spine=pd.read_csv(SPINE_PATH,dtype={'hhcode':'string'}); keys=set(spine.hhcode.dropna().astype(str)); assert len(spine)==6847 and spine.hhcode.is_unique
    b0=pd.read_csv(DATA/'mod_b0_roster_long.csv',dtype={'hhcode':'string','pid':'string'})
    modules={k:pd.read_csv(DATA/v,dtype={'hhcode':'string','pid':'string'}) for k,v in MODULES.items()}
    allcounts=[]; summary=[]; checks={}
    # Specific item sets; only the explicitly specified sets are used as validity rules.
    requested={
      'N1':['n1_0']+[f'n1_01_{i}' for i in range(1,12)],
      'N2':['n2_01']+[f'n2_02_{i}' for i in range(1,7)]+['n2_02_999','n2_02_998','n2_03'],
      'B3':['b3_01','b3_03','b3_04'], 'O1':[f'o1_01_{i}' for i in range(1,21)],
      'O2':['o2_01','o2_03','o2_05','o2_06'],
      'L3':[f'l3_{i:02}' for i in range(1,10)],'L5':[f'l5_{i:02}' for i in range(1,28)]}
    supplied={'O1':{'1','2','3'},'L3':{'1','2','3'},'L5':{'0','1','2','3','4'},'B3':{'0','1'}}
    for mod,df in modules.items():
        name=MODULES[mod]; long=mod=='B3'; present=[c for c in requested[mod] if c in df]
        dup=int(df.hhcode.duplicated(keep=False).sum()) if not long else int(df.duplicated(['hhcode','pid'],keep=False).sum())
        outside=len(set(df.hhcode.dropna().astype(str))-keys)
        inmod=set(df.hhcode.dropna().astype(str)) & keys
        summary.append({'research_label':LABEL,'module':mod,'file':name,'row_structure':'long household-member' if long else 'one row per household','rows':len(df),'distinct_hhcode':int(df.hhcode.nunique()),'duplicate_key_rows':dup,'module_households_not_in_spine':outside,'spine_households_missing_from_module':len(keys-inmod),'spine_households_with_at_least_one_valid_answer':None,'coverage_status':'see variable checks'})
        rows=counts(df,present,mod,'Task-specified set' if mod in supplied else 'not verified; Codebook.zip unavailable',supplied.get(mod))
        allcounts.extend(rows)
        # One per-module CSV, with aggregate frequency rows only (never raw free text).
        pd.DataFrame(rows,columns=['research_label','module','variable','value','count','codebook_status','value_set_source']).to_csv(CHECKS/f'{mod.lower()}_value_counts.csv',index=False,encoding='utf-8-sig')
        checks[mod]=df
    # Household module duplicate/key checks; no ambiguous duplicate joins are allowed.
    for mod in ['N1','N2','O1','O2','L3','L5']:
        df=modules[mod]
        validate_unique_household_key(df,mod)
    # N1 raw flag cross-tab; source flag set is descriptive, not a debt rule.
    n1=modules['N1']; n1flags=[c for c in n1 if re.fullmatch(r'n1_01_\d+',c)]
    n1any=n1[n1flags].apply(lambda r:any(clean(x)=='1' for x in r),axis=1) if n1flags else pd.Series(False,index=n1.index)
    n1tab=pd.crosstab(n1.n1_0.map(lambda x:'[BLANK]' if clean(x) is None else clean(x)),n1any.map({True:'any source flag = 1',False:'no source flag = 1'}),dropna=False).reset_index(names='n1_0')
    n1tab.insert(0,'research_label',LABEL); n1tab.to_csv(CHECKS/'n1_0_by_any_source_flag.csv',index=False,encoding='utf-8-sig')
    # N1 amount summaries: coverage/range only; no source values emitted.
    amount_cols=[c for c in n1 if c.startswith('n1_') and c not in n1flags+['n1_0','n1_respondent'] and not c.endswith('_other')]
    amt=[]
    for c in amount_cols:
        s=pd.to_numeric(n1[c],errors='coerce'); observed=s.dropna()
        amt.append({'research_label':LABEL,'variable':c,'nonblank_count':int(n1[c].map(clean).notna().sum()),'numeric_count':len(observed),'min':observed.min() if len(observed) else None,'max':observed.max() if len(observed) else None})
    pd.DataFrame(amt).to_csv(CHECKS/'n1_amount_field_coverage_range.csv',index=False,encoding='utf-8-sig')
    # N2 response vs flags, using explicitly requested flag fields only.
    n2=modules['N2']; n2flags=[c for c in [f'n2_02_{i}' for i in range(1,7)]+['n2_02_999','n2_02_998'] if c in n2]
    n2any=n2[n2flags].apply(lambda r:any(clean(x) is not None for x in r),axis=1) if n2flags else pd.Series(False,index=n2.index)
    t=pd.crosstab(n2.n2_01.map(lambda x:'[BLANK]' if clean(x) is None else clean(x)),n2any.map({True:'any flag populated',False:'no flag populated'}),dropna=False).reset_index(names='n2_01')
    t.insert(0,'research_label',LABEL); t.to_csv(CHECKS/'n2_01_by_n2_02_flags.csv',index=False,encoding='utf-8-sig')
    # B3 cross-tab and B0 member reconciliation.
    b3=modules['B3'];
    def cat(s): return s.map(lambda x:'[BLANK]' if clean(x) is None else clean(x))
    t=pd.crosstab(cat(b3.b3_01),cat(b3.b3_03),dropna=False).reset_index(names='b3_01')
    t.insert(0,'research_label',LABEL); t.to_csv(CHECKS/'b3_01_by_b3_03.csv',index=False,encoding='utf-8-sig')
    if b3.duplicated(['hhcode','pid']).any(): raise ValueError('B3 duplicate hhcode+pid; refusing member aggregation')
    rosterkeys=set(zip(b0.hhcode.dropna().astype(str),b0.pid.dropna().astype(str)))
    b3keys=set(zip(b3.hhcode.dropna().astype(str),b3.pid.dropna().astype(str)))
    recon=pd.DataFrame([{'research_label':LABEL,'measure':'B3 members not in B0 roster','count':len(b3keys-rosterkeys)},
      {'research_label':LABEL,'measure':'B0 roster members absent from B3','count':len(rosterkeys-b3keys)},
      {'research_label':LABEL,'measure':'spine households with no B3 rows','count':len(keys-set(b3.hhcode.dropna().astype(str)))}])
    recon.to_csv(CHECKS/'b3_roster_reconciliation.csv',index=False,encoding='utf-8-sig')
    # Age bands by B0 roster age. No health status derived from b3_03/04.
    age=pd.to_numeric(b0.b0_04_years,errors='coerce')
    b0=b0.assign(_ageband=np.select([age<15,age.between(15,64),age>=65],['under 15','15-64','65+'],default='age unknown'))
    b3valid=b3.assign(_valid=b3.b3_01.map(lambda x:clean(x) in {'0','1'} if clean(x) is not None else False))
    b3validkeys=set(zip(b3valid.loc[b3valid._valid,'hhcode'].astype(str),b3valid.loc[b3valid._valid,'pid'].astype(str)))
    age_rows=[]
    for band,g in b0.groupby('_ageband',dropna=False):
        valid=sum((str(h),str(p)) in b3validkeys for h,p in zip(g.hhcode,g.pid))
        age_rows.append({'research_label':LABEL,'age_band':band,'roster_members':len(g),'b3_01_valid':valid,'b3_01_missing_or_invalid':len(g)-valid})
    pd.DataFrame(age_rows).to_csv(CHECKS/'b3_coverage_by_age_band.csv',index=False,encoding='utf-8-sig')
    # Assemble additions; all household joins assert one-to-one.
    base=spine[['hhcode']].copy(); base.insert(0,'research_label',LABEL)
    for mod, cols in [('N2',['n2_01']),('N1',['n1_0']),('O1',[f'o1_01_{i}' for i in range(1,21)])]:
        df=modules[mod]; use=[c for c in cols if c in df]
        base=base.merge(df[['hhcode']+use],on='hhcode',how='left',validate='one_to_one')
    base['bank_account']=base.n2_01.map(binary_answer); base['bank_account_status']=np.where(base.bank_account.notna(),'valid','missing')
    base['has_debt']=base.n1_0.map(binary_answer); base['has_debt_status']=np.where(base.has_debt.notna(),'valid','missing')
    # B3 aggregation covers only roster members, and never uses b3_03/b3_04.
    health=health_aggregate(spine,b0,b3)
    base=base.drop(columns=['n2_01','n1_0']).merge(health.drop(columns='hhcode'),left_index=True,right_index=True,validate='one_to_one')
    raw_items=[f'o1_01_{i}' for i in range(1,21) if f'o1_01_{i}' in base]
    base['n_o1_items_valid']=base[raw_items].apply(count_valid_o1,axis=1)
    outcols=['research_label','hhcode','bank_account','bank_account_status','has_debt','has_debt_status','n_members_b3_valid','n_chronic','share_chronic','health_status']+raw_items+['n_o1_items_valid']
    additions=base[outcols]; additions.to_csv(OUT/'modelling_inputs_v0_2_additions.csv',index=False,encoding='utf-8-sig')
    # O1/O2/L3/L5 checks, sensitive to no free text.
    for mod,df in modules.items():
        if mod=='O2': cols=[c for c in df if re.fullmatch(r'o2_\d{2}',c) and c not in {'o2_02','o2_04'}]
        elif mod=='L3': cols=[c for c in df if re.fullmatch(r'l3_\d{2}',c)]
        elif mod=='L5': cols=[c for c in df if re.fullmatch(r'l5_\d{2}',c)]
        else: continue
        vset={'O2':{'1','2','3','4','997'},'L3':{'0','1','2','3','4'},'L5':{'0','1','2','3','4'}}[mod]
        rr=counts(df,cols,mod,'Task-specified set' if mod in {'L3','L5'} else 'not verified; Codebook.zip unavailable',vset if mod in {'L3','L5'} else None)
        pd.DataFrame(rr).to_csv(CHECKS/f'{mod.lower()}_all_lead_value_counts.csv',index=False,encoding='utf-8-sig')
        if mod=='O2':
            grid=[]
            for c in cols:
                s=df[c].map(clean)
                for v in ['1','2','3','4','997','[BLANK]']:
                    grid.append({'research_label':LABEL,'variable':c,'code':v,'count':int((s.isna() if v=='[BLANK]' else s.eq(v)).sum())})
            pd.DataFrame(grid).to_csv(CHECKS/'o2_requested_code_counts.csv',index=False,encoding='utf-8-sig')
            lead_any=df[cols].apply(lambda r:any(clean(x)=='1' for x in r),axis=1)
            pd.DataFrame([{'research_label':LABEL,'households_with_any_lead_code_1':int(lead_any.sum()),'lead_items_checked':';'.join(cols)}]).to_csv(CHECKS/'o2_households_any_code_1.csv',index=False,encoding='utf-8-sig')
    # Expected item presence and scale note are explicit; absent columns are never synthesized.
    presence=[]
    for mod,expected in [('O1',[f'o1_01_{i}' for i in range(1,21)]),('L3',[f'l3_{i:02}' for i in range(1,10)]),('L5',[f'l5_{i:02}' for i in range(1,28)])]:
        df=modules[mod]
        for c in expected:
            presence.append({'research_label':LABEL,'module':mod,'variable':c,'column_present':c in df,
              'scale_type':'3-point frequency/never-sometimes-always per task' if mod=='L3' and c in [f'l3_{i:02}' for i in range(1,10)] else ('frequency 0-4 per task' if mod in {'L3','L5'} else 'severity: 1 severe, 2 moderate, 3 none per task')})
    pd.DataFrame(presence).to_csv(CHECKS/'expected_item_presence_and_scale.csv',index=False,encoding='utf-8-sig')
    # Module coverage based only on stipulated value sets; uncertain sets explicitly unverified.
    cov=[]
    for mod,df in modules.items():
        if mod=='B3': valid=df.b3_01.map(lambda x:clean(x) in {'0','1'} if clean(x) is not None else False); valid_h=set(df.loc[valid,'hhcode'].dropna().astype(str))
        elif mod=='O1': valid=df[[f'o1_01_{i}' for i in range(1,21) if f'o1_01_{i}' in df]].apply(lambda r:any(clean(x) in {'1','2','3'} for x in r),axis=1); valid_h=set(df.loc[valid,'hhcode'].dropna().astype(str))
        elif mod in {'L3','L5'}:
            cols=requested[mod]; cols=[c for c in cols if c in df]; valid=df[cols].apply(lambda r:any(clean(x) in (supplied[mod]) for x in r),axis=1); valid_h=set(df.loc[valid,'hhcode'].dropna().astype(str))
        else:
            cols=requested[mod]; cols=[c for c in cols if c in df]
            valid=df[cols].apply(lambda r:any(clean(x) is not None for x in r),axis=1) if cols else pd.Series(False,index=df.index)
            valid_h=set(df.loc[valid,'hhcode'].dropna().astype(str))
        cov.append({'research_label':LABEL,'module':mod,'spine_households_with_valid_answer':len(valid_h & keys),'validity_note':'value set verified from task-specified rules' if mod in supplied else 'nonblank coverage only; Codebook.zip unavailable'})
    pd.DataFrame(cov).to_csv(CHECKS/'module_coverage.csv',index=False,encoding='utf-8-sig')
    # O1 severity rate and complete valid-item coverage per household.
    o1=modules['O1']; o1cols=[f'o1_01_{i}' for i in range(1,21) if f'o1_01_{i}' in o1]
    o1_rows=[]
    for c in o1cols:
        s=o1[c].map(clean); known=s.isin({'1','2','3'}); severe=s.eq('1'); moderate=s.eq('2')
        o1_rows.append({'research_label':LABEL,'item':c,'valid_count':int(known.sum()),'blank_count':int(s.isna().sum()),'outside_expected_count':int((s.notna()&~s.isin({'1','2','3'})).sum()),'code_1_count':int(severe.sum()),'code_2_count':int(moderate.sum()),'rate_code_1_or_2_among_valid':float((severe|moderate).sum()/known.sum()) if known.sum() else None})
    pd.DataFrame(o1_rows).to_csv(CHECKS/'o1_item_rates.csv',index=False,encoding='utf-8-sig')
    o1valid=o1[o1cols].apply(lambda r:sum(clean(x) in {'1','2','3'} for x in r)==20,axis=1)
    pd.DataFrame([{'research_label':LABEL,'households_all_20_valid':int(o1valid.sum()),'households_with_any_missing_or_invalid':int((~o1valid).sum())}]).to_csv(CHECKS/'o1_all_items_valid.csv',index=False,encoding='utf-8-sig')
    # One summary checks file for row structure.
    pd.DataFrame(summary).to_csv(CHECKS/'module_row_structure.csv',index=False,encoding='utf-8-sig')
    # Missingness and dictionary for additions.
    miss=[]; dictionary=[]
    rules={
      'research_label':('constant','Required research label','metadata'), 'hhcode':('spine','household key','copied'),
      'bank_account':('n2_01','1 yes / 0 no; other and blank remain missing','task-specified'),
      'bank_account_status':('n2_01','valid iff code is 0 or 1; else missing','task-specified'),
      'has_debt':('n1_0','1 yes / 0 no; other and blank remain missing','task-specified; Codebook.zip unavailable for row citation'),
      'has_debt_status':('n1_0','valid iff code is 0 or 1; else missing','task-specified'),
      'n_members_b3_valid':('B3.b3_01','count roster-member records with b3_01 in {0,1}','task-specified'),
      'n_chronic':('B3.b3_01','count valid b3_01 equal to 1','task-specified'),
      'share_chronic':('B3.b3_01','n_chronic / n_members_b3_valid when denominator >=1; otherwise blank','task-specified'),
      'health_status':('B0 roster + B3.b3_01','valid all roster members valid; partial some; missing none','operational definition'),
      'n_o1_items_valid':('O1.o1_01_1..20','count 1/2/3 values; no composite','task-specified')}
    for i in range(1,21): rules[f'o1_01_{i}']=('O1.o1_01_'+str(i),'raw copy; no recode','raw')
    for c in additions:
        src,rule,status=rules.get(c,('', '', ''))
        dictionary.append({'research_label':LABEL,'column':c,'source_variables':src,'rule':rule,'status':status})
        miss.append({'research_label':LABEL,'column':c,'rows':len(additions),'missing_count':int(additions[c].isna().sum()),'missing_share':float(additions[c].isna().mean())})
    pd.DataFrame(dictionary).to_csv(OUT/'column_dictionary.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(miss).to_csv(OUT/'missingness_report.csv',index=False,encoding='utf-8-sig')
    # O1 questionnaire reference-period search (in memory; no free text copied to outputs).
    project_pdf=ROOT/'Data'/'BRIGHT_questionnaire_English.pdf'
    supplied_pdf_note=''
    if USER_QUESTIONNAIRE.exists() and project_pdf.exists() and sha(USER_QUESTIONNAIRE)==sha(project_pdf):
        supplied_pdf_note=f' Supplied PDF SHA-256 matches the project copy: {sha(project_pdf)}.'
    period='O1_01_20 states "in the past 12 months" (Data/BRIGHT_questionnaire_English.pdf, printed page 203). No common reference period is stated for O1_01_1 through O1_01_19 in the reviewed item table (printed pages 201-203).'+supplied_pdf_note
    codebook=ROOT/'Codebook.zip'
    opens=[
      'Codebook.zip was not found at the project root or under the project; requested cleaned-module codebook source rows could not be checked. Counts therefore show observed values, with unverified sets labeled accordingly.',
      'N1 n1_0 and N2 n2_01 use the task-provided 1=yes/0=no mappings; Codebook.zip was unavailable to independently verify the source row. The older domain_review note marks N1 direction unverified; the explicit mapping in this task was used and should be confirmed against the cleaned codebook when available.',
      'B3 b3_01 by b3_03 is a descriptive skip-conflict check only. b3_03 and b3_04 are not used in derived columns.',
      'O1 reference period: '+period+' No O1 composite is constructed (ISS-11).',
      'L3 task lists l3_01..09 and frequency items but does not identify frequency item numbers or skip conditions; no activity-based skip interpretation is made without codebook/questionnaire mapping.',
      'O2 code categories and same-coding lead-item scope require the cleaned Codebook.zip; checks show observed raw values/counts only, and no derived O2 column is created.',
      'Stage 3b implementation and tests are placed under outputs/stage3b to honor the prohibition on modifying pre-existing Stage 3/4 files; no prior pipeline/test file was changed.'
    ]
    (OUT/'open_questions.md').write_text('# Open questions\n\n'+LABEL+'\n\n'+'\n'.join(f'- {x}' for x in opens)+'\n',encoding='utf-8')
    (CHECKS/'read_only_checks.md').write_text('# Stage 3b read-only checks\n\n'+LABEL+'\n\nPer-module CSVs contain observed counts and no free-text values. Codebook.zip was unavailable; see `../open_questions.md`. N1/N2 cross-tabs are descriptive; no inferred code direction is applied. B3 cross-tabs include blank categories. `module_coverage.csv` distinguishes verified valid coverage from nonblank-only coverage.\n',encoding='utf-8')
    # Output inventory with hashes/row counts. Inputs are all requested files plus roster/spine and documentation.
    inputs=[SPINE_PATH,DATA/'mod_b0_roster_long.csv']+[DATA/v for v in MODULES.values()]+[BASE/'docs'/'codebook_crosscheck_v0_1.md',BASE/'docs'/'spec_v0_1_decision_log.md',BASE/'review_register'/'domain_review.md',ROOT/'Data'/'BRIGHT_questionnaire_English.pdf']
    inmeta=[]
    for p in inputs:
        if p.exists():
            n=None
            if p.suffix.lower()=='.csv': n=sum(1 for _ in open(p,encoding='utf-8-sig'))-1
            inmeta.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'row_count':n})
        else: inmeta.append({'path':str(p.relative_to(ROOT)),'status':'missing'})
    outputmeta=[]
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts:
            n=None
            if p.suffix.lower()=='.csv': n=sum(1 for _ in open(p,encoding='utf-8-sig'))-1
            outputmeta.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'row_count':n})
    manifest={'research_label':LABEL,'pipeline_version':'0.3.0','inputs':inmeta,'outputs':outputmeta,'household_rows':len(additions),'notes':['No scores/ranks/imputation. label_high_vuln and pc_cons excluded.','Codebook.zip unavailable.']}
    if USER_QUESTIONNAIRE.exists():
        manifest['supplemental_user_supplied_inputs']=[{'path':str(USER_QUESTIONNAIRE),'sha256':sha(USER_QUESTIONNAIRE),'byte_identical_to_project_copy':sha(USER_QUESTIONNAIRE)==sha(ROOT/'Data'/'BRIGHT_questionnaire_English.pdf')}]
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    # Summary with coverage and B3 skip cross-tab counts.
    b3skip=pd.crosstab(cat(b3.b3_01),cat(b3.b3_03),dropna=False)
    coverage=pd.DataFrame(cov)
    lines=['# Stage 3b summary','',LABEL,'','## Built','',f'- Read-only checks for seven modules; additions table has {len(additions):,} unique spine households.','- Outputs include raw O1 items and limited B1–B3 additions; no model, score, ranking, or imputation.','- N1 and N2 binary indicators use the explicit task mapping; N1 direction should be confirmed against the cleaned Codebook.zip when available.','- No label_high_vuln or pc_cons fields were read into the additions.','', '## Module coverage','', '| Module | Spine households with valid/nonblank response | Status |','|---|---:|---|']
    for _,r in coverage.iterrows(): lines.append(f"| {r['module']} | {r['spine_households_with_valid_answer']:,} | {r['validity_note']} |")
    lines+=['','## B3 b3_01 by b3_03','', '| b3_01 | b3_03 | Count |','|---|---|---:|']
    for (a,b),v in b3skip.stack(dropna=False).items(): lines.append(f'| {a} | {b} | {int(v):,} |')
    lines+=['',f"The skip conflict is pronounced: all {int(b3skip.loc['0','[BLANK]']):,} records with b3_01=0 have b3_03 blank; {int(b3skip.loc['1','[BLANK]']):,} records with b3_01=1 also have b3_03 blank."]
    all20=int(o1valid.sum())
    lines+=['','## O1 item completeness','',f'- Households with all 20 valid O1 items: {all20:,}. Per-item counts/rates are in `checks/o1_item_rates.csv`.','', '## Validation','',f'- Spine and additions rows: {len(additions)}; unique keys: {additions.hhcode.nunique()}.','- Household-level module joins used one-to-one validation; B3 member keys checked for uniqueness.','- share_chronic is null when no valid b3_01; where present it is constrained to [0,1].','- Household-level CSV outputs are ignored by the repository .gitignore rule for CSVs.','', '## Open questions','']
    lines += [f'- {x}' for x in opens]
    (OUT/'stage3b_summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # Refresh manifest to include summary/open questions created after first inventory.
    outputmeta=[]
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts:
            n=sum(1 for _ in open(p,encoding='utf-8-sig'))-1 if p.suffix.lower()=='.csv' else None
            outputmeta.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'row_count':n})
    manifest['outputs']=outputmeta
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

if __name__=='__main__': main()
