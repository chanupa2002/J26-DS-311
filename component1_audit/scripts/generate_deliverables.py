"""Local report/workbook generator for the BRIGHT Component 1 audit.

Uses only local files. The R entry point is the reproducible analysis workflow;
this helper writes the review workbook/report in the current R-less environment.
"""
from pathlib import Path
import csv, json, re, zipfile, html
from xml.sax.saxutils import escape
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = Path(__import__('os').environ.get('BRIGHT_CLEAN_DIR', r'C:\data\processed\clean'))
PROCESSED = Path(__import__('os').environ.get('BRIGHT_PROCESSED_DIR', r'C:\data\processed'))
if not CLEAN.exists():
    CLEAN = ROOT.parent / 'Data' / 'processed' / 'clean'
if not PROCESSED.exists():
    PROCESSED = ROOT.parent / 'Data' / 'processed'
OUT = ROOT / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)

grain_hints = {
    'mod_b0_roster_long':'person roster', 'mod_b1_roster_long':'person roster',
    'mod_b2_roster_long':'person roster', 'mod_b3_roster_long':'person health records',
    'mod_e_land_long':'plot/parcel', 'mod_h1_primary_employment_long':'person primary-employment record',
    'mod_h2_secondary_employment_lon':'person with secondary-job slots', 'mod_j1_fah_long':'food item',
    'mod_j2_fafh-bevs_long':'food-away-from-home item', 'mod_j2_fafh-meals_long':'food-away-from-home item',
    'mod_j2_fafh-snacks_long':'food-away-from-home item', 'mod_k_nfe_long':'non-food expenditure item and period',
    'mod_f2_ag_yala_2024_long':'season-crop', 'mod_f3_ag_maha_2023-2024_long':'season-crop',
    'mod_f3_ag_maha_2023_2024_long':'season-crop duplicate export', 'mod_f4_ag_yearly_long':'season-crop',
    'mod_f6_ag_perennial_crops_long':'season-crop', 'mod_s2_anthro_long':'person anthropometry record',
    'mod_s3_anthro_long':'person/measurement record', 'mod_r1_cash_long':'household-program record',
    'mod_r2_inkind_long':'household-program record', 'mod_r4_informal-support_long':'household-support record',
}

def read_keys():
    p=PROCESSED/'cleaning_log.csv'
    if not p.exists(): return {}
    d=pd.read_csv(p, dtype=str).fillna('')
    return {r.sheet: [s.strip() for s in r.key_cols.split('+') if s.strip()] for r in d.itertuples()}

keys_by_file=read_keys()
inventory=[]
missingness_rows=[]
for f in sorted(CLEAN.glob('*.csv')):
    # Read as strings to preserve codes and identifiers; pandas infers schema from observed content below.
    d=pd.read_csv(f, dtype='string', keep_default_na=False, na_values=['','NA'], low_memory=False)
    stem=f.stem
    keys=keys_by_file.get(stem, ['hhcode'] if 'hhcode' in d.columns else [])
    keys=[k for k in keys if k in d.columns]
    dup=int(d.duplicated(keys).sum()) if keys else None
    miss={c:int(d[c].isna().sum()) for c in d.columns if d[c].isna().any()}
    for c in d.columns:
        missingness_rows.append({'filename':f.name,'variable':c,'missing_n':int(d[c].isna().sum()),'pct_missing':100*float(d[c].isna().mean())})
    types={}
    for c in d.columns:
        x=d[c].dropna()
        if not len(x): typ='all_missing'
        elif x.str.fullmatch(r'(0|1|TRUE|FALSE)',case=False).all(): typ='binary_like'
        elif pd.to_numeric(x,errors='coerce').notna().all(): typ='numeric'
        else: typ='text_or_code'
        types[c]=typ
    grain=grain_hints.get(stem, 'household-shaped; one row per household in this export' if len(keys)==1 and keys[0].startswith('hhcode') else 'entity grain to confirm')
    inventory.append({'filename':f.name,'rows':len(d),'columns':len(d.columns),
        'variable_names':' | '.join(d.columns),'variable_types':' | '.join(f'{k}:{v}' for k,v in types.items()),
        'key_fields':'+'.join(keys),'key_missing_rows':int(d[keys].isna().any(axis=1).sum()) if keys else None,
        'duplicate_key_rows':dup,'observation_grain':grain,
        'missingness_by_variable':' | '.join(f'{k}:{v} ({100*v/len(d):.2f}%)' for k,v in miss.items())})
pd.DataFrame(inventory).to_csv(OUT/'module_inventory.csv',index=False)
pd.DataFrame(missingness_rows).to_csv(OUT/'module_missingness.csv',index=False)

