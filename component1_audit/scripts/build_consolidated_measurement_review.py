"""Consolidate existing D1-D7 measurement audits into review registers.

Reads existing review artifacts only; does not read or modify survey microdata.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "component1_audit" / "outputs" / "consolidated_measurement_review"
REG = ROOT / "component1_audit" / "outputs" / "indicator_registry_review.csv"
DEC = ROOT / "component1_audit" / "outputs" / "research_decisions_status.csv"
HOUSING = ROOT / "component1_audit" / "outputs" / "d1_housing_material_validation"
RES = ROOT / "component1_audit" / "outputs" / "d2_d7_resolution"

PAGE = {
    "d1_income_month": "H1_17, questionnaire p.146",
    "d1_poor_walls": "C1_04, questionnaire pp.14-15",
    "d1_poor_floor": "C1_05, questionnaire p.15",
    "d1_poor_roof": "C1_06, questionnaire p.15",
    "d1_bad_toilet": "C1_08, questionnaire p.16",
    "d1_crowded": "C1_02 and B0 roster, questionnaire pp.14 and 7-8",
    "d1_weak_tenure": "C1_07, questionnaire p.16",
    "d1_housing_deprivation": "C1_02/C1_04-C1_08, questionnaire pp.14-16",
    "d1_asset_share": "D asset module, questionnaire pp.17-21 (itemwise crosswalk required)",
    "d1_income_pc": "H1_17 p.146; B0 roster pp.7-8",
    "d1_income_missing": "H1_17 p.146",
    "d2_fies_raw": "L1_01-L1_08 and L2_01-L2_08, questionnaire pp.178-182",
    "d3_dep_ratio": "B0_04_years/months, p.8",
    "d3_share_child": "B0_04_years/months, p.8",
    "d3_share_elderly": "B0_04_years/months, p.8",
    "d3_any_disability": "B3_01/B3_02, p.12",
    "d3_chronic_share": "B3_01/B3_02, p.12",
    "d3_activity_limited_share": "B3_03, p.13",
    "d4_n_workers": "H1_01 and H2_02, pp.139-146",
    "d4_n_unemp_seeking": "H1_01/H1_13, pp.139, 145",
    "d4_irregular_share": "H1_08, questionnaire pp.139-146",
    "d4_informal_share": "H1_04/H1_11, questionnaire pp.139-146",
    "d4_unemployed_12m": "H1_05/H1_05a, p.143",
    "d4_no_worker": "H1_01 and H2_02, pp.139-146",
    "d5_n_shocks_any": "O1_01_1-O1_01_20, pp.201-203",
    "d5_n_shocks_severe": "O1_01_1-O1_01_20, pp.201-203",
    "d5_severity": "O1_01_1-O1_01_20, pp.201-203",
    "d5_price_shock": "O1_01_1/O1_01_2/O1_01_5/O1_01_6, pp.201-203",
    "d5_income_shock": "O1_01_3/O1_01_4, pp.201-203",
    "d5_health_shock": "O1_01_7, p.202",
    "d5_climate_shock": "O1_01_9-O1_01_13, pp.202-203",
    "d5_agri_shock": "O1_01_11-O1_01_18, pp.202-203",
    "d6_used": "O2_01-O2_18 selected items, pp.203-208",
    "d6_exhausted": "O2_01-O2_18 selected items, pp.203-208",
    "d6_stress_share": "O2_01-O2_18 selected items, pp.203-208",
    "d7_has_debt": "N1_00, p.197",
    "d7_total_debt": "N1_03 institution slots, p.197",
    "d7_n_debt_sources": "N1_01 institution slots, p.197",
    "d7_hard_to_repay": "N1_06 institution slots, p.198",
    "d7_has_bank_account": "N2_01, p.198",
    "d7_able_to_save": "N2_05/N3_05, pp.199-200",
    "d7_n_income_sources": "H1/I/F1/G1; itemwise pages and definition unresolved",
    "d7_debt_income_ratio": "N1_03 p.197 and H1_17 p.146",
}

DOMAIN_NOTES = {
    "d1": "Raw cleaned C/D material, tenure and asset modules are available. Prepared candidate columns exist in hh_indicators.csv, but the precise preparation, missingness, special-code and directional rules are not reproduced by the audited crosswalk. DCS exact combined classification audit: only 30/6,847 households match one published wall-roof-floor combination under exact mappings. Preserve separate material responses; no fallback classification.",
    "d2": "Source L1/L2 core items were compared to delivered bright_csv exports by unique hhcode, with exact cell equality and complete one-to-one key coverage. Prepared score: 39 missing and 3 fractional (0.5, 1.5, 2.5; one each). The three fractional records equal the mean of the two forms' Yes counts in aggregate case diagnostics, which is a hypothesis only; no score derivation or authoritative specification was found.",
    "d3": "B0/B1 keys and age fields match; B3 has 27,021 unique keys, all within B0; 854 roster members across 677 households lack B3 records. B3_01 questionnaire codes 1=No/2=Yes conflict with skip text referring to 1; clean values are 0/1 and not semantically resolved. Age years and months remain separate.",
    "d4": "H1/H2 each have 27,883 unique hhcode+hhmember keys and key sets match; H1 has 8 keys outside B0. H2_02-to-clean H2 h1_02 mapping remains unresolved. H1_17 is monthly household income in LKR repeated on person rows: 6,663 households have multiple H1 rows, 5,328 one consistent nonmissing value, zero conflicts and 1,519 no nonmissing value. Never sum repeats.",
    "d5": "O1 codes: 1 severe impact, 2 moderate impact, 3 no impact. Past-12-month period is explicit for item 20 only; items 1-19 common period is unverified. Printed participation gates are item-specific. F3 Maha 2023-24 and F7 Maha 2024-25 are separate seasons.",
    "d6": "O2 is past-12-month coping. Keep 1 Yes, 2 No because unnecessary, 3 action stopped before period, 4 N/A, and 5 prefer not to say distinct. O2_05/O2_06 have F1_00a=1 gates; multi-select follow-ups are separate from core responses. No combined or count measure is approved.",
    "d7": "Clean/export N1, N2 and N3 values match for selected fields after hhcode joins, but questionnaire-to-export 1/2 versus 0/1 direction is unresolved. Latest key-aligned check: among 2,947 n1_0=1 rows, 31 prepared d7_total_debt zeros; 11 with all 13 amount slots blank; 12 with no positive amount slot. Earlier 20 prepared-zero claim is unreconciled. N1_03 asks loan amount taken, not verified outstanding balance. N2/N3: 1,453 differences in 5,393 paired nonmissing responses; forms remain separate.",
}

def decision_status(row):
    d = str(row["researcher_candidate_decision"])
    if d.startswith("APPROVED"):
        return "approved for stated validation/raw-reference scope only; final indicator inclusion open"
    if d.startswith("DEFERRED"):
        return "deferred by recorded decision; no implementation"
    return "open; no final inclusion decision recorded"

def enrich(r):
    name = r["candidate_indicator"]
    domain = name[:2]
    source = str(r["candidate_source_modules"])
    return {
        "domain": domain.upper(),
        "candidate_construct": r["proposed_construct"],
        "questionnaire_module_item_page": PAGE.get(name, "See source item crosswalk"),
        "source_module_file_and_fields": source + "; " + str(r["candidate_source_variables"]),
        "prepared_variable_name": name + " (column present in Data/processed/hh_indicators.csv)",
        "measurement_level_unit": "Proposed household-level candidate; source level is person-level for B0/B3/H1/H2 and household-level for other named household modules. The candidate aggregation is not validated unless noted.",
        "respondent_universe": "As defined by the questionnaire/module; candidate-specific household respondent selection or eligible member denominator remains unresolved where aggregation is proposed.",
        "reference_period": r["reference_period"],
        "source_lineage_reproducibility": DOMAIN_NOTES[domain],
        "missing_applicability_special_code_handling": r["missing_data_treatment"] + "; " + DOMAIN_NOTES[domain],
        "proposed_interpretation_and_evidence": r["questionnaire_wording_or_item_label"] + "; " + r["evidence"],
        "known_limitations_measurement_error": r["source_mapping_correction_or_note"] + "; Proposed rule: " + r["proposed_aggregation_rule"],
        "cross_domain_overlap": overlap_for(name),
        "alternative_operationalisations_tradeoffs": "Preserve raw source items/form-specific or person-level records (highest provenance, less compact); define an item-specific household rule after universe/code validation (more usable, adds assumptions); defer the construct (avoids unsupported coding, loses candidate evidence).",
        "evidence_needed_before_approval": r["review_gate"],
        "existing_researcher_scope_decision": r["researcher_candidate_decision"],
        "decision_status": decision_status(r),
        "expected_direction_inherited_not_validated": r["expected_direction"],
    }

def overlap_for(name):
    if name.startswith("d1_income") or name == "d1_income_month": return "D1 income-D4 livelihood; income source repeats at person grain."
    if name.startswith("d1_") and any(x in name for x in ("wall", "floor", "roof", "toilet", "tenure", "crowd", "housing")): return "D1 housing/crowding-D3 household size/needs; crowding uses overlapping member count."
    if name.startswith("d2_"): return "D2 food access-D6 food-related coping; same broad 12-month period, different experience/action constructs."
    if name.startswith("d3_"): return "D3 member age/health-D5 household health shocks; different units, gates and periods."
    if name.startswith("d4_"): return "D4 employment-D1 income and D5 income/employment shocks; constructs and periods partly overlap."
    if name.startswith("d5_"): return "D5 shocks-D4 labor/income, D3 health, and D6 coping; event, state and response can overlap."
    if name.startswith("d6_"): return "D6 coping-D2 food access and D7 borrowing/savings/asset depletion; responses may be consequences or co-occurring capacity measures."
    return "D7 financial access/debt/savings-D6 coping and D1 income/assets; temporal/causal relationship is not established."

def build_candidates():
    source = pd.read_csv(REG, encoding="utf-8-sig").fillna("")
    rows = [enrich(r) for _, r in source.iterrows()]
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "candidate_indicator_register.csv", index=False, encoding="utf-8-sig")
    return len(out)

def build_overlaps():
    rows = [
        ["D1 income vs D4 livelihood", "H1_17 monthly household income (p.146); H1_01 current employment, H1_05 past 12 months, H1_13 last four weeks (pp.139-145).", "Conceptual; partial temporal overlap, not causal evidence.", "Repeated H1_17 can multiply income; combining income/status can overweight labor market hardship; dropping either loses resource or work-status information.", "Keep household income and person labor status separately; any/count/share/reference-person alternatives require a defined eligible universe.", "Resolve H1_17 specials/source values and H2_02 mapping; researcher chooses later representation."],
        ["D1 housing/crowding vs D3 household size/needs", "C1_02 bedrooms and C1_04-C1_08 material/tenure (pp.14-16); B0 roster/age (pp.7-8).", "Conceptual, cross-sectional; no crowding threshold established.", "Bedroom count and member count enter both constructs; combining can overweight household size. Removing either loses housing condition or occupancy context.", "Preserve separate housing/material and age/member items; crowding alternatives require bedroom definition, roster numerator, zero handling and cutoff.", "Resolve source codes, roster universe, bedroom handling, age thresholds and purpose."],
        ["D1 assets vs D6 coping / D7 finance", "D asset ownership/functionality items (pp.17-21); O2_01 asset sale past 12 months (pp.203-208); N1 borrowing p.197 and N2/N3 savings p.199-200.", "Conceptual/possible temporal relationship; causal order unknown.", "Asset stock versus asset sale/coping action may double-count or confuse capacity with depletion.", "Retain asset items and coping/finance items separately; a stock/depletion construct would need longitudinal/reference-period evidence.", "Verify asset item universe and availability, O2 period/gates, N1 meaning and N2/N3 respondent semantics."],
        ["D2 food access vs D6 food-related coping", "L1/L2 food-access experiences (pp.178-182); O2 food/money coping (pp.203-208), both broad past 12 months.", "Conceptual and temporal overlap; cross-sectional association does not show causality.", "Counting both may overweight hardship; removing coping loses response/adaptation information, removing D2 loses direct access evidence.", "Keep as separate experiences/actions; compare only after respondent, response-category and item-gate rules are validated.", "Recover FIES scoring/form protocol and O2 itemwise applicability/missingness."],
        ["D3 health conditions vs D5 health shocks", "B3_01/B3_02 and B3_03 (pp.12-13); O1_07 household illness/death/injury (p.202), O1 period unknown.", "Conceptual; temporal link unverified; member condition differs from household shock.", "A chronic/severe condition and an acute family event may both signal need; removing either loses distinct ongoing condition/event information.", "Keep member and household items separate; any-member/share alternatives require confirmed B3 coverage, gate and denominator.", "Resolve B3_01 code/skip, B3_03 category 7 timeframe, B3 coverage and O1 period."],
        ["D4 employment/income vs D5 shocks", "H1_05 past 12 months, H1_13 last four weeks (pp.143,145); O1_04 employment/income shock (period unstated in table), O1_20 past 12 months (p.203).", "Conceptual, partly temporal; event and status differ. No causal inference.", "Same event might be recorded as shock and unemployment; dropping shock loses impact, dropping employment loses current/past work state.", "Preserve both with separate units and periods; revisit only after O1 period and intended construct are established.", "Confirm O1 time frame, impact reference, and H1 respondent/eligible person rules."],
        ["D6 coping vs D7 debt/savings/asset depletion", "O2 coping items past 12 months (pp.203-208); N1 owing/amount taken and repayment difficulty (pp.197-198); N2/N3 saving ability past 12 months (pp.199-200).", "Conceptual; possible temporal overlap for savings/coping; direction is hypothesis only.", "Borrowing or selling assets may be coping action and financial exposure; savings may be capacity/protection. A composite may mix directions.", "Keep action, access, and financial capacity separate; cross-form N2/N3 must remain separate pending respondent rule.", "Verify N1 balance semantics/code direction, N2/N3 forms, and O2 categories/gates."],
        ["D1 housing/material vs D5 shocks", "Current C1 housing/material items (pp.14-16); O1 housing damage/shock items (pp.201-203), items 1-19 period unknown.", "Conceptual; current stock and shock/impact event are distinct; timing unknown.", "Housing quality plus damage response could count the same disadvantage twice, while damage may be a new event.", "Preserve stock and event fields separately; consider event-specific review once period/impact wording is verified.", "Verify O1 item period and relevant C1 condition/response coding."],
    ]
    cols=["overlap_pair","concepts_questions_periods","relationship_type_and_evidence_limit","double_counting_or_information_loss","alternative_treatments_and_tradeoffs","evidence_needed_before_researcher_decision"]
    pd.DataFrame(rows,columns=cols).to_csv(OUT/"cross_domain_overlap_register.csv",index=False,encoding="utf-8-sig")

ISSUES = [
    ("ISS-01","Blocking indicator interpretation","D1 combined housing classification","Only 30/6,847 exact housing-material triplets matched a published DCS 2024 combined wall-roof-floor rule under audited exact mappings; many observed combinations are unmatched/ambiguous.","Retain three material items separately; seek DCS/BRIGHT harmonisation; defer combined class.","Separate items preserve observed evidence; crosswalk can support comparability if validated; deferral avoids invented status but limits composite use.","Do not infer a class for unmatched triplets or generalize a hierarchy."),
    ("ISS-02","Blocking indicator interpretation","D1 C1_08 toilet Other code","Questionnaire lists codes 1-14 but has follow-up text for 999; exact mapping is unresolved.","Keep 999 raw pending platform/export mapping; defer toilet candidate coding until verified.","Raw retention preserves answer; mapping adds interpretability but may misclassify Other without source form evidence.","Cannot classify 999 or derive improved sanitation categories reliably."),
    ("ISS-03","Blocking indicator interpretation","D2 FIES score and form choice","39 missing and 3 fractional values; L1/L2 item source values preserved; prepared score derivation/spec absent.","Form-specific raw items; choose respondent/form using survey design; or obtain an approved combination protocol.","Raw preserves provenance but no household score; single form requires eligibility/design evidence; combination captures reports but introduces duplicate/partial/DK rules.","Do not interpret d2_fies_raw as validated scale or implement score."),
    ("ISS-04","Blocking indicator interpretation","D3 B3 code and skip semantics","Questionnaire B3_01 lists 1 No/2 Yes but B3_02 skip says B3_01=1; cleaned B3_01 0/1 direction unresolved.","Recover questionnaire/export map; retain unlabeled codes/categories; defer recode.","Lineage clarifies response meaning; raw retention avoids false direction but limits interpretation.","B3_02 and household health indicators remain uninterpretable/conditional."),
    ("ISS-05","Blocking indicator interpretation","D3 B3_03 time/category mismatch","Question states last year; code 7 means main activities interrupted completely more than 12 months ago.","Preserve seven categories; exclude code 7 only from explicitly time-bounded analysis after approval; request instrument clarification.","Raw retains information; exclusion improves period alignment but drops valid category; clarification is strongest but may take time.","No recent-period summary or ordering should be derived."),
    ("ISS-06","Blocking indicator interpretation","D4 H2_02 mapping and employment construct","H2_02 second-job question is not transparently mapped to cleaned H2 h1_02; job/member concept is unresolved.","Keep person/item responses raw; map after checking export field IDs/programming; defer worker/no-worker constructs.","Raw is safe but incomplete; verified map supports secondary work but still needs person-vs-job definition.","No workers count or household worker flag."),
    ("ISS-07","Blocking indicator interpretation","D4 H1_17 income semantics","H1_17 household monthly LKR income on H1 person rows; 6,663 multi-record households, 5,328 one consistent nonmissing value, 1,519 none; special codes/prepared formula unresolved.","Use one consistent raw household answer only after lineage/special-code approval; keep missing if unresolved; recover intended respondent rule.","Selection retains data but assumes repeated answers equivalent; conservative missing loses data; lineage recovery is strongest.","Do not sum repeated values; per-capita, missingness and debt-income ratio remain blocked."),
    ("ISS-08","Blocking indicator interpretation","D7 N1 debt semantics","N1_00 questionnaire 1=No/2=Yes vs delivered clean/export 0/1; N1_03 is amount taken, not established outstanding balance.","Recover export recode; use raw unlabeled values pending; defer debt burden without current balance evidence.","Lineage permits interpretation; raw preserves values but cannot label; loan amount taken is not debt stock.","Do not interpret prepared total or ratio as current burden."),
    ("ISS-09","Blocking indicator interpretation","D7 prepared zero discrepancy","Earlier report states 20 prepared zeros but old validation script did not calculate prepared-zero counts. Latest key-aligned resolution reports 31 among n1_0=1. No underlying 20-case diagnostic is present in existing artifacts.","Preserve both as historical claims, prefer neither until a reproducible lineage identifies exact source/universe; current builder's key-aligned 31 is reproducible.","31 is transparent and current; 20 may have a different historical filter but its denominator/predicate cannot be checked; choosing prematurely risks invalid reconciliation.","Treat 20 as unreconciled; no inference that the 11/12 raw slot groups must equal either zero count."),
    ("ISS-10","Blocking indicator interpretation","D7 N2/N3 savings","1,453 differences among 5,393 paired nonmissing records; forms ask 'you' and are men/women forms; clean 0/1 direction unresolved.","Keep form-specific; choose target respondent after survey design review; combine only with approved household rule.","Separate forms preserve perspective; selection omits other respondent; combination risks direction and duplicate-response assumptions.","No unified savings ability measure or income-saved feature."),
    ("ISS-11","Blocking indicator interpretation","D5 O1 reference period and gates","O1_20 explicitly past 12 months; O1_01_1-19 common period unverified; gates include F1/G1/G2/I and blanks need applicable universe.","Retain item-level raw; period-confirmed subset; obtain instrument/programming clarification.","Raw broadest but periods differ; subset is more comparable but excludes items; clarification allows stronger interpretation.","No shock counts/severity/composite."),
    ("ISS-12","Blocking indicator interpretation","D6 O2 category and follow-up semantics","Five response categories distinguish Yes, unnecessary, discontinued, N/A, prefer not to say; follow-up multi-selects and F1 gate are separate.","Retain categorical responses; define approved action grouping; defer uncertain applicability items.","Categorical preserves distinctions; grouping simplifies but collapses states; deferral avoids unsupported denominators.","No coping-used/exhausted flag/count/share."),
    ("ISS-13","Required before household-level aggregation","D3 member ages/needs aggregation","Age recorded separately in years/months; 854 B0 roster members lack B3 records; age bands and roster denominator not approved.","Member-level records; age bands with approved thresholds; dependency ratio with explicit denominator.","Member-level avoids aggregation assumptions; bands are interpretable; ratio is compact but threshold-sensitive and coverage-dependent.","No shares, ratios or any-member flags until denominator and absent-module meaning are resolved."),
    ("ISS-14","Required before household-level aggregation","D4 employment representation","Person/job records and eligibility unresolved; H1_05/H1_13 are person items, H2 mapping unresolved.","Person-level references; any-member; count; eligible-member proportion.","Raw preserves detail; any-member is simple/size-sensitive; count favors large households; proportion depends on reliable eligible denominator.","No household employment aggregate."),
    ("ISS-15","Required before household-level aggregation","D1 income/assets and denominator rules","H1_17 repetition/special values; asset-share denominator not defined; household-size denominator and no-answer behavior unresolved.","Single consistent household H1_17 answer with approval; raw asset items; define an eligible-item denominator only after review.","A selected income value retains observations but assumes repetition; raw asset items preserve detail; share needs comparable denominator.","No per-capita income, missingness feature, asset share/index."),
    ("ISS-16","Required before household-level aggregation","D5/D6 missingness and eligibility","Item gates yield eligible blanks, gate-no values, unknown gate and explicit response categories that are distinct.","Item-specific denominators; explicit structural-missing state; complete-case subset after approval.","Item denominators retain coverage; skip coding clarifies eligibility; complete-case is simple but can select a nonrepresentative subset.","No cross-item sum/share or imputation."),
    ("ISS-17","Required before model construction","D5 F3/F7 agricultural season","F3 Maha 2023-24 and F7 Maha 2024-25 are different periods; existing DEC-23 keeps separate pending target.","Keep separate; select one target season; sensitivity comparison if same construct/coverage.","Separate preserves time; selection aligns target but excludes a season; comparison informs robustness but is not one feature.","No season selection or pooled value."),
    ("ISS-18","Required before model construction","Cross-domain redundancy and construct roles","Income/work, housing/household size, food access/coping, health/shocks, and coping/finance overlap conceptually, but units and periods differ.","Retain distinct candidates; combine only with a shared construct/time basis; compare sensitivity later.","Retention preserves information but may double-weight; combination reduces dimensions but loses distinctions and assumes equivalence; sensitivity is informative after valid measurement.","Do not remove an item solely for correlation or infer causality."),
    ("ISS-19","Important sensitivity analyses","D1 DCS exact housing crosswalk sensitivity","Only 30/6,847 exact triplets match DCS combined rules; approximate mappings were excluded and no hierarchy exists.","Base case exact mappings only; separate individual materials; sensitivity mapping only if approved DCS equivalence is documented.","Exact mapping is conservative and low coverage; approximate mapping may increase coverage but adds classification error; separate items avoid class assumptions.","Report mapping-coverage sensitivity; never treat unmatched as a status."),
    ("ISS-20","Important sensitivity analyses","D2 form-specific versus approved FIES method","Three fractional cases match mean form Yes counts, but this alone does not identify score origin; forms are separate respondents.","No score/raw items; one-form design; pre-specified combined scoring/partial response alternatives.","No score avoids unvalidated use; one form has respondent-selection risk; combination has duplicate/partial/DK/refusal risks.","If a scoring protocol is later supplied, compare only pre-registered alternatives and retain missingness detail."),
    ("ISS-21","Important sensitivity analyses","D7 20 vs 31 prepared-zero claims","Latest independent check yields 31; earlier report says 20 without code that computes the predicate.","Reproduce 20 from its original data/query if found; otherwise retain as unresolved historical result and use 31 only as the current reproducible check.","Original replay could explain universe/filter; current result is reproducible now; assuming equivalence is not justified.","No debt zero recoding; zero and missing stay separate."),
]

def build_issues():
    cols=["issue_id","urgency_group","candidate_or_decision","verified_evidence_and_denominator","available_alternatives","advantages_and_disadvantages","consequence_if_deferred"]
    pd.DataFrame(ISSUES,columns=cols).to_csv(OUT/"unresolved_measurement_issues.csv",index=False,encoding="utf-8-sig")

def build_decisions_md():
    text = """# Researcher decisions required

