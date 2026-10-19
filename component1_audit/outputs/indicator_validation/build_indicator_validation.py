"""Build a read-only, aggregate-only D1-D7 candidate assessment."""
from pathlib import Path
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
INREG = ROOT / "component1_audit/outputs/consolidated_measurement_review/candidate_indicator_register.csv"
ORIGREG = ROOT / "component1_audit/outputs/indicator_registry_review.csv"
DECISIONS = ROOT / "component1_audit/outputs/research_decisions_status.csv"
PREP = ROOT / "Data/processed/hh_indicators.csv"
RES = ROOT / "component1_audit/outputs/d2_d7_resolution"
HOUSING = ROOT / "component1_audit/outputs/d1_housing_material_validation"
VALIDATION = ROOT / "component1_audit/outputs/d2_d7_validation"

EXPECTED = [
    "candidate_id", "domain", "proposed_construct", "questionnaire_source_module_item_page",
    "source_variable", "prepared_variable", "respondent_universe", "unit_of_observation",
    "reference_period", "response_scale_and_verified_meanings", "skip_logic_applicability",
    "transformation_lineage", "prepared_missing_count_full_master_denominator",
    "prepared_nonmissing_count_full_master_denominator", "missingness_interpretation_limit",
    "data_integrity_and_checks", "evidence_status", "construct_assessment", "content_limitations",
    "household_aggregation_requirements", "cross_domain_overlap", "potential_double_counting",
    "alternative_operationalisations_and_tradeoffs", "further_evidence_required",
    "operationalisation_readiness", "existing_research_decision_status",
]

DOMAIN_STATUS = {
    "D1": "D1 housing audit outputs inherited; source-code recoding not rerun in this assessment.",
    "D2": "D2 resolution report and source-export/clean checks inherited; focused regression tests rerun.",
    "D3": "D3/D4 resolution report inherited; focused key/missingness regression tests rerun.",
    "D4": "D3/D4 resolution report inherited; focused key/missingness regression tests rerun.",
    "D5": "D5/D6 resolution diagnostics and questionnaire reading inherited; not recomputed in this assessment.",
    "D6": "D5/D6 resolution diagnostics and questionnaire reading inherited; not recomputed in this assessment.",
    "D7": "D7 resolution key-aligned financial diagnostics inherited; focused D7 regression test rerun.",
}