ind=pd.read_csv(PROCESSED/'hh_indicators.csv') if (PROCESSED/'hh_indicators.csv').exists() else pd.DataFrame()
ctx=pd.read_csv(PROCESSED/'hh_context.csv') if (PROCESSED/'hh_context.csv').exists() else pd.DataFrame()
varmap=pd.read_csv(PROCESSED/'variable_map.csv').fillna('') if (PROCESSED/'variable_map.csv').exists() else pd.DataFrame()
cleanlog=pd.read_csv(PROCESSED/'cleaning_log.csv').fillna('') if (PROCESSED/'cleaning_log.csv').exists() else pd.DataFrame()
miss_report=pd.read_csv(PROCESSED/'missingness_recomputed.csv').fillna('') if (PROCESSED/'missingness_recomputed.csv').exists() else pd.DataFrame()
sent=pd.read_csv(PROCESSED/'sentinel_log.csv').fillna('') if (PROCESSED/'sentinel_log.csv').exists() else pd.DataFrame()
outliers=pd.read_csv(PROCESSED/'outlier_report.csv').fillna('') if (PROCESSED/'outlier_report.csv').exists() else pd.DataFrame()

groups={
 'D1':'Economic and material well-being','D2':'Food insecurity','D3':'Household needs and dependency',
 'D4':'Livelihood and income security','D5':'Shocks and exposure','D6':'Coping stress','D7':'Financial resilience and adaptive capacity'}
module_hints={
 'd1_':['mod_h1_primary_employment_long','mod_c_housing','mod_d_assets','mod_b0_roster_long'],
 'd2_':['mod_l1_food_security_w','mod_l2_food_security_m'],
 'd3_':['mod_b0_roster_long','mod_b1_roster_long','mod_b3_roster_long'],
 'd4_':['mod_h1_primary_employment_long','mod_h2_secondary_employment_lon'],
 'd5_':['mod_o1_shocks'], 'd6_':['mod_o2_coping'],
 'd7_':['mod_n1_debt','mod_n2_savings','mod_n3_savings_w','mod_h1_primary_employment_long','mod_i_nonfarm_business','mod_f1_ag_seasons','mod_g1_livestock']}