These are review choices, not implementation approvals. Existing approvals apply only to stated validation or raw-reference scope. Deferring any choice leaves the related candidate uninterpreted or unavailable for aggregation/model construction.

## Blocking indicator interpretation

1. **D1 housing classification and material coding.** Evidence: only 30 of 6,847 households exactly match a published DCS 2024 wall-roof-floor classification under audited exact mappings; C1_08 also has a code-list/999 follow-up discrepancy. Alternatives: retain C1 material items separately (preserves observations, no combined status); request authoritative code equivalence (better comparability, requires source evidence); defer combined classification (safe but limited). Deferral means unmatched triplets stay unclassified. No unmatched combination should receive a DCS class by hierarchy or analogy.
2. **D2 respondent and FIES rule.** Evidence: 39 missing and 3 fractional prepared values; L1/L2 source items match exports but score derivation is absent. Alternatives: retain forms separately; select a respondent/form under documented survey design; use a validated pre-specified combination and partial-response rule. Separate forms preserve informant perspectives but yield no score; respondent selection may omit information; combination risks double counting and requires DK/refusal/missing rules. Deferral blocks interpreting `d2_fies_raw` as a validated score.
3. **D3 B3 code/skip and B3_03 period.** Evidence: B3_01 displayed 1=No/2=Yes conflicts with skip text B3_01=1; B3_03 last-year wording conflicts with category 7 >12 months. Alternatives: obtain form/export specification; retain codes/categories raw; defer dependent constructs. Source clarification supports interpretation; raw retention avoids false recode but limits meaning. Deferral blocks household health interpretation.
4. **D4 H2_02 and H1_17 semantics.** Evidence: H2_02 is not verified as clean `h1_02`; H1_17 monthly household income repeats on person records, with 5,328 households having one consistent nonmissing value and 1,519 none. Alternatives: recover mapping/cleaning log; keep person-level raw references; use a single consistent H1_17 answer only under approved handling. Recovery is stronger but needs source; raw is safe but limits use; selection assumes repetition validity. Deferral blocks worker constructs, per-capita income and debt-income ratio. Never sum H1_17.
5. **D7 debt status and amount meaning.** Evidence: questionnaire N1_00 1/2 versus exported 0/1; N1_03 asks amount taken, not verified current balance. Latest key-aligned check has 31 prepared zeros among 2,947 `n1_0=1`, with 11 all-slot blank and 12 no-positive-slot cases; earlier 20 claim lacks reproducible predicate in audited artifacts. Alternatives: recover recode/derivation; preserve unlabeled status/slot values; defer debt burden until an outstanding balance is evidenced. Deferral blocks debt-total/ratio interpretation.
6. **D7 savings respondent/codes.** Evidence: N2/N3 differ in 1,453/5,393 paired nonmissing answers, forms are men/women, clean 0/1 direction unresolved. Alternatives: keep separate; define one target respondent; combine with approved household rule. Separate keeps perspectives; selection omits a perspective; combining needs code direction and an aggregation rule. Deferral blocks one household savings-ability measure.
7. **D5/D6 item meaning and response states.** Evidence: O1_20 has a 12-month reference but O1_1-19 do not have a verified common period; item gates are conditional. O2 states distinguish Yes, unnecessary, discontinued, N/A and prefer not to say. Alternatives: retain itemwise categories and denominators; obtain instrument/programming clarification; later define period-specific subsets. Raw preserves meaning but is less compact; subsets improve comparability while omitting items; clarification may take time. Deferral blocks shock/coping counts or shares.

