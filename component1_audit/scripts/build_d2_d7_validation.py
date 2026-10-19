"""Read-only D2-D7 descriptive validation; emits no model features."""
from pathlib import Path
import re
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'Data'/'processed'/'clean'
OUT=ROOT/'component1_audit'/'outputs'/'d2_d7_validation'
PREP=ROOT/'Data'/'processed'/'hh_indicators.csv'
QREF={
 'D2':'Questionnaire PDF pp.177-182 (L1 women and L2 men forms)',
 'D3':'Questionnaire PDF pp.7-8 (B0 age); pp.12-13 (B3 health)',
 'D4':'Questionnaire PDF pp.139-146 (H1); pp.146-150 (H2)',
 'D5':'Questionnaire PDF pp.201-203 (O1); F3/F7 season modules as cited in item text',
 'D6':'Questionnaire PDF pp.203-208 (O2 coping)',
 'D7':'Questionnaire PDF pp.197-200 (N1 debt, N2 savings, N3 women savings)',
}
FILES={
 'D2_L1':'mod_l1_food_security_w.csv','D2_L2':'mod_l2_food_security_m.csv',
 'D3_B0':'mod_b0_roster_long.csv','D3_B1':'mod_b1_roster_long.csv','D3_B3':'mod_b3_roster_long.csv',
 'D4_H1':'mod_h1_primary_employment_long.csv','D4_H2':'mod_h2_secondary_employment_lon.csv',
 'D5_O1':'mod_o1_shocks.csv','D5_F3':'mod_f3_ag_maha_2023-2024.csv','D5_F7':'mod_f7_ag_maha_2024-2025.csv',
 'D5_F1':'mod_f1_ag_seasons.csv','D5_G1':'mod_g1_livestock.csv','D5_G2':'mod_g2_fish.csv','D5_I':'mod_i_nonfarm_business.csv',
 'D6_O2':'mod_o2_coping.csv','D7_N1':'mod_n1_debt.csv','D7_N2':'mod_n2_savings.csv','D7_N3':'mod_n3_savings_w.csv',
}