sources={
 'd1_income_month':('mod_h1_primary_employment_long','h1_17','What is your total monthly household income? in LKR','Integer; no special codes documented for this item','Monthly household income'),
 'd1_income_pc':('mod_h1_primary_employment_long; mod_b0_roster_long','h1_17; roster-derived household size','Household income question above; roster member count','Numeric; household size derived from roster','Monthly income per capita'),
 'd1_income_missing':('mod_h1_primary_employment_long','h1_17','Household income question above','Integer; missing/unknown distinction needs source cleaning logic','Current feature is missingness flag; formula not documented'),
 'd1_poor_walls':('mod_c_housing','c1_04','What is the principal material used in construction for the walls in your house?','Select one; questionnaire lists material categories and 999 Other','Current feature recode not documented'),
 'd1_poor_roof':('mod_c_housing','c1_05','What is the principal material used in construction for the roof in your house?','Select one; inspect full response list in questionnaire','Current feature recode not documented'),
 'd1_poor_floor':('mod_c_housing','c1_06','What is the principal material used in construction for the floor in your house?','Select one; inspect full response list in questionnaire','Current feature recode not documented'),
 'd1_bad_toilet':('mod_c_housing','c1_08','What kind of toilet facility do members of your household usually use?','Select one; 1–3 categories listed; see questionnaire for full list','Current feature recode not documented'),
 'd1_crowded':('mod_c_housing; mod_b0_roster_long','c1_02; roster-derived member count','C1_02: How many bedrooms are in your main dwelling?; B0_00 asks household member count','Bedroom count integer; roster count derived','Crowding formula/cutoff not documented'),
 'd1_weak_tenure':('mod_c_housing','c1_07','What is the ownership status of your main dwelling?','Select one; 999 Other','Current feature recode not documented'),
 'd1_housing_deprivation':('mod_c_housing','c1_04; c1_05; c1_06; c1_08; c1_02; c1_07','See item-specific wording above and in questionnaire','Mixed categorical and integer responses','Composite rule and direction require review'),
 'd1_asset_share':('mod_d_assets','d_* asset ownership/functionality items','Module D questions ask counts/functionality of household assets','Mixed binary and integer; exact included items not in prepared variable map','Share denominator and missing treatment unknown'),
 'd2_fies_raw':('mod_l1_food_security_w; mod_l2_food_security_m','l1_01–l1_08; l2_01–l2_08','Eight experiences: worry about food; unable to eat healthy/nutritious food; limited variety; skipped meals; ate less; ran out of food; hungry but did not eat; went a whole day without eating. Each asks whether this occurred due to lack of money/resources.','Items: 1 Yes, 2 No, 3 Don’t know, 4 Refused; frequency follow-ups have separate codes','Last 12 months; respondent selection and partial-response scoring require approval'),
 'd3_dep_ratio':('mod_b0_roster_long','b0_04_years; household roster rows','B0_04_years: What is MEMBER’s age in years?','Integer; age missingness and thresholds need approval','Ratio denominator/age bands not documented'),
 'd3_share_child':('mod_b0_roster_long','b0_04_years','Age in years','Integer; missing age treatment unresolved','Child age cutoff/formula not documented'),
 'd3_share_elderly':('mod_b0_roster_long','b0_04_years','Age in years','Integer; missing age treatment unresolved','Elderly age cutoff/formula not documented'),
 'd3_any_disability':('mod_b3_roster_long','b3_01–b3_04','Module B3 asks about member health/disability/activity limitations; item wording must be aligned to each field','Mixed coded responses; codebook required','Household any/aggregation rule not documented'),
 'd3_chronic_share':('mod_b3_roster_long','b3_01–b3_04','Module B3 health questions; exact chronic-condition item not resolved from prepared map','Codes require item-specific verification','Share denominator and missingness unknown'),
 'd3_activity_limited_share':('mod_b3_roster_long','b3_01–b3_04','Module B3 health questions; exact activity-limitation item not resolved from prepared map','Codes require item-specific verification','Share denominator and missingness unknown'),
 'd4_n_workers':('mod_h1_primary_employment_long; mod_h2_secondary_employment_lon','h1_01–h1_08; H2 fields stored with h1_* names','Employment module asks current job/activity, sector, status and work characteristics','Mixed employment codes; item mapping needs preprocessing script','Count/eligibility rule for worker not documented'),
 'd4_n_unemp_seeking':('mod_h1_primary_employment_long','h1_14; h1_15; h1_15a','Questionnaire employment status and job search questions; exact wording needs field-level lookup','Coded response; full code list to confirm','Reference period and person aggregation need review'),
 'd4_irregular_share':('mod_h1_primary_employment_long','h1_04; h1_05','Employment status/regularity items; exact field wording needs source script crosswalk','Categorical codes; interpretation pending','Share denominator/missing treatment unknown'),
 'd4_informal_share':('mod_h1_primary_employment_long','h1_08; related contract/social protection fields','Employment module contains work/contract conditions; exact field mapping pending','Coded responses; codebook needed','Share denominator/missing treatment unknown'),
 'd4_unemployed_12m':('mod_h1_primary_employment_long','h1_15–h1_16','Employment module includes prior unemployment and prior job earnings questions','Coded response and integer earnings; period wording field-specific','Household aggregation rule not documented'),
 'd4_no_worker':('mod_h1_primary_employment_long; mod_b0_roster_long','employment records; roster members','Employment and roster modules','Mixed; no worker definition documented','Unknown vs no working-age member distinction needed'),
 'd5_n_shocks_any':('mod_o1_shocks','o1_01_1–o1_01_20','O1 lists household shocks and asks whether impact was severe, moderate, or none','1 severe; 2 moderate; 3 no impact; some items gated by agriculture/livestock/fishing/business status','Past 12 months context; gated items structural inapplicability must remain distinct'),
 'd5_n_shocks_severe':('mod_o1_shocks','o1_01_1–o1_01_20','O1 shock impact questions','1 severe; 2 moderate; 3 no impact','Past 12 months; count aggregation/formula not documented'),
 'd5_severity':('mod_o1_shocks','o1_01_1–o1_01_20','O1 shock impact questions','1 severe; 2 moderate; 3 no impact','Direction and scoring not documented'),
 'd5_price_shock':('mod_o1_shocks','o1_01_1; o1_01_2; o1_01_5; o1_01_6','Higher food prices; higher fuel prices; higher electricity prices; higher taxes','1 severe; 2 moderate; 3 no impact','Past 12 months; combination rule not documented'),
 'd5_income_shock':('mod_o1_shocks','o1_01_3; o1_01_4','Financial shocks; loss of employment/income','1 severe; 2 moderate; 3 no impact','Past 12 months; combination rule not documented'),
 'd5_health_shock':('mod_o1_shocks','o1_01_7','Death, serious illness, or serious injury of family members','1 severe; 2 moderate; 3 no impact','Past 12 months'),
 'd5_climate_shock':('mod_o1_shocks','o1_01_9–o1_01_13','Floods/heavy rain, landslide, unpredictable weather, drought/heat, crop pests/disease; some gated by farm status','1 severe; 2 moderate; 3 no impact','Past 12 months; structural skips must be resolved'),
 'd5_agri_shock':('mod_o1_shocks','o1_01_11–o1_01_18','Agricultural/livestock/fishing shocks gated by F1_00a, G1_00a, G2_00 or I_01','1 severe; 2 moderate; 3 no impact','Past 12 months; inapplicable vs no shock unresolved'),
 'd6_used':('mod_o2_coping','o2_01–o2_18 selected coping items','O2 items ask whether coping mechanisms were used in the past 12 months, including borrowing, asset mortgage/sale, reduced spending and extra work','Usually 1 Yes, 2 No because unnecessary, 3 could not continue prior strategy, 4 N/A, 5 prefer not to say; item-specific exceptions apply','Past 12 months; core 14 list/score requires approved crosswalk'),
 'd6_exhausted':('mod_o2_coping','o2_01–o2_18 selected coping items','Coping questions distinguish no need from inability to continue a prior strategy','Item-specific codes include 1–5; verify each question','Past 12 months; formula and overlapping food items need review'),
 'd6_stress_share':('mod_o2_coping','o2_01–o2_18 selected coping items','O2 coping module','Item-specific codes; no global recode','Past 12 months; denominator and missing treatment unknown'),
 'd7_has_debt':('mod_n1_debt','n1_0; n1_01_*','N1_00: Do you or your household owe any money to a formal or informal institution, shop, friend, or relative?','Questionnaire: 1 No; 2 Yes. Cleaned n1_0 observed values: 0/1; recode crosswalk unresolved.','Current debt; check cleaned column recode, label in raw instrument'),
 'd7_total_debt':('mod_n1_debt','n1_03_1–n1_03_12; n1_03_999','N1_03: How much was the loan you took from the institution?','Integer amount per creditor/source; missing is not evidence of zero','Current loan amounts; sum only after resolving missing and source slot semantics'),
 'd7_n_debt_sources':('mod_n1_debt','n1_01_1–n1_01_12; n1_01_999','N1_01 asks which institutions/people are owed money','Multi-select source codes; 999 Other in source selection','Current debt; distinct-source count rule not documented'),
 'd7_hard_to_repay':('mod_n1_debt','n1_06_*','Debt module repayment difficulty/repayment fields; exact wording mapping needs field lookup','Codes pending codebook/script crosswalk','Reference period and aggregation not documented'),
 'd7_has_bank_account':('mod_n2_savings; mod_n3_savings_w','n2_02_*; n3_*','Savings module includes financial-account/access questions; exact selected field requires source crosswalk','Codes pending codebook/script crosswalk','Household vs respondent combination rule unknown'),
 'd7_able_to_save':('mod_n2_savings; mod_n3_savings_w','n2_05; n3_5','N2_5/N3_05: In the last 12 months do you feel like you have been able to save any money?','Questionnaire: 1 No; 2 Yes. Cleaned n2_05/n3_5 observed values: 0/1; recode crosswalk unresolved.','Past 12 months; male/female respondent reconciliation needs approval'),
 'd7_n_income_sources':('mod_h1_primary_employment_long; mod_i_nonfarm_business; agriculture/livestock modules','income-source indicators across employment/business/agriculture','Household livelihoods modules; exact constructed source list not documented','Mixed coded responses and monetary values','Source count, period and missing/inapplicable treatment unknown'),
 'd7_debt_income_ratio':('mod_n1_debt; mod_h1_primary_employment_long','N1_03_*; h1_17','Loan amount plus monthly household income question','Loan amount integer; h1_17 monthly LKR, but repeated across person records','Debt/income period alignment, zero/unknown income denominator and extreme ratio policy unresolved'),
}