## Required before household-level aggregation

1. **D3 age and health denominators.** Evidence: B0 ages are separate year/month fields; 854 roster members lack B3 records across 677 households. Alternatives: member-level only; approved age-band shares; approved dependency ratio; any-member or eligible-member health share after resolving B3 coverage. Member-level is safest; band/share measures are interpretable but threshold/coverage sensitive. Deferral keeps all D3 candidates unaggregated.
2. **D4 person/job summary rule.** Alternatives: person-level; any-member; count; proportion among eligible members; reference-person measure. Any-member is size-sensitive; counts favor larger households; proportions need a reliable roster and valid H2 mapping. Deferral blocks D4 household aggregates.
3. **D1 household resource and asset rules.** H1_17 needs repeated-value/special-code handling; asset share needs an eligible-item denominator. A selected consistent income value preserves more records but assumes repetition; raw assets preserve evidence but are not a share/index. Deferral blocks per-capita income, missingness flags and asset indices.
4. **D5/D6 structural missingness.** Keep gate-no, gate-unknown, eligible blank, explicit response, and multi-select follow-up distinct. Item-specific denominators retain information but complicate comparison; complete-case subsets simplify but can select a nonrepresentative group. Deferral blocks sums/shares and imputation.

## Required before model construction

1. **D7 debt and income ratio.** Obtain validated debt numerator/current balance, income handling and aligned periods; otherwise defer ratio. A raw loan-taken amount answers a different question; excluding debt burden loses that construct but avoids false current-debt claims.
2. **D5 season choice.** Keep F3 Maha 2023-24 and F7 Maha 2024-25 separate, select a target season, or compare as separate sensitivity measures. Selection improves target alignment but excludes a season; pooling mixes periods. Deferral means no agriculture-season feature.
3. **Cross-domain construct roles.** Keep related but distinct items; combine only if same construct and period are evidenced; or later run sensitivity analyses. Retention preserves information but may double-weight; combination is compact but assumes equivalence; correlation alone supports neither removal nor causality. Deferral means no composite, weight or dependency decisions.
4. **Consumption proxy boundary.** Existing DEC-13 allows separate descriptive sensitivity only; it is not ground truth, eligibility, training target or core candidate. Maintain that boundary unless explicitly revised. Deferral excludes it from indicator/model review.

