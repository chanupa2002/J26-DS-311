"""Export the existing provisional workbook map with explicit review fields.

This script preserves the mapping text in the existing workbook and does not
interpret or approve candidate indicators. It creates a CSV review copy.
"""

from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
WORKBOOK = ROOT / "component1_audit" / "outputs" / "variable_mapping.xlsx"
OUTPUT = ROOT / "component1_audit" / "outputs" / "indicator_registry_review.csv"
NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def column_number(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref).group(0)
    value = 0
    for char in letters:
        value = value * 26 + ord(char) - ord("A") + 1
    return value - 1


def read_first_sheet(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in rels}
        first = workbook.find(".//main:sheet", NS)
        if first is None:
            raise ValueError("Workbook has no worksheets")
        target = targets[first.attrib[f"{{{NS['rel']}}}id"]]
        sheet_path = "xl/" + target.lstrip("/")
        if sheet_path not in archive.namelist():
            sheet_path = "xl/worksheets/" + Path(target).name
        sheet = ET.fromstring(archive.read(sheet_path))
        rows = []
        for row in sheet.findall(".//main:sheetData/main:row", NS):
            cells = row.findall("main:c", NS)
            values = [""] * (max((column_number(c.attrib["r"]) for c in cells), default=-1) + 1)
            for cell in cells:
                inline = cell.find("main:is", NS)
                text = "".join(t.text or "" for t in inline.findall(".//main:t", NS)) if inline is not None else ""
                values[column_number(cell.attrib["r"])] = text
            rows.append(values)
        return rows