def domain(c): return 'D'+c[1] if re.match(r'd[1-7]_',c) else 'Other'
mapping=[]
page_ref={'D1':'questionnaire pp.14–21, 146','D2':'questionnaire pp.178–182','D3':'questionnaire pp.7–13',
          'D4':'questionnaire employment module pp.140–146','D5':'questionnaire pp.201–203',
          'D6':'questionnaire pp.203–208','D7':'questionnaire pp.197–200'}
for c in [x for x in ind.columns if x!='hhcode'] if len(ind) else []:
    d=domain(c); src,vars_,word,codes,period= sources.get(c,('','', 'Question wording not verified','Not verified','Not verified'))
    expected='Higher value indicates greater vulnerability' if d not in ('D7',) else 'Mixed/indicator-specific direction; requires review'
    if c in ('d1_asset_share','d7_able_to_save','d7_has_bank_account'): expected='Likely higher value indicates greater resilience; direction requires review'
    agg='Household-level feature already prepared; reproduce exact aggregation from missing preprocessing script before use'
    if any(x in src for x in ('roster','employment','expenditure','debt','agriculture')):
        agg='Aggregate this source module to hhcode independently before joining; exact current rule unavailable'
    mapping.append({'candidate_indicator':c,'proposed_construct':groups.get(d,''),'candidate_source_modules':src,
        'candidate_source_variables':vars_,'questionnaire_wording_or_item_label':word,'response_codes_or_units':codes,
        'reference_period':period,'proposed_aggregation_rule':'UNRESOLVED: '+agg,
        'expected_direction':expected,'missing_data_treatment':'Preserve NA separately from observed zero; apply no recode until skip/refusal code semantics and current derivation are verified.',
        'evidence':f'Data/BRIGHT_questionnaire_English.pdf, {page_ref.get(d,"page not verified")} (item text only, where explicitly quoted); Data/processed/variable_map.csv (domain/source notes); prepared hh_indicators.csv (candidate names). Preprocessing script absent; provisional, not validated.'})