## Important sensitivity analyses

1. **D1 housing mapping.** Compare exact DCS mapping coverage with separately reported material items. Approximate mappings could improve coverage but add classification error; exact-only mapping is conservative. Do not label unmatched combinations.
2. **D2 FIES protocol.** If an authoritative specification is recovered, compare only pre-specified form/partial-response alternatives while retaining DK/refusal/missing states. The three mean-pattern cases are hypothesis-generating, not proof of the score rule.
3. **D7 zero diagnostics.** Reproduce the historical 20 count from its original query if found; compare predicates only after denominator/source alignment. Current 31 is reproducible; 20 remains an unreconciled historical claim. Do not treat missing amounts as zero.
4. **Overlap and household size.** After source semantics and denominators are approved, inspect sensitivity to distinct housing, age, income/work, shock/health, food/coping and finance constructs. Removing correlated candidates solely on association risks information loss.

No option above has been selected on the researcher's behalf. The full issue inventory, including alternatives and deferral consequences, is in `unresolved_measurement_issues.csv`; candidate-specific evidence and existing scope decisions are in `candidate_indicator_register.csv`.
"""
    (OUT/"researcher_decisions_required.md").write_text(text,encoding="utf-8")

def build_reports(candidate_count):
    housing=pd.read_csv(HOUSING/"housing_combination_feasibility.csv")
    matched=int(housing.loc[housing.feasibility_status.eq("classifiable by verified rule"),"household_count"].sum())
    total=int(housing.household_count.sum())
    summary=f"""# Consolidated D1-D7 measurement review