def main() -> None:
    rows = read_first_sheet(WORKBOOK)
    headers, records = rows[0], rows[1:]
    extra = ["questionnaire_review_status", "source_mapping_correction_or_note",
             "review_candidate_name", "implementation_status", "researcher_candidate_decision", "review_gate"]
    verified_d1 = {
        "d1_income_month": (
            "QUESTION_TEXT_AND_UNIT_VERIFIED",
            "H1_17 asks total monthly household income in LKR; integer response (PDF p.146). Special-code semantics remain unresolved.",
        ),
        "d1_income_pc": (
            "SOURCE_ITEM_VERIFIED_DERIVATION_PENDING",
            "Uses H1_17 monthly household income plus roster count; per-capita denominator/eligibility and missingness rule are not questionnaire-defined.",
        ),
        "d1_income_missing": (
            "SOURCE_ITEM_VERIFIED_DERIVATION_PENDING",
            "H1_17 item is verified, but missingness categories cannot be distinguished from this item text alone; current feature formula unavailable.",
        ),
        "d1_poor_walls": (
            "QUESTION_TEXT_AND_CODES_VERIFIED",
            "C1_04 principal wall material: codes 1-11 plus 999 Other, specify (PDF pp.14-15). Which materials count as deprivation requires approval.",
        ),
        "d1_poor_floor": (
            "CORRECTED_MAPPING_QUESTION_TEXT_AND_CODES_VERIFIED",
            "Corrected from C1_06 to C1_05: C1_05 asks principal flooring material; codes 1-7 plus 999 Other, specify (PDF p.15). Deprivation grouping requires approval.",
        ),
        "d1_poor_roof": (
            "CORRECTED_MAPPING_QUESTION_TEXT_AND_CODES_VERIFIED",
            "Corrected from C1_05 to C1_06: C1_06 asks principal roof material; codes 1-7 plus 999 Other, specify (PDF p.15). Deprivation grouping requires approval.",
        ),
        "d1_bad_toilet": (
            "QUESTIONNAIRE_INTERNAL_CODE_DISCREPANCY",
            "C1_08 asks usual household toilet facility; response list codes 1-14 (PDF p.16), but following text says C1_08=999 triggers Other text although 999 is absent from list. Cleaned export contains code 999 in 22 households and 24 nonblank C1_08_other values. Confirm export/instrument version before recoding.",
        ),
        "d1_crowded": (
            "QUESTION_TEXT_VERIFIED_DERIVATION_PENDING",
            "C1_02 asks integer number of bedrooms (PDF p.14); roster-derived member count is a separate input. Crowding formula and threshold require approval.",
        ),
        "d1_weak_tenure": (
            "QUESTION_TEXT_AND_CODES_VERIFIED",
            "C1_07 asks ownership/tenure of main dwelling; codes 1-8 plus 999 Other, specify (PDF p.15). Which categories indicate deprivation requires approval.",
        ),
        "d1_housing_deprivation": (
            "COMPONENT_ITEMS_VERIFIED_COMPOSITE_PENDING",
            "Candidate combines C1_02, C1_04-C1_08. Composite construction, overlap, direction, and cutoffs are not defined by the questionnaire.",
        ),
        "d1_asset_share": (
            "ASSET_ITEMS_VERIFIED_SHARE_FORMULA_PENDING",
            "Module D has direct counts/ownership questions: D_01,D_03,D_05,D_06,D_08,D_10,D_12-D_23 (PDF pp.19-21). A share denominator and included assets are not specified.",
        ),
        "d3_dep_ratio": (
            "AGE_ITEM_VERIFIED_THRESHOLD_AND_FORMULA_PENDING",
            "B0_04_years asks MEMBER age in years and B0_04_months asks age in months (PDF p.8). Dependency age bands, numerator/denominator, and treatment of age zero/months require approval.",
        ),
        "d3_share_child": (
            "AGE_ITEM_VERIFIED_CUTOFF_PENDING",
            "B0_04_years/months are observed (PDF p.8). Child age boundary and denominator are research choices; do not infer them from the variable name.",
        ),
        "d3_share_elderly": (
            "AGE_ITEM_VERIFIED_CUTOFF_PENDING",
            "B0_04_years/months are observed (PDF p.8). Older-person age boundary and denominator are research choices; do not infer them from the variable name.",
        ),
        "d3_any_disability": (
            "QUESTION_WORDING_MIXED_CONSTRUCT_AND_CODE_CROSSWALK_PENDING",
            "B3_01 asks whether MEMBER has any chronic illness or severe disability (questionnaire codes 1 No, 2 Yes, PDF p.12); B3_02 asks condition type (PDF pp.12-13). It does not measure disability alone. Cleaned b3_01 is 0/1; 0 has no b3_02 responses and 1 has b3_02 responses, but the source recode is unavailable. Questionnaire skip text says B3_01=1 although its code list says 1=No.",
        ),
        "d3_chronic_share": (
            "CANDIDATE_CONCEPT_NOT_DIRECTLY_IDENTIFIED",
            "B3_01 combines chronic illness and severe disability; B3_02 mixes illness and disability categories. A chronic-only share is not directly identified without a reviewed item classification. B3_04 is pregnancy and is not a chronic/disability measure.",
        ),
        "d3_activity_limited_share": (
            "QUESTION_TEXT_VERIFIED_APPLICABILITY_AND_DENOMINATOR_PENDING",
            "B3_03 asks interruption of usual activities because of the chronic illness/disability in the last year; response categories 1-7 include code 7 for complete interruption more than 12 months ago (PDF p.13). Questionnaire skip text refers to B3_01=1, conflicting with 1=No. Cleaned B3_03 is present for 7,566 of 7,616 b3_01=1 rows; 50 are blank. B3 lacks a roster row for 854 members in 677 households.",
        ),
        "d4_n_workers": (
            "QUESTION_TEXT_VERIFIED_SECONDARY_FIELD_CROSSWALK_PENDING",
            "H1_01 asks current employment status (codes 1-10, PDF p.139). H2_02 asks whether a second job was held/worked at least one hour last month (0 No, 1 Yes, PDF p.146). The cleaned H2 file stores its first response as h1_02; exact export crosswalk must be documented. Counting people versus jobs and unpaid activities needs a rule.",
        ),
        "d4_n_unemp_seeking": (
            "CORRECTED_SOURCE_MAPPING_QUESTION_TEXT_VERIFIED",
            "Corrected to H1_01 current status and H1_13 active job search during the last four weeks (conditional on H1_01=8; 0 No, 1 Yes, PDF p.145). H1_14 is trying to start a business in the last six months; H1_15/15a record when unemployment began and are not the direct job-search item.",
        ),
        "d4_irregular_share": (
            "QUESTION_TEXT_VERIFIED_CONSTRUCT_PENDING",
            "H1_08 asks how often income is received; categories include daily, weekly, biweekly, monthly, 10 days, multi-month intervals, annually, end of season, piecework, and no fixed schedule (PDF pp.143-144). These are payment-frequency categories; an irregularity classification/share rule is not specified.",
        ),
        "d4_informal_share": (
            "CANDIDATE_CONCEPT_NOT_DIRECTLY_MEASURED",
            "H1_04 asks about a written employment agreement (0 No, 1 Yes, 998 Don't know; applies to selected H1_01 statuses, PDF p.143). H1_11 asks payment modes (PDF pp.144-145). Neither directly establishes informality/social protection; a definition and universe are needed.",
        ),
        "d4_unemployed_12m": (
            "CORRECTED_SOURCE_MAPPING_QUESTION_TEXT_VERIFIED",
            "Corrected to H1_05: asks whether the person was unemployed at any point in the past 12 months (0 No, 1 Yes, 998 Don't know); H1_05a records months if Yes (PDF p.143). H1_15/15a ask when unemployment began and H1_16 previous-job earnings, with different conditions.",
        ),
        "d4_no_worker": (
            "CURRENT_STATUS_ITEM_VERIFIED_WORKER_DEFINITION_PENDING",
            "H1_01 lists statuses 1-10 including waged, employer, self-employed, contributing/unpaid family worker, unemployed, retired (PDF p.139). H2_02 covers second-job participation last month (PDF p.146). Which statuses count as a worker and how missing employment records are treated require approval.",
        ),
        "d5_n_shocks_any": (
            "O1_CODES_VERIFIED_REFERENCE_PERIOD_AND_APPLICABILITY_PENDING",
            "O1_01_1-O1_01_20 use 1=Yes, severe impact; 2=Yes, moderate impact; 3=No impact (PDF pp.201-203). The table explicitly says past 12 months only for O1_01_20; the other O1 reference period is not stated there. Structural gates apply to O1_01_11-13, 16-17 via F1_00a=1; _14 via G1_00a=1; _15 via G2_00=1; and _18 via F1_00a=1 or I_01=1. Raw only per DEC-23; no count or recode.",
        ),
        "d5_n_shocks_severe": (
            "O1_CODES_VERIFIED_AGGREGATION_NOT_APPROVED",
            "O1 severity responses are 1=severe, 2=moderate, 3=no impact (PDF pp.201-203). Counting severe shocks is an unapproved derivation; period/applicability must be resolved. Raw only per DEC-23.",
        ),
        "d5_severity": (
            "O1_CODES_VERIFIED_SEVERITY_AGGREGATION_NOT_APPROVED",
            "O1 response codes distinguish severe, moderate and no impact (PDF pp.201-203); no combined severity score is specified. Raw only per DEC-23.",
        ),
        "d5_price_shock": (
            "O1_ITEM_WORDING_VERIFIED_REFERENCE_PERIOD_PENDING",
            "O1_01_1 higher food prices; _2 higher fuel prices; _5 higher electricity prices; _6 higher taxes. Each uses 1=severe, 2=moderate, 3=no impact (PDF pp.201-202). Table does not state reference period for these items. Raw only per DEC-23.",
        ),
        "d5_income_shock": (
            "O1_ITEM_WORDING_VERIFIED_REFERENCE_PERIOD_PENDING",
            "O1_01_3 financial shocks (examples include interest/exchange rates, price volatility, not getting a loan); _4 loss of employment/income/earnings of any household member. Codes 1=severe, 2=moderate, 3=no impact (PDF p.201). Table does not state reference period. Raw only per DEC-23.",
        ),
        "d5_health_shock": (
            "O1_ITEM_WORDING_VERIFIED_REFERENCE_PERIOD_PENDING",
            "O1_01_7 asks about death, serious illness or serious injury of family members; codes 1=severe, 2=moderate, 3=no impact (PDF p.201). Table does not state reference period. Raw only per DEC-23.",
        ),
        "d5_climate_shock": (
            "O1_ITEM_WORDING_AND_GATES_VERIFIED_REFERENCE_PERIOD_PENDING",
            "O1_01_9 floods/too much rain and _10 landslide; _11 unpredictable weather, _12 drought/severe heat and _13 crop pests/disease. Codes 1=severe, 2=moderate, 3=no impact (PDF pp.201-202). _11-_13 gated by F1_00a=1. Reference period not explicit in table. Raw only per DEC-23.",
        ),
        "d5_agri_shock": (
            "O1_ITEM_WORDING_AND_GATES_VERIFIED_REFERENCE_PERIOD_PENDING",
            "O1_01_11-_13, _16 lack of seeds/feed/fuel/fertilizer/other inputs, and _17 difficulty selling agricultural outputs/animal products are gated by F1_00a=1; _14 livestock disease by G1_00a=1; _15 poor fishing catches by G2_00=1; _18 hiring/workers/tools/equipment by F1_00a=1 or I_01=1 (PDF pp.202-203). Codes 1=severe, 2=moderate, 3=no impact. Raw only per DEC-23; F3 2023-24 and F7 2024-25 remain separate sources pending target season.",
        ),
        "d6_used": (
            "O2_RAW_ITEMS_REFERENCE_ONLY_PER_DEC24",
            "O2_01-O2_17 ask about coping with lack of food or money; the questionnaire states past 12 months for these items (PDF pp.203-207). Common responses are 1=Yes, 2=No because unnecessary, 3=No because already done before last 12 months and could not continue, 4=Not applicable, 5=Prefer not to say. O2_05/O2_06 are gated by F1_00a=1; O2_02/O2_04/O2_10a/O2_11a are conditional follow-up multi-selects. Keep raw only; no used/exhausted scoring.",
        ),
        "d6_exhausted": (
            "O2_RAW_ITEMS_REFERENCE_ONLY_PER_DEC24",
            "O2 category 3 records an action done before the last 12 months that could not continue; this differs from current-period Yes and should remain distinct. Items refer to the past 12 months, with item-specific gates and follow-ups (PDF pp.203-207). Raw only per DEC-24; no exhaustion flag.",
        ),
        "d6_stress_share": (
            "O2_RAW_ITEMS_COMPOSITE_NOT_APPROVED_PER_DEC24",
            "O2 items span asset sales/mortgages, production inputs, financial actions, health, food/non-food spending, migration, schooling and work (PDF pp.203-207). A stress-share denominator, item weights and treatment of codes 2-5 are not specified. Raw only per DEC-24; no composite.",
        ),
        "d7_has_debt": (
            "QUESTION_VERIFIED_CLEAN_CODE_DIRECTION_PENDING",
            "N1_00 asks whether the respondent/household owes money to any formal or informal institution, shop, friend or relative; questionnaire codes 1=No, 2=Yes (PDF p.197). Clean field n1_0 is 0/1 (3,900/2,947); recode direction cannot be established without transformation code. Do not recode from the name.",
        ),
        "d7_total_debt": (
            "AMOUNT_FIELDS_VERIFIED_COMPLETENESS_AND_AGGREGATION_PENDING",
            "N1_03 asks the loan amount from each institution as an integer (PDF p.197). Clean n1_03_1-n1_03_12 and n1_03_999 are source slots; 11 of 2,947 cleaned debt-positive households have all 13 amount fields blank and 12 have no positive amount total. Do not sum all-missing to zero; identify slot rules and units first.",
        ),
        "d7_n_debt_sources": (
            "SOURCE_CHECKBOX_FIELDS_VERIFIED_AGGREGATION_PENDING",
            "N1_01 asks which institutions the household owes money to (multiple response, PDF p.197); cleaned n1_01_1-n1_01_12 and n1_01_999 are binary columns. Preserve blanks and verify recode/skip behavior before counting.",
        ),
        "d7_hard_to_repay": (
            "QUESTION_VERIFIED_LOAN_SLOT_AGGREGATION_PENDING",
            "N1_06 asks difficulty repaying debt from each institution; codes 1=very difficult, 2=somewhat difficult, 3=not too difficult, 4=easily repayable, 5=don't know/don't want to say (PDF p.198). Cleaned values are slot-specific n1_06_*; do not collapse unknown or aggregate across loans without a rule.",
        ),
        "d7_has_bank_account": (
            "CORRECTED_SOURCE_MAPPING_QUESTION_VERIFIED_RECODE_PENDING",
            "Corrected source to N2_01/n2_01. N2_01 asks whether respondent or anyone in household has a bank account, questionnaire codes 1=No, 2=Yes (PDF p.198). N2_02 is where savings are deposited, not bank-account ownership; N3 is a separate women savings form and has no bank-account item. Clean n2_01 is 0/1 for all 6,847 households; recode direction is unverified.",
        ),
        "d7_able_to_save": (
            "CORRECTED_SOURCE_MAPPING_QUESTION_VERIFIED_FORM_RECONCILIATION_PENDING",
            "N2_05 (clean n2_05; men form) and N3_05 (clean n3_5; women form) ask whether respondent could save in the last 12 months, with questionnaire codes 1=No, 2=Yes (PDF pp.199). Clean fields are 0/1; N3 is present for 5,393 households and differs from N2_05 in 1,453. Keep forms distinct pending recode and respondent/form reconciliation.",
        ),
        "d7_n_income_sources": (
            "CANDIDATE_CONCEPT_NOT_DIRECTLY_DEFINED",
            "Proposed count spans employment, business and agriculture sources, but the questionnaire/source crosswalk and definition of an income source are not specified in the existing map. Defer construction pending explicit item list and overlap rule.",
        ),
        "d7_debt_income_ratio": (
            "DERIVED_MEASURE_PERIOD_AND_DENOMINATOR_PENDING",
            "Combines N1_03 integer loan amounts (PDF p.197) with H1_17 monthly household income (PDF p.146). Debt/loan amount reference period and H1_17 denominator/zero/special-code treatment are not aligned or established. Prepared ratio has 5,281 nonmissing, 36 above 10 and maximum 50,000; do not cap or reinterpret.",
        ),
    }
    source_corrections = {
        "d4_n_workers": "H1_01; questionnaire H2_02 (clean secondary file field name is h1_02; crosswalk pending)",
        "d3_any_disability": "b3_01; b3_02",
        "d3_chronic_share": "b3_01; b3_02",
        "d3_activity_limited_share": "b3_03",
        "d4_n_unemp_seeking": "h1_01; h1_13",
        "d4_irregular_share": "h1_08",
        "d4_informal_share": "h1_04; h1_11_1-h1_11_4; h1_11_999",
        "d4_unemployed_12m": "h1_05; h1_05a_1-h1_05a_12",
        "d4_no_worker": "h1_01; H2_02 (clean file field crosswalk pending)",
        "d7_has_bank_account": "n2_01 (corrected; n2_02 is savings deposit location; N3 has no bank-account item)",
        "d7_able_to_save": "n2_05 (men form); n3_5 (women form; questionnaire N3_05)",
    }
    researcher_choices = {
        "d1_poor_walls": "APPROVED_FOR_VALIDATION_AS_SEPARATE_CANDIDATE",
        "d1_poor_floor": "APPROVED_FOR_VALIDATION_AS_SEPARATE_CANDIDATE",
        "d1_poor_roof": "APPROVED_FOR_VALIDATION_AS_SEPARATE_CANDIDATE",
        "d1_bad_toilet": "APPROVED_FOR_VALIDATION_AS_SEPARATE_CANDIDATE; resolve 999 code-list discrepancy first",
        "d1_weak_tenure": "APPROVED_FOR_VALIDATION_AS_SEPARATE_CANDIDATE",
        "d1_housing_deprivation": "DEFERRED_BY_RESEARCHER; composite not approved",
        "d1_asset_share": "DEFERRED_BY_RESEARCHER; share/index not approved",
        "d1_income_month": "APPROVED_FOR_LATER_RECONSTRUCTION_AS_RAW_CANDIDATE",
        "d1_income_pc": "DEFERRED_BY_RESEARCHER; derivative not approved",
        "d1_income_missing": "DEFERRED_BY_RESEARCHER; missingness derivative not approved",
        "d3_dep_ratio": "APPROVED_FOR_VALIDATION_ONLY; thresholds and formula pending",
        "d3_share_child": "APPROVED_FOR_VALIDATION_ONLY; age cutoffs and denominator pending",
        "d3_share_elderly": "APPROVED_FOR_VALIDATION_ONLY; age cutoffs and denominator pending",
        "d3_any_disability": "APPROVED_FOR_VALIDATION_ONLY_WITH_REVISED_LABEL; household aggregation/code crosswalk pending",
        "d3_chronic_share": "DEFERRED; chronic-only share is not directly identified by current mapping",
        "d3_activity_limited_share": "APPROVED_FOR_ITEM_REVIEW_ONLY; preserve B3_03 categories, do not calculate share",
        "d4_unemployed_12m": "APPROVED_AS_SEPARATE_VALIDATION_CANDIDATE; H1_05/H1_05a; no household aggregation",
        "d4_n_unemp_seeking": "APPROVED_AS_SEPARATE_VALIDATION_CANDIDATE; H1_01/H1_13; no household aggregation",
        "d4_irregular_share": "DEFERRED_AS_CONSTRUCT; retain H1_08 payment-frequency item as raw review reference",
        "d4_informal_share": "DEFERRED_AS_CONSTRUCT; retain H1_04/H1_11 items as raw review references",
        "d4_n_workers": "DEFERRED; retain person employment records pending person-vs-job and H2 crosswalk rules",
        "d4_no_worker": "DEFERRED; retain person employment records pending worker-status universe and missingness rules",
        "d5_n_shocks_any": "RAW_REFERENCE_ONLY; no derived shock indicator per DEC-23",
        "d5_n_shocks_severe": "RAW_REFERENCE_ONLY; no derived shock indicator per DEC-23",
        "d5_severity": "RAW_REFERENCE_ONLY; no derived shock indicator per DEC-23",
        "d5_price_shock": "RAW_REFERENCE_ONLY; no derived shock indicator per DEC-23",
        "d5_income_shock": "RAW_REFERENCE_ONLY; no derived shock indicator per DEC-23",
        "d5_health_shock": "RAW_REFERENCE_ONLY; no derived shock indicator per DEC-23",
        "d5_climate_shock": "RAW_REFERENCE_ONLY; no derived shock indicator per DEC-23",
        "d5_agri_shock": "RAW_REFERENCE_ONLY; no derived shock indicator per DEC-23",
        "d6_used": "RAW_REFERENCE_ONLY; no derived coping indicator per DEC-24",
        "d6_exhausted": "RAW_REFERENCE_ONLY; no derived coping indicator per DEC-24",
        "d6_stress_share": "RAW_REFERENCE_ONLY; no derived coping indicator per DEC-24",
        "d7_has_debt": "RAW_REFERENCE_ONLY per DEC-25; no recode from cleaned 0/1 until crosswalk verified",
        "d7_total_debt": "DEFERRED; no amount sum until all-blank/zero and source-slot rules are resolved",
        "d7_n_debt_sources": "RAW CHECKBOX ITEMS ONLY per DEC-25; no source count",
        "d7_hard_to_repay": "RAW REFERENCE ONLY per DEC-25; no category collapse or loan-slot aggregation",
        "d7_has_bank_account": "RAW REFERENCE ONLY; corrected to N2_01; no recode until crosswalk verified",
        "d7_able_to_save": "RAW REFERENCE ONLY per DEC-25; keep N2 and N3 forms separate",
        "d7_n_income_sources": "DEFERRED; concept and source universe not defined",
        "d7_debt_income_ratio": "DEFERRED; denominator, periods, code direction and zero handling unresolved",
    }
    review_names = {
        "d3_any_disability": "d3_any_member_chronic_illness_or_severe_disability",
        "d3_activity_limited_share": "d3_activity_interruption_category",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers + extra)
        writer.writeheader()
        for values in records:
            row = {headers[i]: values[i] if i < len(values) else "" for i in range(len(headers))}
            candidate = row.get("candidate_indicator", "")
            if not candidate:
                continue
            review_status, review_note = verified_d1.get(
                candidate,
                ("NOT_YET_ITEMWISE_VERIFIED", "Existing workbook text is provisional; verify each item wording, code, universe, period and source derivation against the questionnaire and data."),
            )
            if candidate in ("d1_poor_floor", "d1_poor_roof"):
                source_vars = row.get("candidate_source_variables", "")
                source_vars = source_vars.replace("c1_06", "c1_05") if candidate == "d1_poor_floor" else source_vars.replace("c1_05", "c1_06")
                row["candidate_source_variables"] = source_vars
            if candidate in source_corrections:
                row["candidate_source_variables"] = source_corrections[candidate]
            row.update({
                "questionnaire_review_status": review_status,
                "source_mapping_correction_or_note": review_note,
                "review_candidate_name": review_names.get(candidate, candidate),
                "implementation_status": "PENDING_NOT_IMPLEMENTED",
                "researcher_candidate_decision": researcher_choices.get(candidate, "OPEN: retain for validation / exclude / revise"),
                "review_gate": (
                    "Verify item wording, codes, universe, period, and source-to-feature derivation; "
                    "then decide candidate inclusion and overlap. Provisional domain only."
                ),
            })
            writer.writerow(row)
    print(f"Wrote {sum(bool(r and r[0]) for r in records)} candidate rows: {OUTPUT}")


if __name__ == "__main__":
    main()