mapping_df=pd.DataFrame(mapping)

# Key diagnostic counts based on prepared artifacts only; no row-level identifiers emitted.
fies_frac=int(((ind['d2_fies_raw'].dropna()%1)!=0).sum()) if 'd2_fies_raw' in ind else None
fies_missing=int(ind.d2_fies_raw.isna().sum()) if 'd2_fies_raw' in ind else None
hh_key_unique=bool(ind.hhcode.is_unique and ind.hhcode.notna().all()) if 'hhcode' in ind else False
context_keys=bool(ctx.hhcode.is_unique and ctx.hhcode.notna().all()) if 'hhcode' in ctx else False
join_diff=(len(set(ind.hhcode)^set(ctx.hhcode)) if 'hhcode' in ind and 'hhcode' in ctx else None)
issues=[]
def issue(id, finding, consequence, action, evidence): issues.append({'issue_id':id,'finding':finding,'risk_or_consequence':consequence,'required_review':action,'evidence':evidence})
issue('DQ-01','Special codes vary by item: questionnaire uses 999 for Other in many fields, while some items separately define Don’t know, Refused, Prefer not to say; 998 and 997 appear on some items.','Global sentinel recoding can convert valid categories or unknowns incorrectly.','Confirm each special code by exact variable/item; retain a codebook-driven lookup.','BRIGHT_questionnaire_English.pdf; Data/processed/sentinel_log.csv records some recodes but not semantic rationale.')
issue('DQ-02','Employment h1_17 is a household monthly income question stored on person-level employment rows; 6,663 households have multiple H1 person records and 5,328 have the same nonmissing h1_17 repeated.','Summing repeated h1_17 across member rows can multiply income.','Trace exact current extraction and compare within-household repeated values; choose one household value only after consistency review.','Questionnaire p.146; cleaned mod_h1_primary_employment_long has hhcode + hhmember key; prior outlier report flags h1_17 maximum 27,000,000 and 4 records >10× p99.')
issue('DQ-03','Food expenditure is item-level; nonfood expenditure is item-and-period level.','Zero-filling unanswered/omitted items can understate consumption; summing without period conversion mixes unlike periods.','Reconstruct missingness and period normalization from questionnaire plus preprocessing; no NA-to-zero conversion until approved.','Questionnaire pp.157–158 (J1 past 7 days), pp.173–176 (K_period/K_expend); prior validation report flags label leakage absent but does not validate zero semantics.')
issue('DQ-04',f'Prepared d2_fies_raw has {fies_frac} non-integer values (one each at 0.5, 1.5, and 2.5) and {fies_missing} missing value(s).','A fractional raw FIES score may be an averaging or partial-response artifact and is not the standard binary item count without documented scoring.','Review affected-case patterns securely, respondent selection, eight-item scoring, DK/refusal handling, and female/male form merge.','Questionnaire pp.178–182; prepared hh_indicators.csv and missingness report.')
issue('DQ-05','B0/B1 each have 27,875 rows, unique hhcode+pid keys and no missing ages; B2/B3 are partial/module-specific person records. One B0 age is 101.','Roster duplication or an unverified extreme age can distort denominators and dependency indicators.','Reconcile B0/B1, confirm whether age 101 is valid, and prove roster-to-household counts.','Inventory plus cleaning_log.csv; questionnaire pp.7–13.')
issue('DQ-06','N1 amount data use multiple creditor-source columns. In cleaned records, 11 households answer yes to debt but all 13 amount slots are blank; 20 additional yes-to-debt households have aggregate debt zero.','All-missing amount slots summed to zero would imply debt-free status incorrectly.','Cross-tab debt status/source selection against every N1_03 amount; preserve unknowns unless verified no debt.','Questionnaire p.197; cleaned mod_n1_debt.csv and prepared d7_total_debt; preprocessing script missing.')
issue('DQ-07','Prepared debt-income ratio has substantial missingness noted in prior report and relies on a monthly income measure repeated in employment rows.','Extreme ratios can reflect period/scale mismatch, zero denominators, or genuine high liabilities.','Inspect distribution and units; do not cap; approve denominator and ratio definition.','Questionnaire pp.146–147 and 197; existing missingness/outlier reports.')
issue('DQ-08','Savings items distinguish yes/no and percentage brackets; male N2 and female N3 forms are separate.','A simple ordinal score or direct comparison across forms may misstate resilience.','Confirm saved columns and respondent reconciliation, and keep category labels rather than numeric midpoint unless approved.','Questionnaire pp.199–200; prepared map source is broad.')
issue('DQ-09','O1 agriculture/livestock/fishing/business shock questions have conditional universes based on participation questions.','Blank/inapplicable can be confused with no shock.','Preserve applicability flags and score only applicable items under an approved rule.','Questionnaire pp.201–203; O1 variables and F1/G1/G2/I modules.')
issue('DQ-10','Authoritative C:\\data clean directory has Maha 2023–24 F3 and separate Maha 2024–25 F7 modules; repository Data mirror additionally contains an underscore-named F3 long file that its cleaning log calls an identical duplicate.','Combining seasons mixes reference periods; using both duplicate exports can duplicate crop records.','Keep seasons distinct; use the stated C:\\data source and confirm lineage before using the mirror duplicate.','Both local inventories and cleaning_log.csv; questionnaire contents p.2 and F3/F7 sections.')
issue('DQ-11','Prepared label_high_vuln is bottom-quintile consumption proxy; validation report reports weighted prevalence ~0.2001.','This is a relative sample ranking, not official eligibility or independent truth; it is potentially non-independent of consumption-based features.','Use only for exploratory validation and sensitivity analysis; label it unvalidated proxy in every output.','Data/processed/hh_context.csv and preprocessing_validation_report.csv.')
issue('DQ-12','Survey source reports 6,850 interviewed households while prepared tables contain 6,847.','The three-record difference may reflect consent, incomplete interview or cleaning exclusions; silent dropping is unacceptable.','Obtain disposition/exclusion reconciliation and document the analytic household universe.','IFPRI BRIGHT project page; prepared outputs and household ID CSV row counts.')
issue('DQ-13','No R preprocessing or mechanical validation script was found in workspace or C:\\data\\processed; prior outputs exist.','Transformations cannot be reproduced or semantically audited from output tables alone.','Recover scripts and package versions before approving candidate indicators.','Recursive file inventory; only generated CSV/RDS outputs and questionnaire PDF found.')