## Purpose and scope

This consolidates the existing D1 housing/material audit, D1-D7 registry/validation artifacts, and the D2-D7 resolution audit into a candidate measurement register. It is a measurement review only. It does not define an indicator, recode source responses, impute missing values, aggregate household-level candidates, assign weights, create fuzzy memberships/Bayesian dependencies, rank households or make eligibility decisions.

The register contains {candidate_count} inherited candidate names from `component1_audit/outputs/indicator_registry_review.csv`. These are proposals, not validated or approved final features. Previously recorded approval statuses are reproduced with their explicit scope limits.

## Evidence by domain

- **D1 housing, assets and income:** the housing audit reports {matched:,} of 6,847 households ({matched/6847*100:.2f}%) matching one published DCS 2024 wall-roof-floor class under exact audited material mappings. Individual C1 material responses remain the defensible evidence; unmatched combinations are not assigned classes. C1_08 has a 999 discrepancy. H1_17 is addressed below.
- **D2 food access:** 39 missing and three fractional `d2_fies_raw` values (0.5, 1.5, 2.5) were reproduced in the resolution audit. L1/L2 item fields matched their export counterparts after unique-key joins. The derivation remains unreproducible; forms stay separate.
- **D3 household needs:** B3 has 27,021 members, all within B0; 854 roster members across 677 households lack B3 records. B3_01 code/skip conflict remains. Age years/months stay separate; no threshold or household summary is approved.
- **D4 livelihood/income:** H1/H2 key sets match. H1_17 has 6,663 multi-record households; 5,328 with one consistent nonmissing answer; zero conflicts; 1,519 with none. Do not sum repeated household income. H2_02 to clean `h1_02` mapping remains unresolved.
- **D5 shocks:** O1 code states and item gates are preserved. The common period for items 1-19 is unverified; item 20 specifies 12 months. No shock count or severity measure is approved.
- **D6 coping:** O2 retains five different response states and conditional follow-ups. No used/exhausted flag, count or share is approved.
- **D7 debt/savings:** latest key-aligned check has 31 prepared zero totals among 2,947 `n1_0=1`; 11 with all 13 raw amount slots blank and 12 with no positive raw slot. Historical 20 prepared-zero claim remains unreconciled: the prior validation script did not calculate prepared-zero counts and no underlying 20-case predicate is in the reviewed artifacts. N1_03 is amount taken, not confirmed current debt. N2/N3 differ in 1,453 of 5,393 paired nonmissing responses and remain separate.