def read(name): return pd.read_csv(DATA/name,low_memory=False,dtype={'hhcode':'string','pid':'string','hhmember':'string'})
def pct(n,d): return round(100*n/d,4) if d else ''
def main():
    frames={k:read(v) for k,v in FILES.items()}
    master=read('mod_a_household_identification.csv')
    h1=frames['D4_H1']; h2=frames['D4_H2']; b0=frames['D3_B0']; b3=frames['D3_B3']
    checks=[]
    def keycheck(label,df,keys):
        checks.append((label,len(df),int(df[keys].isna().any(axis=1).sum()),int(df.duplicated(keys).sum())))
    keycheck('master',master,['hhcode'])
    for k,df in frames.items(): keycheck(k,df,['hhcode','pid'] if k in ('D3_B0','D3_B1','D3_B3') else ['hhcode','hhmember'] if k in ('D4_H1','D4_H2') else ['hhcode'])
    assert all(m==0 and d==0 for _,_,m,d in checks)
    rosterkeys=set(map(tuple,b0[['hhcode','pid']].to_numpy()))
    b3keys=set(map(tuple,b3[['hhcode','pid']].to_numpy()))
    outside_b3=len(b3keys-rosterkeys)
    h1keys=set(map(tuple,h1[['hhcode','hhmember']].to_numpy())); h2keys=set(map(tuple,h2[['hhcode','hhmember']].to_numpy()))
    h1h2_only_h1=len(h1keys-h2keys); h1h2_only_h2=len(h2keys-h1keys)
    assert outside_b3==0
    masterkeys=set(master.hhcode)
    person_modules={'D3_B0','D3_B1','D3_B3','D4_H1','D4_H2'}
    for key,df in frames.items():
        if df.hhcode.isna().any() or (key not in person_modules and df.hhcode.duplicated().any()):
            raise AssertionError(f'{key} household key incomplete or nonunique at expected grain')
        if not set(df.hhcode).issubset(masterkeys):
            raise AssertionError(f'{key} contains household keys outside master')

    freq=[]; missing=[]
    def profile(domain,form,df,cols,applicability='Not established or unconditional in source item'):
        for col in cols:
            if col not in df: continue
            s=df[col]; n=len(df); miss=int(s.isna().sum()); non=n-miss
            missing.append({'domain':domain,'form_or_module':form,'variable':col,'records':n,'nonmissing':non,'missing':miss,'missing_pct_records':pct(miss,n),'applicability_rule':applicability,'structural_skip_count':'not separable from blank without validated item gate'})
            vc=s.value_counts(dropna=True,sort=False)
            for value,count in vc.items():
                freq.append({'domain':domain,'form_or_module':form,'variable':col,'response_or_value':str(value),'count':int(count),'denominator_nonmissing':non,'denominator_module_records':n,'pct_nonmissing':pct(int(count),non),'pct_module_records':pct(int(count),n)})
            if miss:
                freq.append({'domain':domain,'form_or_module':form,'variable':col,'response_or_value':'[MISSING]','count':miss,'denominator_nonmissing':non,'denominator_module_records':n,'pct_nonmissing':'','pct_module_records':pct(miss,n)})

    for tag,prefix in [('D2_L1','l1'),('D2_L2','l2')]:
        d=frames[tag]; cols=[f'{prefix}_{i:02}' for i in range(1,9)]
        profile('D2',tag,d,[f'{prefix}_answered',*cols], 'Household form-level answer/response; forms remain distinct. Follow-ups conditional on item answers per questionnaire.')
        for i in (6,7,8): profile('D2',tag,d,[f'{prefix}_{i:02}a',f'{prefix}_{i:02}b'], 'Follow-up fields; questionnaire gates reference item Yes and frequency response. Instrument has cross-item gate wording requiring source review.')
    profile('D3','B0 roster',b0,['b0_04_years','b0_04_months'],'Roster member age fields; integer units stated separately as years and months.')
    profile('D3','B3 health',b3,['b3_01','b3_03'],'B3 presence is partial; B3_03 gate text conflicts with B3_01 code list. Do not assume blank means no.')
    # Multiple response B3_02 flags: summarize presence/counts without printing other text.
    b3multi=[c for c in b3 if c.startswith('b3_02_') and c!='b3_02_other']
    if b3multi:
        for c in b3multi: profile('D3','B3 health',b3,[c],'Multiple-response condition flags; questionnaire gate says B3_01=1, conflicting with listed No=1.')
    for c in ['h1_01','h1_04','h1_05','h1_13','h1_08','h1_17']:
        profile('D4','H1 primary employment',h1,[c], 'H1_13 only applies at H1_01=8; H1_05a applies if H1_05=1; other fields follow item-specific universe.')
    months=[c for c in h1 if re.fullmatch(r'h1_05a_\d+',c)]
    profile('D4','H1 primary employment',h1,months,'H1_05a month selections; conditional on H1_05=1.')
    profile('D4','H2 secondary employment',h2,[c for c in h2 if c in ['h1_02','h1_03_1','h1_03_2','h1_03_3']], 'H2 questionnaire H2_02 is not directly named in cleaned export; field correspondence is unresolved.')
    profile('D5','O1 shocks',frames['D5_O1'],[f'o1_01_{i}' for i in range(1,21)],'O1 household shock items; questionnaire period stated for item 20 only; applicable subgroups gated by participation fields.')
    profile('D6','O2 coping',frames['D6_O2'],[f'o2_{i:02}' for i in range(1,19)],'Item-specific conditional applicability; preserve response 2/3/4/5 meanings and blanks.')
    profile('D7','N1 debt',frames['D7_N1'],['n1_0','n1_06_1','n1_06_2','n1_06_3','n1_06_4','n1_06_5','n1_06_6','n1_06_7','n1_06_8','n1_06_9','n1_06_10','n1_06_11','n1_06_12','n1_06_999'],'N1 amount/repayment columns use institution slots; blank may reflect N1_00/no debt or item-specific skip.')
    n1=frames['D7_N1']; amount_cols=[c for c in n1 if re.fullmatch(r'n1_03_(?:\d+)',c)]
    profile('D7','N1 amount slots',n1,amount_cols,'Institution-specific loan amount slots; questionnaire asks amount of loan taken, not explicitly outstanding balance.')
    profile('D7','N2 savings',frames['D7_N2'],['n2_01','n2_02','n2_03','n2_04','n2_05','n2_06','n2_07'],'N2 household form; N2_06 gated by N2_05=1 per questionnaire (code 1=No, 2=Yes).')
    profile('D7','N3 women savings',frames['D7_N3'],['n3_5','n3_6','n3_7'],'Separate women form; questionnaire says N3_05 and N3_06/07; cleaned names differ; N3_06 gated by N3_05=1 as printed (code list 1=No, 2=Yes).')
    # Explicit gate diagnostics; merge validations are one-to-one and do not alter sources.
    def gate_counts(label, gate, gatecol, target, fields, applicable_value='1'):
        left=gate[['hhcode',gatecol]].copy(); right=target[['hhcode',*fields]].copy()
        assert left.hhcode.is_unique and right.hhcode.is_unique
        z=left.merge(right,on='hhcode',how='left',validate='one_to_one',indicator=True)
        assert len(z)==len(left) and z.hhcode.equals(left.hhcode)
        app=z[gatecol].astype('string').eq(applicable_value)
        for field in fields:
            miss=int(z.loc[app,field].isna().sum())
            missing.append({'domain':label.split()[0],'form_or_module':label,'variable':field,'records':int(app.sum()),'nonmissing':int(app.sum())-miss,'missing':miss,'missing_pct_records':pct(miss,int(app.sum())),'applicability_rule':f'{gatecol}={applicable_value}, joined one-to-one by hhcode','structural_skip_count':int((z[gatecol].notna() & ~app).sum()),'applicability_gate_missing_count':int(z[gatecol].isna().sum())})
    f1=frames['D5_F1']; g1=frames['D5_G1']; g2=frames['D5_G2']; biz=frames['D5_I']; o1=frames['D5_O1']; o2=frames['D6_O2']
    for tag,form in [('D5_F3','F3'),('D5_F7','F7')]: profile('D5',form,frames[tag],[c for c in frames[tag] if c in ('f1_00a','f3_00a','f3_00','f3_01a','f7_00','f7_01')], 'Agriculture participation/season gate and season roster fields; blank remains distinct from a No gate.')
    gate_counts('D5 O1 agriculture gate',f1,'f1_00a',o1,['o1_01_11','o1_01_12','o1_01_13','o1_01_16','o1_01_17','o1_01_18'])
    gate_counts('D5 O1 livestock gate',g1,'g1_00a',o1,['o1_01_14'])
    gate_counts('D5 O1 fishing gate',g2,'g2_00',o1,['o1_01_15'])
    # O1 item 18 has alternate business gate; publish both component applicability summaries separately.
    gate_counts('D5 O1 business gate',biz,'i_01',o1,['o1_01_18'])
    gate_counts('D6 O2 agriculture gate',f1,'f1_00a',o2,['o2_05','o2_06'])
    pd.DataFrame(freq).to_csv(OUT/'d2_d7_frequency_report.csv',index=False)
    pd.DataFrame(missing).to_csv(OUT/'d2_d7_missingness_applicability.csv',index=False)

    # D2 prepared value diagnostics: inspect only aggregate distributions and compare response lineage candidates.
    prep=pd.read_csv(PREP,low_memory=False,dtype={'hhcode':'string'}); d2=prep['d2_fies_raw']; frac=int(((d2.dropna()%1)!=0).sum()); d2miss=int(d2.isna().sum())
    l1=frames['D2_L1']; l2=frames['D2_L2']
    d2_diag={'prepared_rows':len(prep),'prepared_d2_missing':d2miss,'prepared_d2_fractional':frac,'l1_answered':int(l1.l1_answered.fillna(0).sum()),'l2_answered':int(l2.l2_answered.fillna(0).sum())}
    # H1_17 duplicate/value disagreement by household, never sum or expose keys.
    h17=h1.groupby('hhcode').h1_17.agg(['count','nunique']); h17non=h1.dropna(subset=['h1_17']).groupby('hhcode').h1_17.nunique()
    h17diag={'households':int(h1.hhcode.nunique()),'households_multiple_h1_records':int((h1.groupby('hhcode').size()>1).sum()),'households_repeated_nonmissing_h1_17':int((h17non==1).sum()),'households_conflicting_nonmissing_h1_17':int((h17non>1).sum()),'households_no_nonmissing_h1_17':int((h17non==0).sum())}
    # N1 raw amount cells versus questionnaire debt response, with zeros and blanks kept distinct.
    debtpos=n1[n1.n1_0.astype('string').eq('1')]; n1allblank=int(debtpos[amount_cols].isna().all(axis=1).sum()); anyzero=int((debtpos[amount_cols].fillna(1).eq(0).any(axis=1)).sum())
    prepcols=[c for c in ['d7_total_debt','d7_has_debt','d7_debt_income_ratio'] if c in prep]
    debtpos_count=int(debtpos.shape[0])
    diagnostics={'d2':d2_diag,'h1_17':h17diag,'d7_n1':{'cleaned_debt_positive_n1_0_1':debtpos_count,'debt_positive_all_amount_slots_missing':n1allblank,'debt_positive_any_explicit_zero_slot':anyzero,'prepared_rows':len(prep),'prepared_d7_fields':prepcols}}
    # prepared score distribution without row-level values
    diagnostics['d2']['fractional_value_counts']={str(k):int(v) for k,v in d2[d2.notna() & (d2%1!=0)].value_counts().items()}

    meta=[]
    domains={
      'D2':('Questionnaire pp.177-182','L1/L2 food-access items refer to the past 12 months; 1 Yes, 2 No, 3 DK, 4 Refused.','Prepared fractional/missing score lineage is unavailable; forms remain distinct.','No FIES scoring or form merge.'),
      'D3':('Questionnaire pp.7-8, 12-13','B0 years/months are separate integers; B3_01 combines chronic illness/severe disability; B3_03 is activity interruption.','B3_01 code/skip conflict; B3 coverage partial; no approved age cutoffs.','No thresholds, conversions or household aggregates.'),
      'D4':('Questionnaire pp.139-146','H1_01 current status; H1_05 prior 12 months; H1_13 job search last four weeks conditional on status 8; H1_17 monthly household income LKR.','H2_02-to-clean h1_02 unresolved; H1_17 repeated by member records; informality/irregularity not directly measured.','No person-to-household aggregation.'),
      'D5':('Questionnaire pp.201-203','O1 codes 1 severe, 2 moderate, 3 no impact; item 20 explicitly past 12 months.','Other item periods and conditional applicability unresolved; F3/F7 are distinct seasons.','No shock counts or severity scores.'),
      'D6':('Questionnaire pp.203-208','O2 categories distinguish Yes, no because unnecessary, discontinued action, N/A and prefer not to say.','Conditional gates and follow-ups require review; preserve category values.','No used/exhausted flags, counts or scores.'),
      'D7':('Questionnaire pp.197-200','N1_00 questionnaire codes 1/2; N2_01 is bank account; N2/N3 savings capacity refers to prior 12 months.','Clean code direction unresolved; amount taken is not verified balance; N2/N3 are separate forms.','No debt totals/ratios, source counts, or savings composite.'),
    }
    candidates={
      'D2':[('d2_fies_raw','L1_01-08 / L2_01-08','L1 and L2 answered flags'),],
      'D3':[('d3_dep_ratio','B0_04_years/months','dependency bands/formula absent'),('d3_share_child','B0_04_years/months','child boundary/denominator absent'),('d3_share_elderly','B0_04_years/months','older-age boundary/denominator absent'),('d3_any_disability','B3_01/B3_02','combined chronic illness and severe disability; not disability-only'),('d3_chronic_share','B3_01/B3_02','chronic-only status not directly identified'),('d3_activity_limited_share','B3_03','member categories; category 7 refers to >12 months'),],
      'D4':[('d4_n_unemp_seeking','H1_01/H1_13','current status plus conditional recent job search'),('d4_unemployed_12m','H1_05/H1_05a','past-year unemployment and month flags'),('d4_n_workers','H1_01/H2_02','worker status and second-job mapping/definition unresolved'),('d4_no_worker','H1_01/H2_02','worker definition and missingness unresolved'),('d4_irregular_share','H1_08','payment frequency alone does not establish irregularity'),('d4_informal_share','H1_04/H1_11','agreement/payment modes alone do not establish informality'),('d1_income_month (D1-D4 overlap)','H1_17','household income field repeated on H1 member records'),],
      'D5':[('d5_n_shocks_any','O1_01_1-20','raw household items; periods/gates unresolved'),('d5_n_shocks_severe','O1_01_1-20','aggregation not approved'),('d5_severity','O1_01_1-20','severity codes verified; score not defined'),('d5_price_shock','O1_01_1,2,5,6','item wording; periods unresolved'),('d5_income_shock','O1_01_3,4','financial/income loss items; periods unresolved'),('d5_health_shock','O1_01_7','health/death/injury household shock'),('d5_climate_shock','O1_01_*','item mapping and period require review'),('d5_agri_shock','O1_01_11-18; F3/F7','conditional agriculture/exposure; seasons separate'),],
      'D6':[('d6_used','O2_01-18','raw multi-category responses'),('d6_exhausted','O2_01-18','discontinued-action response is not a generic exhaustion flag'),('d6_stress_share','O2_01-18','denominator and binary mapping not approved')],
      'D7':[('d7_has_debt','N1_00 / cleaned n1_0','code direction needs lineage'),('d7_total_debt','N1_03 source slots','amount taken; outstanding balance and aggregation unresolved'),('d7_n_debt_sources','N1_01/N1_03 slots','source-count definition not approved'),('d7_hard_to_repay','N1_06 source slots','item/follow-up universe requires source review'),('d7_has_bank_account','N2_01','correct candidate source is N2_01, not N2_02'),('d7_able_to_save','N2_05 and N3_05','distinct household and women forms; do not combine'),('d7_n_income_sources','H1/I/F1/G1','source list and universe unsupported'),('d7_debt_income_ratio','N1 prepared total/H1_17','both numerator lineage and repeated household income need resolution')],
    }
    for domain,items in candidates.items():
        ref,sem,finding,boundary=domains[domain]
        for candidate,source,note in items:
            meta.append({'domain':domain,'candidate_or_construct':candidate,'source_fields':source,'verified_questionnaire_semantics':sem,'questionnaire_reference':ref,'validation_finding_or_unresolved_issue':finding+' Candidate-specific note: '+note,'implementation_boundary':boundary})
    pd.DataFrame(meta).to_csv(OUT/'d2_d7_indicator_validation.csv',index=False)

    overlaps=[
      ('D1 income ↔ D4 livelihood','H1_17 is household monthly income recorded on person employment rows; employment status/search captures earning capacity and labor-market exposure.','Income may be repeated on each H1 person row; do not sum. Keep current labor status, past-year unemployment, and household income conceptually separate; inspect correlation only after validated representation.','No final redundancy decision.'),
      ('D1 housing/crowding ↔ D3 household needs','Bedroom count/material context may covary with household size, ages, and member needs.','Avoid interpreting bedroom count as crowding without approved numerator, denominator and cutoff; avoid duplicate household-size effects across dependency candidates.','No age bands or crowding formula approved.'),
      ('D2 food insecurity ↔ D6 food-related coping','Food access responses may overlap coping actions involving food expenditure/consumption (notably O2_11/O2_12 per provisional map).','Preserve each item and reference period; compare only after gates and response meanings are validated.','No automatic exclusion or score.'),
      ('D5 shocks ↔ D4 income/employment changes','O1 shocks may report employment/income loss also observed in H1 current/past-year status.','Different reference periods and respondent framing can create apparent disagreement; O1 nonresponse must not mean no exposure.','O1 periods/applicability unresolved.'),
      ('D3 health conditions ↔ D5 health shocks','B3 chronic illness/disability and O1 serious illness/death/injury describe related but different constructs and units.','B3 is member-level and conditional; O1 is household shock response. Preserve level and period separately.','B3 code/skip conflict and O1 period unresolved.'),
      ('D6 coping ↔ D7 debt/savings/asset depletion','Coping actions may include borrowing, asset sale, drawing savings, or inability to save.','These can represent actions and capacity/outcomes; correlated items need not be removed automatically. Keep N2/N3 and N1 independent pending crosswalk.','No debt/savings or coping aggregation.'),
    ]
    pd.DataFrame([{'overlap_pair':a,'why_overlap_may_matter':b,'validation_handling':c,'researcher_decision_pending':d} for a,b,c,d in overlaps]).to_csv(OUT/'cross_domain_overlap_register.csv',index=False)

    issues=[
      ('CRITICAL','D2','Prepared d2_fies_raw includes fractional values and missing cases with no recoverable scoring/combination code.','The present candidate cannot be reproduced or interpreted as a valid household FIES score.','Recover transformation, respondent selection, partial response and DK/refusal rules; retain L1/L2 separately until approved.'),
      ('CRITICAL','D7','Prepared debt totals/ratios cannot be validated from raw fields; debt-positive households have all amount fields blank and raw N1_03 asks amount taken.','Potentially invalid debt burden and denominator; loan disbursement may not equal current debt.','Trace source selection and define outstanding balance; never sum repeated H1_17.'),
      ('HIGH','D3','B3_01 listed Yes/No codes contradict skip condition; partial B3 member coverage.','Eligible denominator and health/activity interpretation uncertain.','Confirm instrument/export version; quantify coverage; do not roll to household.'),
      ('HIGH','D4','H2_02 appears as cleaned H2 field h1_02; H1_17 repeats across employment records.','Secondary job crosswalk and income lineage at risk of field misassignment or multiplication.','Validate raw export field map and reconcile household income without summing.'),
      ('HIGH','D5','O1 reference period absent for items 1-19 and blanks include gated non-applicability.','Exposure timing and missing-as-no bias.','Confirm period and gates for each item; keep F3 and F7 separate.'),
      ('HIGH','D6','O2 responses distinguish no-need, discontinued, N/A and prefer-not-to-say.','Binary “used” recodes collapse materially different states.','Retain raw categories and verify each applicable universe.'),
      ('MEDIUM','D7','N1_00 and N2/N3 questionnaire 1/2 versus cleaned 0/1 fields; N3 names differ from questionnaire.','Direction may reverse and N2/N3 could be incorrectly combined.','Trace code lineage; preserve forms separately.'),
      ('MEDIUM','D3','Age recorded separately as integer years and months; dependency boundaries absent.','Thresholds or conversions could change membership classification.','Keep raw units; researcher to choose formula/threshold if needed.'),
      ('MEDIUM','D1↔D4 / D1↔D3 / D2↔D6 / D4↔D5 / D3↔D5 / D6↔D7','Cross-domain overlap may double-count related circumstances or actions.','Correlated signals can influence later composite/model balance.','Review overlap and intended constructs; do not automatically remove any item.'),
    ]
    pd.DataFrame([{'priority':a,'domain_or_pair':b,'issue':c,'validity_implication':d,'recommended_review':e} for a,b,c,d,e in issues]).to_csv(OUT/'d2_d7_issue_register.csv',index=False)

    debtpos_count=int(debtpos.shape[0])
    rep=f'''# Coordinated D2–D7 indicator validation audit\n\n**Status:** descriptive validation only. Domains remain provisional; none of these results approves a final model feature. No fuzzy membership, Bayesian dependency, weight, ranking, eligibility decision, deprivation score, household aggregate, or recoded item was produced.\n\n## Provenance and method\n\nCleaned inputs read from `Data/processed/clean/`: {', '.join(f'`{v}`' for v in FILES.values())}. Prepared comparison input: `Data/processed/hh_indicators.csv` (only for read-only diagnostics of existing D2/D7 prepared values). Questionnaire: `Data/BRIGHT_questionnaire_English.pdf`. Outputs contain aggregate frequencies and validation notes only; no identifiers or personal free-text. The builder is `component1_audit/scripts/build_d2_d7_validation.py`.\n\n## Results by domain\n\n- **D2 Food insecurity.** L1 women and L2 men forms were profiled separately across eight core items and available follow-ups. Questionnaire pp.177–182 specify 12-month food-access experiences with 1 Yes, 2 No, 3 Don't know, 4 Refused. Follow-up wording contains cross-form/item references that need verification. The existing prepared `d2_fies_raw` has {d2_diag['prepared_d2_missing']} missing and {frac} fractional values; fractional values: {d2_diag['fractional_value_counts']}. L1 answered flag totals {d2_diag['l1_answered']}; L2 {d2_diag['l2_answered']}. No source transformation reproduces these prepared outputs; do not score or combine forms.\n- **D3 Household needs.** B0 age years and months remain separate; B3 condition and activity responses are profiled at member level. Roster has {len(b0):,} rows; B3 has {len(b3):,} rows and {outside_b3} B3 keys outside B0. Questionnaire B3_01 lists 1 No/2 Yes but its skip text says B3_01=1; B3_03 code 7 describes complete interruption more than 12 months ago despite the question's last-year frame. No age thresholds, age conversion, or household rollup was applied. Candidate formulas remain alternatives only: age-band shares use an approved age threshold and roster denominator; a dependency ratio needs approved dependent and working-age bands plus denominator.\n- **D4 Livelihood/income.** H1/H2 person records have {len(h1):,}/{len(h2):,} rows; unique `hhcode+hhmember` checks passed. H1/H2 person key sets: {h1h2_only_h1} H1-only and {h1h2_only_h2} H2-only. H1_17 is total monthly household income in LKR, repeated in employment rows; household diagnostics: {h17diag}. It was not summed. H1_05 is past-12-month unemployment; H1_13 is job search in last 4 weeks conditional on H1_01=8. H2_02 wording does not map transparently to cleaned H2 `h1_02`; crosswalk remains unresolved.\n- **D5 Shocks.** O1 response distributions are retained by item; 1=severe, 2=moderate, 3=no impact. Questionnaire explicitly gives past 12 months for item 20; items 1–19 period remains unverified. Gate blanks are not interpreted as no shock. F3 (Maha 2023–24) and F7 (Maha 2024–25) remain separate source modules.\n- **D6 Coping.** O2 items are profiled individually. Preserve distinctions among Yes, No because unnecessary, discontinued action, Not applicable and Prefer not to say; do not reduce these to used/exhausted flags. O2_05/O2_06 have the F1_00a=1 gate, and follow-up checkboxes depend on Yes responses. The O2 source is separate from O1.\n- **D7 Financial resilience.** N1, N2 and N3 remain separate. N1_00 cleaned values and questionnaire codes differ; raw amount slots are preserved as frequency/missingness summaries. Among {debtpos_count:,} records with cleaned N1 status `1`, {n1allblank:,} have all amount slots missing and {anyzero:,} contain an explicit zero amount slot. N1_03 asks amount of loan taken, not verified outstanding balance. The prior issue review also records 20 debt-positive prepared totals at zero and 12 debt-positive cases without positive raw amount slots; this audit did not calculate or replace those totals. N2_01 is bank-account access; N2_02 is savings location. N3 is a separate women's form and field names differ; the existing review found N2/N3 savings responses disagree in 1,453 of 5,393 paired records. No debt/savings sums or ratios were computed.\n\n## Checks actually executed\n\n- Key completeness and uniqueness checked for household master, each household module, and person keys in B0/B1/B3 and H1/H2; 19 file/grain checks passed with zero missing-key rows and zero duplicate-key rows.\n- B3 person keys are a subset of B0; H1/H2 keys compared; no join was performed that could multiply records.\n- Every reported field has frequency and missingness counts with explicit module-record and nonmissing denominators. Explicit 0 values remain separate from blanks.\n- Existing prepared D2 fractional/missing counts and raw N1 amounts were inspected as aggregate diagnostics only. No prepared feature was changed.\n- No aggregation/score reproduction, sample disposition reconciliation, or raw-to-clean transformation replay was possible from available scripts; those were not executed.\n\n## Priority issues and researcher review choices\n\n1. **Critical – D2 score provenance:** recover respondent selection, item-level scoring, partial response and DK/refusal handling; alternatively leave L1/L2 item-level only.\n2. **Critical – D7 debt meaning:** decide whether N1 amount-taken fields can support a debt-burden construct; obtain current balance/source lineage before any total.\n3. **High – D3 and D4 semantic crosswalks:** resolve B3 code/skip contradictions and H2_02-to-clean-field mapping.\n4. **High – D5 applicability/reference periods and D6 response semantics:** verify gated missingness and periods; retain category detail.\n5. **Medium – form combinations, age thresholds and overlap:** choose only after evidence review; N2/N3 and F3/F7 remain separate until an approved crosswalk/target period exists.\n\nCandidate alternatives are: (a) keep raw items/form-specific descriptions; (b) define a documented item-level construct and eligible denominator after source clarification; or (c) defer the candidate. These are review choices, not recommendations to implement now. The cross-domain register explains overlap without removing correlated items. The bottom-quintile consumption proxy was not used as ground truth or a model feature.\n'''
    (OUT/'d2_d7_validation_report.md').write_text(rep,encoding='utf-8')
    print(f"D2-D7 outputs written; key checks={len(checks)}; B3 outside roster={outside_b3}; H1/H2 key differences={h1h2_only_h1}/{h1h2_only_h2}; D2 fractional={frac}, missing={d2miss}; debt-positive all amount blank={n1allblank}.")

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True); main()