pd.DataFrame(issues).to_csv(OUT/'issue_register.csv',index=False)
decision_rows=[
('DEC-01','Questionnaire and codebook','Provide exact instrument/codebook version','Mappings and response codes need source definitions','Questionnaire PDF/XLSForm plus codebook with versions','OPEN'),
('DEC-02','Special codes 997/998/999','Confirm meaning separately by item','Codes can represent other, unknown, refusal or valid values','Instrument labels and codebook','OPEN'),
('DEC-03','Food expenditure zeros','Confirm blank/zero means no consumption vs unobserved/not asked','Consumption and ranking can be biased by imputing missing components as zero','Questionnaire skip logic plus source-to-cleaning derivation','OPEN'),
('DEC-04','Non-food expenditure zeros','Confirm blank/zero means no expense vs not collected/merge failure','Consumption label depends on period and missingness decisions','Questionnaire recall periods and cleaning derivation','OPEN'),
('DEC-05','FIES partial scores','Approve item scoring and response-validity rules','Fractional scores suggest partial response/scoring needs review','Question wording and scoring guide','OPEN'),
('DEC-06','Roster duplicates/ages','Resolve duplicate people and missing/invalid age handling','Dependency/needs indicators depend on accurate person counts and ages','Roster keys and instrument rules','OPEN'),
('DEC-07','Employment income','Resolve repeated household income in member/job rows','Naive summation can multiply income','Income item universe, period, unit and derivation','OPEN'),
('DEC-08','Debt missingness','Define when all-missing loan amounts mean no debt','Sum-to-zero silently equates unknown with debt-free','Debt skip logic and amount item','OPEN'),
('DEC-09','Debt/income ratio','Approve denominator, period alignment and zero/unknown policy','Extreme ratios may reflect unit mismatch or genuine distress','Questionnaire units and income definition','OPEN'),
('DEC-10','Savings codes','Interpret codes and whether category is ordinal or numeric','Wrong treatment can invert resilience','Codebook and savings wording','OPEN'),
('DEC-11','Agricultural shock fields','Confirm structural applicability','Not-applicable could be misread as no shock','Module universe/skip logic','OPEN'),
('DEC-12','Maha module versions','Select and document season/module export version','Combining different seasons can mix reference periods or duplicate records','Instrument versions and export lineage','OPEN'),
('DEC-13','Bottom-quintile label','Retain as relative proxy or replace with approved outcome','Not official eligibility or independent ground truth','Research protocol and weighted design specification','OPEN'),
('DEC-14','Aggregation protocol','Approve independent hh aggregation for each long module','Prevents many-to-many joins and inflated totals','Reviewed variable map and aggregation rules','OPEN'),
('DEC-15','Household universe','Reconcile 6,847 prepared rows to 6,850 survey households','Do not silently drop or manufacture records','Sample disposition and exclusion log','OPEN')]
decisions=pd.DataFrame(decision_rows,columns=['decision_id','topic','decision_required','why_it_matters','evidence_needed','status'])
decisions.to_csv(ROOT/'decisions_for_review.csv',index=False)