## Cross-domain measurement risks

Eight overlap pairs are documented in `cross_domain_overlap_register.csv`: D1 income-D4 livelihood; D1 housing/D3 household size and needs; D1 assets-D6/D7; D2 food access-D6 coping; D3 health-D5 health shocks; D4 employment-D5 shocks; D6 coping-D7 finance; and D1 housing-D5 shocks. These are conceptual or temporal overlaps, not proof of causal relationships or redundancy. No candidate is removed because it may correlate with another.

## Decisions and limits

Blocking semantic decisions include D1 exact material mapping/Other codes; D2 respondent and score protocol; D3 B3 code/skip and time categories; D4 H2 mapping and H1_17 handling; D5 periods/gates; D6 category treatment; and D7 direction, current-balance meaning and N2/N3 respondent rules. Household aggregation additionally needs approved age, member, income, asset and missingness denominators. Model construction remains blocked pending those decisions and later explicit construct/overlap review.

The bottom-quintile consumption proxy remains separate and is not ground truth, eligibility, a training target or a core candidate indicator. Existing decision DEC-13 limits it to separate descriptive sensitivity.

Urgency-grouped options and consequences of deferral are in `researcher_decisions_required.md`; issue-level alternatives and tradeoffs are in `unresolved_measurement_issues.csv`.
"""
    (OUT/"consolidated_measurement_review.md").write_text(summary,encoding="utf-8")

    scope="""# Reproducibility and scope