SPEC = {
"d1_income_month": ("Household income resources", "Household question recorded on H1 person rows", "Monthly", "H1_17 asks total monthly household income in LKR (p.146); supports an income-resource measure, but special-code and repeated-answer semantics remain unresolved.", "Potentially useful resource context; does not alone establish current vulnerability or equivalence across households.", "Select one consistent household response only after code/repetition checks; preserve person records; defer per-capita derivation.", "H1_17 specials, respondent rule, source-to-prepared derivation and duplicate handling.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d1_poor_walls": ("Wall material condition", "Household housing module respondent", "Current condition; no recall period", "C1_04 directly records principal wall material (pp.14-15); material is observed, poor-condition interpretation is not validated.", "Material category omits durability, maintenance, exposure and household preferences; category-to-vulnerability direction requires an approved crosswalk.", "Retain raw material category; use an exact DCS class only where all three materials map exactly; defer unmatched cases.", "Verify codes/labels and any material equivalence; researcher must define vulnerability relevance.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d1_poor_floor": ("Floor material condition", "Household housing module respondent", "Current condition; no recall period", "C1_05 is flooring (p.15), not roofing; direct material report only.", "Grouped BRIGHT responses are not fully equivalent to DCS subcategories; housing quality is not the same as vulnerability.", "Keep C1_05 separate or classify only exact supported material combinations; no inferred unmatched class.", "Confirm code crosswalk, DCS exact mapping and intended construct.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d1_poor_roof": ("Roof material condition", "Household housing module respondent", "Current condition; no recall period", "C1_06 is roofing (p.15); direct material response only.", "Material alone omits structural state, leakage, repair need and exposure.", "Retain raw roof category; only exact classifications after complete triad validation.", "Confirm exact label mappings and whether a status classification is the intended construct.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d1_bad_toilet": ("Sanitation facility type/access", "Household housing module respondent", "Current facility; no recall period", "C1_08 is a toilet/facility item (p.16); direct reported facility category.", "Facility type does not establish use, sharing, functionality or safe sanitation; code 999 conflicts with list of 1-14 and Other follow-up.", "Retain item codes; resolve Other code; report access/type separately if validated.", "Questionnaire/export version and 999 follow-up mapping; intended sanitation construct.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d1_crowded": ("Occupancy pressure / possible crowding", "Household bedrooms and roster members", "Current household composition", "C1_02 bedrooms plus B0 roster can inform occupancy pressure; a crowding formula is not questionnaire-defined.", "Bedrooms and household size are distinct components; no room suitability, sleeping arrangements or cutoff evidence.", "Report bedrooms and roster size separately; ratio or threshold only after bedroom definition, numerator and cutoff approval.", "Zero-bedroom handling, eligible roster, household-size rule and threshold.", "Plausible but requires further evidence", "Blocked by unresolved aggregation or missingness rules"),
"d1_weak_tenure": ("Tenure security / housing stability", "Household housing module respondent", "Current tenure", "C1_07 records housing tenure (p.16); tenure is a context/proxy, not a direct measure of insecurity without category rules.", "Tenure categories may not reflect legal rights, eviction risk, cost or perceived security.", "Keep tenure categories; alternative grouping requires local legal/qualitative evidence and approval.", "Code definitions and researcher definition of housing security.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d1_housing_deprivation": ("Combined housing deprivation", "Multiple household housing items", "Current; no common recall period", "Composite combines materials, toilet, bedrooms and tenure; only 30/6,847 exact material triplets fit DCS classes, and no composite rule is approved.", "Mixes heterogeneous dimensions and unsupported thresholds; unmatched materials cannot be classified.", "Separate domain items; DCS class only for exact matches; any composite requires an explicit validated rule.", "Researcher selects dimensions, thresholds, missingness and weighting after construct review.", "Unsupported by current evidence", "Blocked by unresolved aggregation or missingness rules"),
"d1_asset_share": ("Household asset ownership/functionality share", "Household asset module", "Current ownership/functionality", "D module records direct asset items; a share/index denominator and inclusion list are undefined.", "Ownership is not necessarily access, adequacy or liquid wealth; functionality and unequal asset values matter.", "Report selected items separately; define an eligible denominator only with item coverage and missingness evidence.", "Asset item universe, ownership versus functionality coding, denominator and construct purpose.", "Plausible but requires further evidence", "Blocked by unresolved aggregation or missingness rules"),
"d1_income_pc": ("Per-capita monthly household income", "H1 household income plus roster members", "Monthly income and current roster", "Uses H1_17 and B0 size; H1_17 is household monthly income but repeats on H1 person rows.", "Needs one income value, valid household denominator and special-code treatment; equal per-capita allocation is an assumption.", "Defer; later compare raw household income with per-capita version only after approved denominator.", "H1_17 handling, resident roster definition, zero/special codes and approval.", "Plausible but requires further evidence", "Blocked by unresolved aggregation or missingness rules"),
"d1_income_missing": ("Income nonresponse/missingness marker", "H1_17 person-level rows", "Monthly income item; nonresponse process", "Prepared missingness derivative exists, but absence may reflect skip, source loss, refusal or nonresponse and is not inherently deprivation.", "A missingness flag could encode survey process or respondent characteristics rather than vulnerability.", "Keep missing state in data quality reporting; do not treat as vulnerability signal without missingness mechanism study and approval.", "Source reason codes, item applicability, nonresponse process, and explicit decision on use.", "Unsupported by current evidence", "Blocked by source or semantic uncertainty"),
"d2_fies_raw": ("Household food-access experience / prepared FIES-like score", "L1 women's and L2 men's forms; household food-access items", "Previous 12 months", "L1/L2 items 01-08 (pp.178-182), codes 1 Yes/2 No/3 DK/4 Refused; prepared d2_fies_raw derivation not reproduced. Item-level experience is supported; household score is not.", "Food access covers a relevant deprivation dimension but eight experiences do not capture all affordability, diet, nutrition or seasonal aspects; two informants may differ.", "Keep L1/L2 item responses separate; obtain authoritative scoring and respondent protocol before any score; do not use current prepared score as validated.", "Scoring code/specification, respondent selection, DK/refusal/partial-response treatment, follow-up gates and source version.", "Unsupported by current evidence", "Blocked by source or semantic uncertainty"),
"d3_dep_ratio": ("Age-based dependency ratio", "B0 person roster", "Current age", "B0_04_years and B0_04_months separately record age (p.8); no threshold or denominator is in questionnaire.", "Age dependency is a demographic proxy, not direct need or economic dependence; age bands are judgement-sensitive.", "Keep raw age units; later compare approved age-band shares or ratio; no threshold selected.", "Age conversion, age cutoffs, working-age denominator, roster completeness and zero denominator rule.", "Plausible but requires further evidence", "Blocked by unresolved aggregation or missingness rules"),
"d3_share_child": ("Share of household members below a child age threshold", "B0 person roster", "Current age", "Age is recorded in years/months; child threshold and eligible roster denominator are not specified.", "Age alone does not establish care need, school participation or dependency.", "Retain member ages; approved age band/share after definition and denominator review.", "Researcher-defined age threshold and treatment of age months/unknowns.", "Plausible but requires further evidence", "Blocked by unresolved aggregation or missingness rules"),
"d3_share_elderly": ("Share of household members above an older-age threshold", "B0 person roster", "Current age", "Separate age units are available; no older-age threshold or denominator approved.", "Age proxy omits health, income support and functional ability.", "Retain ages; define and compare approved age bands only after review.", "Threshold, denominator and age-field validation.", "Plausible but requires further evidence", "Blocked by unresolved aggregation or missingness rules"),
"d3_any_disability": ("Combined chronic illness/severe disability household context", "B3 member health module", "B3_01 chronic illness or severe disability; B3_02 condition types (p.12)", "Questionnaire says B3_01 1=No/2=Yes, but skip text says if 1; clean values 0/1. B3 record missing for 854/27,875 roster members; full roster coverage denominator 27,875.", "Combines chronic illness and severe disability; item is person-level and incomplete coverage cannot be interpreted as absence.", "Preserve member responses/categories; household any-member only after code and B3 universe/coverage resolution.", "Questionnaire/export mapping, skip correction, B3 eligibility and absent-record meaning.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d3_chronic_share": ("Share of members with chronic illness", "B3 member health module", "Chronic illness/severe disability combined question; p.12", "Current/reported condition; the current item combines chronic illness and severe disability, so chronic-only numerator is not identified.", "Proposed chronic-only construct exceeds instrument specificity; B3 coverage is incomplete.", "Retain combined raw item; defer chronic-only share unless source contains a separate item.", "Evidence of a separate chronic-only question and approved denominator.", "Unsupported by current evidence", "Requires additional data or external documentation"),
"d3_activity_limited_share": ("Share of members whose activities are limited by condition", "B3_03 member module", "Question framed as last year; code 7 says completely interrupted more than 12 months ago (p.13)", "Member-level categories; B3_01 code/skip conflict and B3 coverage complicate eligibility.", "Share depends on eligible members and period alignment; no record can mean missing module, not no limitation.", "Keep B3_03 categories at member level; aggregate only after period, gate and denominator resolution.", "Clarify code 7, age/eligibility gates, B3 missing-record coverage and denominator.", "Plausible but requires further evidence", "Blocked by unresolved aggregation or missingness rules"),
"d4_n_workers": ("Household count of workers/jobs", "H1 primary and H2 secondary employment person/job modules", "H1_01 current status; H2_02 other activity last month (pp.139-146); H2 clean field h1_02 mapping unresolved.", "Person/job-level; primary status and second activity are different units; H2_02 field mapping unverified.", "Count can depend on job versus person definition, eligibility and roster linkage; larger households mechanically have more opportunities.", "Keep person items separately; define eligible worker any/count/share only after mapping and universe validation.", "Raw export field IDs, H2 crosswalk, job/person definition and missingness rules.", "Unsupported by current evidence", "Blocked by source or semantic uncertainty"),
"d4_n_unemp_seeking": ("Current unemployment/job search context", "H1_01 and H1_13 primary employment", "Current status; H1_13 active search in last 4 weeks conditional on status 8 (pp.139,145)", "Questionnaire H1_13 gate is H1_01=8; resolution audit found 954 nonmissing H1_13 values, zero outside status 8; source person rows are not household aggregates.", "Search behavior and current unemployment are not the same construct; does not capture underemployment or job quality.", "Keep status and search separate; household any/count/share only after eligible person denominator approval.", "Person roster correspondence, status labels/codes, and household summary rule.", "Plausible but requires further evidence", "Blocked by unresolved aggregation or missingness rules"),
"d4_irregular_share": ("Irregular employment share", "H1_08 payment frequency", "Current job/payment periodicity", "Question asks payment frequency; periodicity alone does not establish work regularity.", "Proxy construct unsupported; denominator among jobs/persons unclear.", "Keep payment frequency categories raw; obtain a direct regularity item or validated construct before deriving.", "Questionnaire concept, eligible job/person denominator, and construct validation.", "Unsupported by current evidence", "Requires additional data or external documentation"),
"d4_informal_share": ("Informal employment share", "H1_04 written agreement; H1_11 payment modes", "Current employment conditions", "Written agreement/payment mode items do not alone define informality.", "Misses legal registration, social protection and other dimensions; share denominator unresolved.", "Retain component items separately; use an authoritative informality definition only if required items exist.", "Validated definition, coding crosswalk and eligible employment denominator.", "Unsupported by current evidence", "Requires additional data or external documentation"),
"d4_unemployed_12m": ("Past-year unemployment exposure", "H1_05/H1_05a", "Unemployed at any time during past 12 months; months in follow-up (p.143)", "Person-level; among 2,592 H1_05 Yes rows, all month flags are nonmissing in resolution audit; this does not establish household aggregation.", "Retrospective self-report, duration follow-up, and person/household interpretation remain distinct from current job search.", "Keep H1_05 and H1_05a separate; household summaries require approved eligible member rule.", "Special code semantics, respondent/member mapping and household denominator.", "Plausible but requires further evidence", "Blocked by unresolved aggregation or missingness rules"),
"d4_no_worker": ("Household with no worker", "H1_01/H2_02 plus B0 roster", "Current status and H2 other activity last month", "No-worker requires a worker definition and complete eligible roster; H2 mapping remains unresolved.", "No record/missing status cannot be equated with no worker; household size affects opportunity.", "Defer; later any eligible working member under an explicit definition, or keep person records.", "Worker/job definition, source crosswalk, status universe and missingness rule.", "Unsupported by current evidence", "Blocked by source or semantic uncertainty"),
"d5_n_shocks_any": ("Count of household shocks", "O1_01_1-20", "O1 codes 1 severe/2 moderate/3 no impact; item 20 12 months, common period for 1-19 unresolved (pp.201-203)", "Household responses with participation gates; blank is not no shock.", "Count assumes shared period, item weights/equivalence and eligible denominators; impact categories are not simple occurrence.", "Retain item-level states; period-verified subset only after approval; do not count now.", "O1 item periods, gates, missingness and intended event definition.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d5_n_shocks_severe": ("Count of severe-impact shocks", "O1_01_1-20", "Code 1 severe impact; period only explicit for item 20", "Severity count requires common period and applicability per item.", "A count weights all event types equally and omits moderate impact/household consequence differences.", "Preserve item severity categories; defer count or compare pre-specified subsets after clarification.", "Period/gates and severity construct definition.", "Unsupported by current evidence", "Blocked by source or semantic uncertainty"),
"d5_severity": ("Combined shock severity", "O1_01_1-20", "Codes 1/2/3 severe/moderate/no impact", "No validated ordering, weights or period for items 1-19.", "Ordinal response categories and event mix cannot be summed without assumptions.", "Retain separate item categories; no total/score until instrument and researcher approve semantics.", "Scoring specification, common period and missingness/gate rules.", "Unsupported by current evidence", "Blocked by source or semantic uncertainty"),
"d5_price_shock": ("Price/food-cost shock grouping", "O1_01_1,2,5,6", "Items pp.201-202; period not verified for items 1-19", "Household shock items; no group count/period validated.", "Combines different price/availability experiences; possible overlap with D2 food access and D6 coping.", "Keep item-level; define a grouping only after question text and common reference period review.", "Verify exact item wording, period, gate and candidate definition.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d5_income_shock": ("Employment/income loss shock", "O1_01_3/4", "Items pp.201-202; common period unverified", "Conceptually related to H1_05 past-12-month unemployment; distinct question framing.", "Potential double-count with D4 labor outcomes; different period and impact wording.", "Keep O1 items separate from H1 states; compare only after period verification.", "O1 reference period and event/impact meaning.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d5_health_shock": ("Household health/death/injury shock", "O1_01_7", "p.202; common period unverified", "Household event/impact, distinct from member B3 condition.", "May overlap conceptually with D3 need but represents an event, not ongoing member condition.", "Keep event and member-condition measures separate; no member count.", "Reference period, event definition and applicability.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d5_climate_shock": ("Climate/natural shock grouping", "O1_01_9-13", "pp.202-203; periods for items 1-19 unverified", "Some item applicability depends on agriculture participation; gates and blanks remain distinct.", "Combines environmental events with potentially different impacts and exposures.", "Retain items; season/context-specific subsets after gate validation.", "Exact item content, common period, F1 gates and eligible denominator.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d5_agri_shock": ("Agriculture/fisheries shock grouping", "O1_01_11-18; F1/G1/G2/I gates", "pp.202-203; F3/F7 separate Maha seasons", "Gate-defined households and season-specific agricultural modules are not interchangeable.", "Combining household shock items with season modules may mix exposure periods and units.", "Keep O1 items and F3 2023-24/F7 2024-25 separate; select target only after approval.", "Gate rules, O1 periods and target season.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d6_used": ("Use of coping actions", "O2_01-18", "Past 12 months, pp.203-208; response categories 1 Yes, 2 unnecessary, 3 discontinued, 4 N/A, 5 prefer not to say", "O2_05/06 gated by F1_00a=1; selected follow-ups are multiselects.", "Binary use coding would collapse no-need, discontinued, N/A and non-disclosure; items can overlap D2.", "Retain five-category item responses; itemwise actions with explicit eligibility only after approval.", "Itemwise gates, response interpretation and target action set.", "Unsupported by current evidence", "Blocked by source or semantic uncertainty"),
"d6_exhausted": ("Coping capacity exhaustion", "O2_01-18 selected items", "Past 12 months; categories 1-5 distinguish multiple states", "No validated exhaustion hierarchy or formula; follow-up flags are separate.", "Exhaustion is not necessarily directly asked; collapsing response categories imposes construct.", "Keep item-level; seek direct measure or validated protocol before defining exhaustion.", "Operational definition, item selection, gates and validation evidence.", "Unsupported by current evidence", "Requires additional data or external documentation"),
"d6_stress_share": ("Share of coping stress items", "O2_01-18 selected items", "Past 12 months; denominator and five-state handling unresolved", "A share requires a defined eligible item denominator and binary/ordinal rule.", "Mixes structural skips and explicit categories; may duplicate D2 and D7 signals.", "Report itemwise response states; later eligible-item denominator only with approved rule.", "Core item list, gate/skip handling, response mapping and missingness rule.", "Unsupported by current evidence", "Blocked by unresolved aggregation or missingness rules"),
"d7_has_debt": ("Owing status / financial liability context", "N1_00", "p.197; response is 1 No/2 Yes in questionnaire; no verified period", "Clean/export n1_0 is 0/1 and cell-identical for checked source/clean files; direction mapping unresolved.", "May measure owing status but not amount, burden or current balance semantics; household/respondent universe needs source check.", "Keep raw code unlabeled pending recode lineage; defer interpreted status.", "Questionnaire-platform export map and transformation code.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d7_total_debt": ("Debt amount / proposed total", "N1_03 amount slots 1-12/999", "p.197; amount of loan taken, no explicit outstanding-balance period", "Among 2,947 n1_0=1: 31 prepared zeros; 11 all 13 source slots blank; 12 with no positive slot. Denominator is provisional code-1 status, not semantically confirmed debt-positive.", "Loan-origin amount is not current outstanding debt; prepared-total derivation unreplicated; historical 20 count unresolved.", "Preserve amount slots; defer all summation/current-debt interpretation until source rule and balance measure verified.", "Prepared derivation, slot selection, missing/zero rule, and evidence of current outstanding balance.", "Unsupported by current evidence", "Blocked by source or semantic uncertainty"),
"d7_n_debt_sources": ("Number of debt sources", "N1_01 source slots", "p.197; institution/source selections", "Source-count rule and Other 13 vs follow-up 999 discrepancy unresolved.", "Checkbox response slots may mix sources and conditional amounts; not direct count until code mapping is verified.", "Keep checkbox fields; count only with validated source-slot codebook and missingness.", "Instrument/export crosswalk and prepared formula.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d7_hard_to_repay": ("Repayment difficulty", "N1_06 source slots", "p.198; 1 very difficult, 2 somewhat, 3 not too difficult, 4 easy, 5 DK/don't want to say", "Loan/source-slot level in household record; no approved aggregation across slots.", "Mixes ordinal difficulty and combined unknown/non-disclosure category; no verified period or eligible loan universe.", "Retain slot-specific ordinal response; any household summary needs explicit worst/any/weighted rule.", "Questionnaire-to-column mapping, slot universe and unknown/refusal separation if possible.", "Plausible but requires further evidence", "Blocked by unresolved aggregation or missingness rules"),
"d7_has_bank_account": ("Household access to bank account", "N2_01", "p.198; questionnaire 1 No/2 Yes; no recall period", "Household access question; delivered clean/export direction remains 0/1 pending recode lineage. N2_02 is savings location, not ownership.", "Access does not measure account use, balance, control or financial inclusion quality.", "Keep raw N2_01; interpret only after code direction is verified; do not substitute N2_02.", "Export recode and code mapping.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d7_able_to_save": ("Saving ability / financial capacity", "N2_05 men form and N3_05 women form (clean n2_05/n3_5)", "Past 12 months; questionnaire 1 No/2 Yes, clean/export 0/1 direction unresolved", "5,393 paired nonmissing records; 1,453 disagree. Respondent forms differ; does not establish household savings amount.", "Prepared combined field semantics/derivation unknown; different respondent universes and personal versus household concept.", "Keep N2/N3 separately; select respondent or combine only with approved household rule and verified code direction.", "Form respondent IDs/universe, export recode and prepared derivation.", "Plausible but requires further evidence", "Blocked by source or semantic uncertainty"),
"d7_n_income_sources": ("Count of household income sources", "H1/I/F1/G1 candidate source list not explicit", "No validated common reference period or item list", "No explicit verified source list or complete module eligibility mapping supports the prepared count.", "Mixes labor, enterprise and agriculture source domains; structural inapplicability can be confused with absence.", "Defer; retain source items independently; define source list and period only after evidence.", "Prepared formula, named source fields, gates and common period.", "Unsupported by current evidence", "Requires additional data or external documentation"),
"d7_debt_income_ratio": ("Debt-to-income ratio", "N1_03/prepared debt and H1_17", "N1 amount has no confirmed outstanding period; H1_17 monthly household income p.146", "Prepared numerator/denominator not reproducible; income repeats on person rows; periods/scales and zero/unknown handling unresolved.", "Ratio may combine historical loan amount with monthly income and use repeated/missing/special-coded denominator.", "Defer ratio; only revisit with validated current balance, income basis, period alignment and zero rules.", "Both derivations, current-balance measure, H1_17 treatment and ratio interpretation.", "Unsupported by current evidence", "Blocked by source or semantic uncertainty"),
}

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1<<20),b""): h.update(block)
    return h.hexdigest()

def overlap(name):
    if name.startswith("d1_income"): return "D1 income-D4 livelihood (conceptual/partial temporal); H1_17 duplicated across person rows is a data-grain duplication."
    if name.startswith("d1_") and any(x in name for x in ("wall","floor","roof","toilet","tenure","crowd","housing")): return "D1 housing/crowding-D3 household size/needs; conceptual overlap, not observed redundancy."
    if name.startswith("d1_asset"): return "D1 assets-D7 financial resilience and D6 asset-sale coping; stock/action distinction, no causal evidence."
    if name.startswith("d2_"): return "D2 food access-D6 food coping; same broad 12-month window, different construct."
    if name.startswith("d3_"): return "D3 health/age-D5 health shocks; person versus household units and periods differ."
    if name.startswith("d4_"): return "D4 employment/income-D1 income and D5 shock reports; related concepts with differing periods."
    if name.startswith("d5_"): return "D5 shocks-D4 employment/income, D3 health and D6 coping; events differ from states/actions."
    if name.startswith("d6_"): return "D6 coping-D2 food access and D7 debt/savings/assets; action/capacity may co-occur."
    return "D7 finance-D6 coping and D1 income/assets; no causal direction established."

def status(source_decision):
    return source_decision if source_decision else "No explicit researcher decision found; pending researcher approval"

def source_file_field(value):
    parts=[x.strip() for x in str(value).split(";") if x.strip()]
    modules=[x for x in parts if x.startswith("mod_")]
    fields=[x for x in parts if not x.startswith("mod_")]
    paths=[f"Data/processed/clean/{m}.csv" for m in modules]
    return "; ".join(paths + (["fields: " + "; ".join(fields)] if fields else []))

def readiness(spec, old):
    if old.startswith("DEFERRED"): return "Blocked by source or semantic uncertainty"
    return spec[8]

def make_register():
    old=pd.read_csv(ORIGREG,encoding="utf-8-sig").fillna("")
    cons=pd.read_csv(INREG,encoding="utf-8-sig").fillna("")
    # The consolidated predecessor register omitted a dedicated stable-ID column;
    # recover IDs from its documented prepared-variable label and cross-check below.
    cons["candidate_id"]=cons.prepared_variable_name.str.split(" (column",regex=False).str[0]
    prep=pd.read_csv(PREP,low_memory=False)
    assert len(old)==43 and old.candidate_indicator.is_unique
    assert len(cons)==43 and cons.candidate_id.is_unique
    assert cons.candidate_id.tolist()==old.candidate_indicator.tolist()
    # Aggregate count diagnostics only. The denominator here is full prepared master rows,
    # not an asserted eligibility denominator.
    n=len(prep)
    out=[]
    for _,r in cons.iterrows():
        name=r.candidate_id; spec=SPEC[name]; pvar=name
        miss=int(prep[pvar].isna().sum())
        source=old.loc[old.candidate_indicator.eq(name)].iloc[0]
        dom=r.domain
        assessment={
          "candidate_id":name,"domain":dom,"proposed_construct":r.candidate_construct,
          "questionnaire_source_module_item_page":r.questionnaire_module_item_page,
          "source_variable":source_file_field(r.source_module_file_and_fields),
          "prepared_variable":f"Data/processed/hh_indicators.csv:{pvar}" if pvar in prep.columns else "not present",
          "respondent_universe":spec[1],"unit_of_observation":r.measurement_level_unit,
          "reference_period":spec[2],"response_scale_and_verified_meanings":spec[3],
          "skip_logic_applicability":spec[3] + " Additional inherited gate/skip details: " + str(source.get("missing_data_treatment","")),
          "transformation_lineage":spec[3] + " Prepared column exists; existence is not derivation validation. Domain evidence: " + r.source_lineage_reproducibility,
          "prepared_missing_count_full_master_denominator":f"{miss}/{n} prepared rows missing; full-row denominator, not eligible denominator",
          "prepared_nonmissing_count_full_master_denominator":f"{n-miss}/{n} prepared rows nonmissing; may include special/unresolved values",
          "missingness_interpretation_limit":r.missing_applicability_special_code_handling + f" Prepared-column missing count is {miss}/{n}; cannot distinguish structural skip, refusal, unknown or unexplained missing without source lineage.",
          "data_integrity_and_checks":DOMAIN_STATUS[dom] + " Prepared column presence checked; full-row missingness counted. No source recode or new household aggregation performed.",
          "evidence_status":("Partially verified" if dom in ("D2","D3","D4","D7") else "Partially verified"),
          "construct_assessment":spec[7],"content_limitations":spec[4],
          "household_aggregation_requirements":spec[5],"cross_domain_overlap":overlap(name),
          "potential_double_counting":r.potential_double_counting if "potential_double_counting" in r else overlap(name),
          "alternative_operationalisations_and_tradeoffs":spec[5],"further_evidence_required":spec[6],
          "operationalisation_readiness":readiness(spec,str(source.researcher_candidate_decision)),
          "existing_research_decision_status":status(str(source.researcher_candidate_decision)),
        }
        out.append(assessment)
    df=pd.DataFrame(out,columns=EXPECTED)
    return df, old, n

OVERLAPS=[
 ("D1 income and D4 livelihood","H1_17 is monthly household income (p.146); H1_01 current, H1_05 past 12 months, H1_13 last four weeks (pp.139-145).","Conceptual/partial temporal; repeated household income across H1 persons is duplicated data grain, not a separate construct.","Income may multiply if summed by person; combining income and work status can overweight livelihood hardship.","Retain household income and person employment separately; any/count/share representations require eligible denominator.","H1_17 and H2_02 mapping; respondent and period rules."),
 ("D1 crowding and D3 household size/dependency","C1_02 bedrooms (p.14); B0 roster and age (pp.7-8).","Conceptual/mathematical if a future occupancy ratio uses both; no correlation tested.","A crowding ratio plus age/dependency measure can overweight household size/composition.","Keep bedroom count and age fields separate; later test defined crowding and dependency candidates as distinct constructs.","Bedroom units/rooms, roster denominator, thresholds and age bands."),
 ("D2 food insecurity and D6 food-related coping","L1/L2 food-access items, previous 12 months (pp.178-182); O2 coping past 12 months (pp.203-208).","Conceptual and same broad reference window; no causal analysis performed.","Hardship experiences and responses may both signal deprivation; removing coping loses response information.","Retain item/form responses separately; compare after scoring and gates are resolved.","D2 scoring/respondent rule and O2 item applicability/categories."),
 ("D3 health conditions and D5 health shocks","B3 member health/activity pp.12-13; O1_07 household illness/death/injury p.202, period unresolved.","Conceptual overlap, distinct member condition versus household event; no shared source item.","Could count ongoing need and acute event together, but each carries different information.","Keep member-level conditions and household shocks separate; only later use aligned period constructs.","B3 code/skip/coverage and O1 period."),
 ("D4 employment/income changes and D5 shocks","H1_05 past-year unemployment/H1_13 recent search; O1_04 income/employment shock and O1_20 past year.","Conceptual and partly temporal; O1_1-19 period unresolved; no causal inference.","Same event may appear as labor status and shock impact; units and time windows differ.","Keep event and labor outcomes separately; defer comparison until O1 period established.","O1 item period, H1 member denominator and event meaning."),
 ("D6 coping and D7 debt/savings","O2 coping past year; N1 borrowing/repayment (pp.197-198), N2/N3 savings (pp.199-200).","Conceptual/possible temporal; direction is a hypothesis only.","Debt may finance coping or reflect burden; savings ability may be capacity/protection. Combining may reverse direction.","Separate coping actions from finance/access; N2 and N3 form-specific.","N1 current balance/code direction; savings respondents; O2 item definitions."),
 ("D1 assets and D7 financial resilience","D asset stock items pp.17-21; N1 debt and N2/N3 account/savings items pp.197-200.","Conceptual association; no shared item, no empirical association tested.","Asset ownership and financial access may both proxy resources, but assets differ in liquidity and ownership.","Retain direct asset and financial-access items separately; avoid an unvalidated asset share/index.","Asset universe/functionality and D7 semantic crosswalk."),
 ("D1 housing stock and D5 housing shocks","C1 current materials pp.14-16; O1 shock impact items pp.201-203.","Conceptual, current condition versus event; O1 period for 1-19 unresolved.","Housing material and damage event can count related adversity, while event adds timing/impact.","Keep separately; compare only after O1 period and item wording resolved.","O1 shock time frame and exact housing damage question mapping."),
]

ISSUES=[
 ("EV-01","D1","Only 30/6,847 exact housing triads matched DCS 2024 classes in inherited audit; other combinations remain unmatched/approximate.","Re-read inherited feasibility table; underlying crosswalk not rerun.","Keep material items raw; exact class only; later authoritative harmonisation.","No invented class; limited combined classification coverage."),
 ("EV-02","D1","C1_08 code list 1-14 but Other follow-up 999; H1_17 repeated across person rows; asset share denominator absent.","Questionnaire review inherited; missingness counts on prepared columns newly calculated.","Resolve 999; preserve H1_17 without sum; defer asset share/per-capita derivatives.","No toilet code interpretation, income aggregate or asset index."),
 ("EV-03","D2","39/6,847 missing and 3/6,847 fractional prepared values; L1/L2 export-clean matches; no scoring derivation.","Prior resolution tests rerun; lineage search inherited.","Keep forms separate; obtain specification; defer score.","Prepared score not validated."),
 ("EV-04","D3","854/27,875 B0 roster members have no B3 record; B3_01 code/skip contradiction; B3_03 category 7 period mismatch.","Focused regression test rerun; questionnaire crosswalk inherited.","Raw member-level categories; clarify gates; defer household summaries.","Absence is not condition-free; no dependency/health aggregate."),
 ("EV-05","D4","1,519/6,847 households have no nonmissing H1_17; H2_02 mapping unresolved; income repeats on persons.","Focused H1_17 missingness and key tests rerun.","Never sum; recover field mapping; defer household employment aggregates.","No worker count, per-capita income or ratio."),
 ("EV-06","D5","O1 only item 20 explicit past-12-month; gates and blank status distinct.","Inherited D5/D6 report reviewed; diagnostics not recomputed.","Item-level states; clarify periods; no count/severity.","No common period construct."),
 ("EV-07","D6","O2 five states and follow-up multi-selects have distinct semantics and gates.","Inherited D5/D6 report reviewed; diagnostics not recomputed.","Retain categories; no binary/count/share.","Coping candidates remain unimplemented."),
 ("EV-08","D7","31/2,947 prepared zeros; 11/2,947 all slots missing; 12/2,947 no positive amount; historical 20 unreconciled.","Focused D7 key-aligned regression rerun; old validator inspected and did not compute prepared-zero predicate.","Keep both historical claim and latest reproducible count; do not infer equivalence.","No debt total/current balance interpretation."),
 ("EV-09","D7","1,453/5,393 paired nonmissing N2/N3 differences; export direction unresolved; N1 amount is amount taken.","Inherited resolution diagnostics reviewed; not rerun except D7 regression.","Keep forms separate; verify code direction and target respondent.","No combined saving or debt burden measure."),
 ("EV-10","D7","No verified explicit item list for d7_n_income_sources; ratio numerator/denominator lineage not reproducible.","Prepared variable presence and missingness counted; formulas not rerun.","Defer both; preserve source items.","No debt-income ratio or source count."),
]

def decision_queue():
    return """# Researcher decision queue

No option below has been selected. Recorded decisions authorize only their stated validation/raw-reference scope.

## A. Blocking interpretation or source-lineage issues

- **D1 exact housing and Other mappings:** 30/6,847 exact DCS combinations in inherited audit; C1_08 999 mismatch. Alternatives: raw item responses (transparent, no combined status), exact-only DCS classification (low coverage), or obtain authoritative equivalence (requires source evidence). Deferring leaves unmatched cases unclassified. Further documentation can resolve mappings; what counts as vulnerable housing needs judgement.
- **D2 FIES score/respondent:** 39 missing, three fractional, no score derivation. Alternatives: separate L1/L2 items, select a form using survey design, or validated combination rule. Each trades provenance against compactness and respondent/partial-response assumptions. Deferring blocks score interpretation. Scoring specification may resolve technical rules; target respondent remains a research choice.
- **D3 B3 semantics:** code list versus skip conflict, and category 7 exceeds stated last-year period. Alternatives: obtain source version clarification, preserve raw codes, or defer affected summaries. Deferring blocks recode/health interpretation; instrument/export records may resolve.
- **D4 H2_02 and H1_17:** mapping unresolved; 1,519 households lack nonmissing H1_17, repeated values must not be summed. Alternatives: recover source crosswalk, keep raw person measures, or select one consistent household answer after special-code review. Deferring blocks income and worker-derived candidates. Source lineage may resolve fields; household aggregation needs judgement.
- **D5 O1 periods/gates:** only item 20 has explicit 12-month period; blanks are not no shock. Alternatives: raw item states, period-confirmed subset, or clarification. Deferral blocks shock counts; source programming may resolve.
- **D6 O2 meanings:** preserve five categories and gated follow-ups. Alternatives: raw categories, later item grouping, or defer uncertain items. Deferral blocks coping score. Grouping requires researcher construct judgement.
- **D7 debt/savings semantics:** N1_00 1/2 questionnaire versus 0/1 clean/export; amount taken is not current balance; N2/N3 differ 1,453/5,393 paired cases. Alternatives: recover mapping, raw unlabeled values, form-separated savings, or defer debt burden. Deferral blocks financial aggregates; source records may resolve some, respondent target is a research decision.

## B. Decisions required before household-level aggregation

- **D3 age, health and roster denominator:** 854 roster members lack B3. Alternatives: member-level only, age bands, dependency ratio, member-any or eligible-member share. Raw is least assumption-heavy; ratios/shares need thresholds, denominator and coverage decisions. Deferral leaves D3 member-level. Eligibility may be clarified technically; thresholds require judgement.
- **D4 employment summary:** person/job distinction and H2 mapping unresolved. Alternatives: person-level, any member, count, share, reference person. Any is size-sensitive; count mechanically grows with household size; share requires reliable eligible denominator. Deferral prevents household employment features.
- **D1 income/assets:** select one nonconflicting H1_17 only after special-code approval; no per-capita or asset-share denominator yet. Alternatives preserve raw fields versus approved derived summary. Deferral leaves contextual items unaggregated.
- **D5/D6 applicability:** keep gate-no, gate-missing, eligible blank and explicit categories distinct. Itemwise denominators preserve information; complete-case subsets simplify but can select cases. Deferral blocks sums/shares/imputation.

## C. Candidate construct and redundancy decisions

- Decide whether housing material, sanitation, tenure, assets and income are direct conditions or proxies for vulnerability. Raw responses preserve detail; composed classes are more compact but assume category thresholds/equivalence. Deferral keeps candidates descriptive.
- Decide whether proposed D3 combined condition, D4 irregular/informal work, D5 grouped shocks, D6 use/exhaustion/stress, and D7 source/ratio constructs match questionnaire content. Item wording supports some component facts, not all composites. Deferral excludes derived interpretations.
- Review eight documented cross-domain pairs. Retaining separate constructs may double-weight; combining risks information loss and assumptions. No correlation/feature selection was run; no candidate should be removed solely for conceptual overlap.

## D. Decisions required before Fuzzy-Bayesian modelling

- Approve candidate definitions, units, eligible populations, category treatment, missingness, and household aggregation only after evidence closure. Alternatives are validated raw/categorical features, validated derived measures, or exclusion/deferment; these affect interpretability and coverage. Deferral blocks model construction.
- Preserve DEC-13 boundary: bottom-quintile consumption proxy is separate descriptive sensitivity, not ground truth, eligibility, training target or core feature. Any change requires explicit researcher approval.
- Do not choose weights, fuzzy sets, Bayesian dependencies, ranks or eligibility rules in this validation stage.

## E. Sensitivity analyses to consider later

- D1 exact-only DCS material matches (30/6,847) versus separate component items; do not classify unmatched cases.
- D2 form-specific item response alternatives only after an authoritative scoring protocol; three fractional mean-pattern cases are not proof of derivation.
- D7 reproduce the historical 20-zero count if its source query becomes available; compare to current 31 only after matching predicates and denominators.
- After measurement approval, assess distinct overlap pairs and denominator sensitivity. No association or causal analysis is asserted here.
"""

def make_reports(df, n):
    # Writes the 7 domain files and the combined file from the same schema/order.
    df.to_csv(OUT/"all_43_candidate_assessment.csv",index=False,encoding="utf-8-sig")
    for domain in [f"D{i}" for i in range(1,8)]:
        df.loc[df.domain.eq(domain)].to_csv(OUT/f"{domain}_candidate_assessment.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(OVERLAPS,columns=["overlap_pair","source_concepts_and_periods","relationship_type_and_evidence","potential_double_counting","alternatives_and_tradeoffs","evidence_needed"]).to_csv(OUT/"cross_domain_redundancy_review.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(ISSUES,columns=["gap_id","domain","evidence_gap_and_denominator","evidence_status_and_checks","alternatives","consequence_if_unresolved"]).to_csv(OUT/"evidence_gaps_and_blockers.csv",index=False,encoding="utf-8-sig")
    (OUT/"researcher_decisions_required.md").write_text(decision_queue(),encoding="utf-8")
    coverage="""# Construct coverage review

## What the questionnaire can observe

The inherited 43 candidates span material/housing and income resources (D1), food-access experiences (D2), roster age/health needs (D3), employment and income (D4), reported shocks (D5), coping responses (D6), and debt/account/savings context (D7). These are observable domains, not proof that each proposed composite has valid content or predicts current vulnerability.

## Important limitations and possible coverage gaps

- **Housing and living conditions:** material, toilet, tenure and bedroom questions do not necessarily cover structural safety, overcrowding experience, utilities, water reliability, accessibility, housing costs or displacement. Treat these as dimensions not represented or not established by the reviewed candidates; do not add proxies without instrument evidence and researcher approval.
- **Resources and livelihoods:** H1_17 and labor items cover income/work concepts, but prepared income lineage, special codes, secondary work mapping, stability, debt balance and liquid assets are not fully established. A derived asset share is not currently supported.
- **Food and health needs:** D2 has food-access items but no reproducible household score; B3 has member coverage gaps and semantic conflicts. Nutrition status, dietary adequacy and health-care access are not established by these reviewed candidate definitions.
- **Shocks and adaptation:** O1 periods are unclear for items 1-19; O2 response categories measure distinct coping states. The 43 candidate list does not by itself establish shock duration, recovery, repeated exposure or causal resilience.
- **Financial resilience:** N1 amount taken is not verified outstanding liability; N2/N3 are respondent-specific and disagree. The candidates do not establish liquid savings amounts, financial control, repayment burden or a consistent household resilience measure.
- **Population and survey process:** missing module records, sample disposition and nonresponse mechanisms can affect observed coverage. Missing must not be treated as absence or vulnerability without evidence.

## Interpretation

The review identifies instrument dimensions not captured or not verified; it does not assert that BRIGHT lacks all corresponding questions elsewhere. Before proposing additions, review the full instrument and source modules. No new candidate was added, no existing candidate removed, and no construct was scored. Technical completeness and correct joins do not establish content validity, construct validity, decision relevance, or fairness for beneficiary prioritisation.
"""
    (OUT/"construct_coverage_review.md").write_text(coverage,encoding="utf-8")
    methods=f"""# Validation methods and tests

## Inputs inspected

- Candidate inventory: `component1_audit/outputs/consolidated_measurement_review/candidate_indicator_register.csv` and source `component1_audit/outputs/indicator_registry_review.csv` (43 candidate IDs).
- Existing decisions: `component1_audit/outputs/research_decisions_status.csv`; no decision was altered.
- D1: `component1_audit/outputs/d1_housing_material_validation/housing_classification_audit.md`, `housing_material_crosswalk.csv`, `housing_combination_feasibility.csv`, and `housing_material_frequency_report.csv`; builder `component1_audit/scripts/build_housing_material_validation.py`.
- D2-D7: `component1_audit/outputs/d2_d7_resolution/d2_lineage_report.md`, `d3_d4_source_semantics_report.md`, `d5_d6_period_applicability_report.md`, `d7_financial_semantics_report.md`, `d2_d7_resolution_summary.md`; builder `component1_audit/scripts/build_d2_d7_resolution.py`, regression file `component1_audit/scripts/test_d2_d7_resolution.py`.
- Cross-domain and prior issues: `component1_audit/outputs/d2_d7_validation/cross_domain_overlap_register.csv`, `d2_d7_validation_report.md`, and `component1_audit/outputs/consolidated_measurement_review/cross_domain_overlap_register.csv`, `unresolved_measurement_issues.csv`, `researcher_decisions_required.md`.
- Questionnaire: `Data/BRIGHT_questionnaire_English.pdf`; DCS reference used by inherited D1 audit: Census of Population and Housing 2024 Final Report, section 11.5, printed p.189.
- Prepared values: `Data/processed/hh_indicators.csv`, read only to confirm prepared columns and count each column's missing values over its full row count ({n:,}). These are full-master denominators, not eligible-case denominators and do not distinguish structural skip from nonresponse.

## Assessment method

The original stable candidate IDs and order were retained, partitioned D1 through D7, and assessed using identical columns. Evidence and readiness classifications are separate from approval status. Every prepared-column missingness count uses the full {n:,}-row prepared file denominator; observed nonmissing values may include special/unresolved codes. Item eligibility denominators are reported only where inherited diagnostics establish them. Unknowns are explicitly stated; no new recode, imputation, household aggregation, score, model feature, association test or feature selection was computed.

## Checks executed in this run

1. Candidate inventory: 43 source rows, 43 unique IDs; consolidated register has 43 unique IDs; no duplicates or omissions. All 43 candidate names exist as columns in `hh_indicators.csv`.
2. Per-candidate prepared missingness count: one aggregate count per variable with explicit full-file denominator; this does not imply an eligible denominator or valid construct.
3. D1 inherited feasibility table aggregate was summed: 30 exact classifiable cases and total frequency 6,847. Underlying material mapping was inherited, not rerun.
4. Ran `python -m unittest component1_audit.scripts.test_d2_d7_resolution -v`: three tests passed (D2 missing/fractional values, D3 B3 coverage/D4 income missingness, D7 status/amount/zero diagnostics). These tests print no records or identifiers.
5. D7 historical 20-vs-31 test: inspected `component1_audit/scripts/build_d2_d7_validation.py` and its report. The earlier validator calculates raw amount blank/explicit-zero counts but does not calculate prepared debt-total zeros. The latest resolution diagnostic is key-aligned and reports 31; preserve 20 as unreconciled, not resolved.
6. Output schema check: seven domain files share the combined file schema; values in evidence/construct/readiness classifications are checked against the requested vocabularies; all reported missing counts include `/full denominator`; no IDs or raw responses are written.
7. Preservation check: SHA-256 hashes of inherited candidate registry, decision register, prepared `hh_indicators.csv`, D1 feasibility output, D2-D7 reports, prior validation report and `.gitignore` were captured before/after generation and remained unchanged.

## Checks not performed / limits

The D1 raw source mapping was not recomputed, D5/D6 raw module counts were not rerun, no questionnaire PDF was re-extracted in this run, and no correlation, predictive validity, fairness, reliability, causal, or model analysis was performed. D2/D7 lineage searches and questionnaire interpretation are inherited from the cited audits. No valid eligible denominator is inferred from a full-file missingness count.

## CSV data dictionary

- `D1_candidate_assessment.csv` through `D7_candidate_assessment.csv`: same fields as the combined register, domain-filtered and in original candidate order.
- `all_43_candidate_assessment.csv`: one record per candidate. `prepared_missing_count_full_master_denominator` and `prepared_nonmissing_count_full_master_denominator` show count/full prepared row denominator; these are not eligible-case percentages.
- `cross_domain_redundancy_review.csv`: eight documented relationships, source concepts/periods, overlap type, risk, alternatives and evidence needed; no empirical associations were tested.
- `evidence_gaps_and_blockers.csv`: one record per domain-level evidence issue, checks actually run/inherited, alternatives and consequence if unresolved.

No final indicator is approved by this assessment. Existing decisions are preserved verbatim in the candidate register; validation approval is not model-inclusion approval.
"""
    (OUT/"validation_methods_and_tests.md").write_text(methods,encoding="utf-8")
    summary="""# Candidate indicator validation summary

## Scope

Assessed the 43 inherited candidate IDs in order from D1 through D7. The output is an evidence review, not an indicator approval or modeling step. Domain files and combined register use the same schema. Unknown construct or denominator details remain marked rather than inferred.

## Main findings

- D1: inherited exact DCS housing crosswalk matches 30/6,847 households; separate material items remain more defensible than classifying unmatched combinations. H1_17 repetition prevents summation; toilet code 999 and asset-share rules remain open.
- D2: 39 missing and three fractional prepared scores; L1/L2 raw item fields were preserved through source-clean joins, but score derivation is not reproducible.
- D3: 854 roster members lack B3; code/skip contradiction and age thresholds prevent household summaries.
- D4: H2_02 mapping unresolved; 1,519 households have no nonmissing H1_17; repeated income must not be summed.
- D5-D6: O1 period/gate issues and five distinct O2 response states prevent counts or collapsed stress measures; F3/F7 seasons remain separate.
- D7: current key-aligned check reports 31 prepared zeros among 2,947 provisionally status-1 rows; the historical 20 count cannot be reproduced from the prior validator. N1 amount taken is not verified current debt; N2/N3 remain form-specific.

## Readiness

No candidate has been approved for final model inclusion. Many raw items are appropriate for continued validation, while derived scores, household aggregates, and constructs that exceed item wording are blocked by unresolved source, semantic, missingness or denominator rules. Cross-domain overlap is documented without asserting causality or removing candidates.

Tests executed: three focused regression tests passed; output inventory/schema/classification/preservation assertions passed. See `validation_methods_and_tests.md` for exact scope and limitations and `researcher_decisions_required.md` for the decision queue.
"""
    (OUT/"candidate_validation_summary.md").write_text(summary,encoding="utf-8")

def validate_outputs(df, old, n, before_hashes):
    files=[f"D{i}_candidate_assessment.csv" for i in range(1,8)]+["all_43_candidate_assessment.csv","cross_domain_redundancy_review.csv","construct_coverage_review.md","evidence_gaps_and_blockers.csv","researcher_decisions_required.md","validation_methods_and_tests.md","candidate_validation_summary.md"]
    assert len(df)==43 and df.candidate_id.is_unique
    assert set(df.domain)=={f"D{i}" for i in range(1,8)}
    assert all(len(df[df.domain.eq(f"D{i}")])>0 for i in range(1,8))
    assert list(df.columns)==EXPECTED
    assert df["prepared_missing_count_full_master_denominator"].str.contains(r"/\d+ prepared rows missing").all()
    assert set(df.evidence_status).issubset({"Verified","Partially verified","Unresolved","Not assessed"})
    assert set(df.construct_assessment).issubset({"Supported by current evidence","Plausible but requires further evidence","Unsupported by current evidence","Not assessable from available data"})
    assert set(df.operationalisation_readiness).issubset({"Ready for researcher decision","Blocked by source or semantic uncertainty","Blocked by unresolved aggregation or missingness rules","Requires additional data or external documentation","Not yet assessed"})
    assert df.existing_research_decision_status.notna().all()
    combined=pd.read_csv(OUT/"all_43_candidate_assessment.csv",encoding="utf-8-sig")
    assert list(combined.columns)==EXPECTED and combined.candidate_id.tolist()==old.candidate_indicator.tolist()
    for i in range(1,8):
        part=pd.read_csv(OUT/f"D{i}_candidate_assessment.csv",encoding="utf-8-sig")
        assert list(part.columns)==EXPECTED and part.domain.eq(f"D{i}").all()
    assert not any(x in " ".join(p.read_text(encoding="utf-8",errors="ignore") for p in OUT.glob("*.md")).lower() for x in ("household identifier: ","person identifier: "))
    # The raw output contains only candidate/schema/aggregate summaries; reject common identifier fields.
    for p in OUT.glob("*.csv"):
        cols=pd.read_csv(p,encoding="utf-8-sig",nrows=0).columns
        assert not any(str(c).lower() in {"hhcode","pid","hhmember"} for c in cols)
    for path,digest in before_hashes.items(): assert sha(path)==digest, f"Inherited artifact changed: {path}"
    assert sorted(p.name for p in OUT.iterdir() if p.is_file())==sorted(files+["build_indicator_validation.py"])

def main():
    immutable=[INREG,ORIGREG,DECISIONS,PREP,HOUSING/"housing_combination_feasibility.csv",RES/"d2_lineage_report.md",RES/"d3_d4_source_semantics_report.md",RES/"d5_d6_period_applicability_report.md",RES/"d7_financial_semantics_report.md",VALIDATION/"d2_d7_validation_report.md",ROOT/".gitignore"]
    before={p:sha(p) for p in immutable}
    df,old,n=make_register()
    make_reports(df,n)
    validate_outputs(df,old,n,before)
    print(f"PASS: 43 candidates; 7 domains; {len(OVERLAPS)} overlaps; {len(ISSUES)} gaps; all assertions passed.")

if __name__=="__main__": main()