def xml_cell(v, r, style):
    if v is None or (isinstance(v,float) and pd.isna(v)): v=''
    s=str(v)
    return f'<c r="{r}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(s)}</t></is></c>'
def colname(n):
    out=''
    while n:
        n,rem=divmod(n-1,26); out=chr(65+rem)+out
    return out
def sheet_xml(df):
    rows=[]
    for ri,row in enumerate([list(df.columns)]+df.fillna('').astype(str).values.tolist(),1):
        style=1 if ri==1 else 2
        ht=32 if ri==1 else 66
        rows.append(f'<row r="{ri}" ht="{ht}" customHeight="1">'+''.join(xml_cell(v,f'{colname(ci)}{ri}',style) for ci,v in enumerate(row,1))+'</row>')
    cols=''.join(f'<col min="{i}" max="{i}" width="{min(56,max(22,len(str(h))+8))}" customWidth="1"/>' for i,h in enumerate(df.columns,1))
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>'+cols+'</cols><sheetFormatPr defaultRowHeight="66"/><sheetData>'+''.join(rows)+'</sheetData><autoFilter ref="A1:'+colname(len(df.columns))+str(len(df)+1)+'"/></worksheet>'
def write_xlsx(path, sheets):
    names=list(sheets)
    wb='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i,n in enumerate(names,1))+'</sheets></workbook>'
    rel='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(names)+1))+'<Relationship Id="rId'+str(len(names)+1)+'" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
    content='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'+''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(names)+1))+'<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'
    styles='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="10"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf xfId="0" fontId="0" fillId="0" borderId="0"/><xf xfId="0" fontId="1" fillId="2" borderId="0" applyFont="1" applyFill="1"><alignment vertical="center" wrapText="1"/></xf><xf xfId="0" fontId="0" fillId="0" borderId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs></styleSheet>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',content)
        z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml',wb); z.writestr('xl/_rels/workbook.xml.rels',rel); z.writestr('xl/styles.xml',styles)
        for i,n in enumerate(names,1): z.writestr(f'xl/worksheets/sheet{i}.xml',sheet_xml(sheets[n]))

write_xlsx(OUT/'variable_mapping.xlsx',{'Candidate mapping':mapping_df,'Decisions':decisions,'Module inventory':pd.DataFrame(inventory),'Issue register':pd.DataFrame(issues)})