## Inherited evidence reviewed (not rerun as part of consolidation)

- D1 housing audit: `component1_audit/outputs/d1_housing_material_validation/housing_classification_audit.md`, `housing_combination_feasibility.csv`, `housing_material_crosswalk.csv`, `housing_material_frequency_report.csv`; builder `component1_audit/scripts/build_housing_material_validation.py`. The reported 30/6,847 exact matches are inherited from that audited crosswalk; this consolidation reads its aggregate feasibility CSV, not the source microdata or Census PDF.
- Existing candidate/preprocessing registry: `component1_audit/outputs/indicator_registry_review.csv` (43 candidates), `implementation_status.csv`, `research_decisions_status.csv`, and `updated_issue_register.csv`.
- D1-D7 validation: `component1_audit/outputs/d2_d7_validation/d2_d7_validation_report.md`, `cross_domain_overlap_register.csv`, and builder `component1_audit/scripts/build_d2_d7_validation.py`. The earlier report's debt-zero value 20 is retained as a historical claim. Its builder diagnostics only computed N1 raw all-blank and explicit-zero amount slots; they did not compute prepared zero totals.
- D2-D7 resolution: four domain reports and `research_decisions_pending.csv` in `component1_audit/outputs/d2_d7_resolution/`; builder `component1_audit/scripts/build_d2_d7_resolution.py`; tests `component1_audit/scripts/test_d2_d7_resolution.py`.
- Questionnaire: `Data/BRIGHT_questionnaire_English.pdf`; page/item references appear in the candidate and issue registers. DCS reference cited by inherited D1 audit: Department of Census and Statistics, Census of Population and Housing 2024 Final Report, section 11.5, printed p.189.