report=f'''# BRIGHT Component 1 — data-quality and implementation audit

Audit date: 2026-10-18  
Purpose: research decision support for human review; not an automated Aswesuma or Samurdhi eligibility system.

## Source files found

- {len(inventory)} cleaned CSV files in `{CLEAN}`.
- Prepared outputs in `{PROCESSED}`: `hh_indicators.csv` ({len(ind)} rows × {len(ind.columns)} columns), `hh_context.csv` ({len(ctx)} × {len(ctx.columns)}), `cleaning_log.csv`, `preprocessing_validation_report.csv`, `missingness_recomputed.csv`, `outlier_report.csv`, `sentinel_log.csv`, and `variable_map.csv`.
- Questionnaire: `Data/BRIGHT_questionnaire_English.pdf` (243 pages). It provides question text and item codes for the domains used below. No separate codebook was found.
- No original preprocessing or mechanical validation R script was found in the workspace or the supplied processed-data directory. Existing CSV/RDS reports were inspected, but they do not permit exact transformation replay.

## Inventory and grain

The full per-file inventory, including dimensions, exact column names, observed data types, nonmissing-key status, duplicate-key rows, and variable-level missingness, is in `module_inventory.csv` and the workbook. In this cleaned export, the household ID file and most single-row modules are household-shaped; B0–B3 are person/member records; H1/H2 are employment/person records; E and selected F modules are plot/crop-season records; J1 and J2 are food-item records; K is expenditure-item-by-period; R support files use program/support identifiers; and S2/S3 are person/measurement records. A one-row household export is not proof every item is household-level; respondent and applicability rules still require instrument crosswalks.

## Current mechanical checks

- Prepared household indicators and context each have 6,847 rows. Household keys are unique/nonmissing in both: {hh_key_unique} / {context_keys}. Key-set difference: {join_diff}.
- The indicator table contains 43 D1–D7 candidates plus `hhcode`. Previous validation says output IDs match, no infinite/NaN indicators, and weighted proxy prevalence is 0.2001.
- IFPRI describes 6,850 interviewed households (https://www.ifpri.org/project/bright-sri-lanka/); the 6,847-row analytic set must be reconciled to sample disposition before claiming full sample coverage.
- Existing `cleaning_log.csv` reports row/key checks for modules. Notable transformations include padded rows removed from B2/B3; J1/K stray rows removed; a duplicate F3 underscore export recorded as identical and skipped; and sentinel recoding in several modules. These checks do not establish semantic correctness.

## Findings requiring review

1. **Special values:** 997/998/999 do not have global meanings. The questionnaire uses 999 for “Other” on many questions and has item-specific “Don’t know,” “Refused,” and “Prefer not to say.” Review every recode against the question, not just numeric value. The sentinel log lists counts/recode status but cannot replace item documentation.
2. **Employment income:** questionnaire H1_17 asks total monthly household income while H1 is represented on person rows. There are 6,663 households with multiple H1 person records, and 5,328 have the same nonmissing H1_17 repeated. Summing these rows would multiply income. The existing outlier report flags H1_17 with maximum 27,000,000 and four records above ten times p99. Treat those as review cases; do not cap or delete them.
3. **Food/non-food expenditure:** J1 asks past-7-day item consumption/value; among 255,605 item rows coded consumed, 65,573 have missing `j1_08`; another 641,230 rows are coded not consumed and have missing value. K has 36,286 missing amounts in 472,443 item-period rows and 257,691 recorded zero amounts. Validate each period conversion and missing-to-zero decision. Missing data and “no expenditure” are not interchangeable.
4. **FIES:** the prepared score contains three fractional values (0.5, 1.5, and 2.5, one household each) and {fies_missing} missing value(s). L1/L2 contain eight experience items with separate DK/refusal responses and follow-ups. The partial-response, respondent-merging, and scoring rule remain unapproved.
5. **Roster:** B0/B1 contain 27,875 person rows each and unique `hhcode+pid`; no ages are missing in these exports, but one age is 101. B2/B3 are partial/question-specific records; their smaller row counts follow removal of padded rows in the cleaning log and do not by themselves prove person loss.
6. **Debt/savings:** N1 is a one-row household export with multiple creditor-source amount slots, not a loan-row table. Eleven debt-positive households have every amount blank and 20 debt-positive households have a zero aggregate. The prepared total records all 6,847 as nonmissing. Verify status/source selection before treating these as zero. Debt-income ratios are nonmissing for 5,281 households, with 36 values above 10 and a maximum of 50,000; no capping was applied. N2 and N3 are separate savings instruments; questionnaire No/Yes codes are 1/2, while cleaned N2_05/N3_5 values are 0/1, so the recode needs to be traced. N2_06/N3_06 are percent bands, not continuous measured savings.
7. **Structural skips:** O1 agriculture/livestock/fishing/business shocks are conditional on participation. Preserve applicability. Maha versions include 2023–24 F3 and 2024–25 F7; these are different reference seasons, not interchangeable duplicates. The workspace mirror also has a duplicate underscore-named F3 long export that is absent from the configured C:\\data cleaned directory.
8. **Long joins:** independently aggregate each long source to one row per `hhcode`, assert uniqueness, then join to the household spine with a row-count invariant. Never join raw job, crop, food, nonfood, support or person-level tables to each other before aggregation.
9. **Label:** `label_high_vuln` is a weighted bottom-quintile consumption indicator, an unvalidated relative proxy. It is not official eligibility or independent ground truth and may overlap with consumption features.

## Proposed implementation sequence

1. Recover/version the preprocessing and mechanical validation scripts, confirm raw-to-clean lineage, and document R/package versions.
2. Freeze an approved codebook-driven variable map, including each question, code, recall period, universe, direction, aggregation, and NA/zero/refusal handling.
3. Rebuild household aggregates module-by-module with key assertions and a household row-count invariant after every join; retain audit columns and excluded/missing counts.
4. Validate distributions, sentinel patterns, structural skips, expenditure period conversions, and sensitivity of the relative label. Resolve all open decisions in the register.
5. Only after review, define construct scoring/weights/uncertainty and later consider fuzzy/Bayesian methods. Keep outputs advisory and require officer review.

## Limitations

No fuzzy or Bayesian model was built. No indicator transformation is approved by this audit. Question wording is transcribed only for the candidate examples shown in the workbook; where the exact prepared-feature-to-source crosswalk could not be proven, it is explicitly marked unresolved. R is not installed in this execution environment, so the supplied R scripts/tests could not be run here; this report's generated inventory was produced with the included local Python standard-library/pandas helper and should be regenerated in the project R environment.
'''
(OUT/'data_quality_report.md').write_text(report,encoding='utf-8')
print(f'Wrote {len(inventory)} modules, {len(mapping_df)} candidate mappings, {len(issues)} flagged issues to {OUT}')