## Checks executed for this consolidation

- Read the inherited 43-row candidate registry and decision register; wrote a consolidated 43-row register without touching source registers.
- Read the inherited D1 aggregate combination table and summed the exact-match status: 30 classifiable households; total of all listed triplet frequencies is 6,847. The underlying D1 material-code mapping was not rerun here.
- Reviewed the earlier D7 validator implementation: its reported 20 prepared zeros were cited in its prose but not calculated by that script. The latest resolution builder joins N1 and prepared totals on unique `hhcode`, validates one-to-one cardinality, and reproduced 31. Therefore the earlier 20 cannot be reconciled from existing audited predicates; denominator/predicate are absent.
- No source microdata, questionnaire records, free text, identifiers, prepared variables or pipeline artifacts were changed. No new diagnostic aggregation was run for this consolidation.

## Output data dictionary

- `candidate_indicator_register.csv`: one row per inherited candidate; includes source/module/page fields, proposed prepared column, source/unit/universe, lineage and missingness limits, overlap, alternatives, evidence needed, and inherited scope decision. The prepared-variable column exists in `Data/processed/hh_indicators.csv`; existence does not establish derivation or approval.
- `cross_domain_overlap_register.csv`: one row per documented pair; columns describe concepts/questions/periods, relationship evidence limits, double-counting or information-loss risks, options, and remaining evidence.
- `unresolved_measurement_issues.csv`: one row per issue; records urgency group, evidence/denominator, alternatives, pros/cons, and deferral consequence.
- `researcher_decisions_required.md`: decisions grouped by the four requested urgency classes, with alternatives and tradeoffs.
- `consolidated_measurement_review.md`: summary and consolidated findings.
- `reproducibility_and_scope.md`: provenance, inherited versus executed checks, and CSV dictionaries.

No new substantive decision is marked approved. Validation-scope approvals in prior records do not authorize final indicator inclusion.
"""
    (OUT/"reproducibility_and_scope.md").write_text(scope,encoding="utf-8")

def overlap_for_stub():
    return ""

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    count=build_candidates()
    build_overlaps()
    build_issues()
    build_decisions_md()
    build_reports(count)
    print(f"Wrote six consolidated review outputs; candidates={count}; unresolved issues={len(ISSUES)}")

if __name__ == "__main__":
    main()
