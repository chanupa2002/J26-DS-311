# D3–D4 source semantics audit

## D3 household needs

**Verified questionnaire facts:** B0_04_years asks integer age in years and B0_04_months asks integer age in months (PDF p.8). Preserve both fields separately. B3_01 asks if member suffers from chronic illness or severe disability; questionnaire codes 1 No/2 Yes (p.12). B3_02 is condition-type multi-select, with skip text “If B3_01 was 1,” which contradicts the code list. B3_03 asks interruption of usual activities due to condition in last year; category 7 says main activities interrupted completely more than 12 months ago (p.13).

B0 and B1 each have 27,875/27,875 unique `hhcode+pid` rows and exact key sets and age-field values. B3 has 27,021 unique member keys, all inside B0; 854 B0 members lack B3 records across 677 households. This is module coverage, not proof of skip status or illness absence. Age fields: years missing 0; months missing 27,671. The questionnaire gives separate units and no conversion/age thresholds.

Cleaned B3_01 response coverage and B3_02 linkage:

| Clean B3_01 value | Rows | B3_02 nonmissing rows |
| --- | --- | --- |
| 0 | 19405 | 0 |
| 1 | 7616 | 7616 |

Clean B3_01 is 0/1 while the questionnaire lists 1/2; no source transformation resolves direction. B3_02 nonmissing alignment is evidence about the exported pattern only and cannot authorize a recode because it conflicts with skip text. B3_03 applicability likewise remains uncertain until that conflict and the age>5 gate are clarified. No child/older cutoffs, dependency formula, chronic-only score, or household aggregation was applied. Possible alternatives for review: age-band shares with a chosen threshold/denominator; dependent-to-working-age ratio with specified bands; or raw age references only. For health: member-level categories, any-member representation, or share among a confirmed eligible roster; these differ in household-size sensitivity and missingness assumptions.

## D4 livelihood and income

Questionnaire pp.139–146: H1_01 is current employment status (1–10); H1_05 asks whether unemployed at any point in the past 12 months and H1_05a records months if Yes (p.143); H1_13 asks active job search in the last four weeks, only if H1_01=8 (p.145). H1_08 records payment frequency, not job regularity by itself; H1_04 written agreement and H1_11 payment modes do not alone define informality. H2_02 asks whether a second paid/unpaid job or at least one hour of other activity occurred last month, including household farm/business help (p.146).

H1/H2 have 27,883/27,883 unique `hhcode+hhmember` keys; their key sets match. H1 keys outside B0 roster: 8. H2_02 is not named in the cleaned H2 file; the candidate mapping to `h1_02` remains unresolved despite similar placement in the export. Questionnaire wording does not prove that field mapping.

H1_17 asks total monthly household income in LKR (p.146), but is repeated on person-level H1 records. Reproduced household diagnostics across 6,847 households: 6,663 have multiple H1 records; 5,328 have exactly one distinct nonmissing H1_17 value; 0 have conflicting nonmissing values; 1,519 have no nonmissing H1_17. **Do not sum repeated H1_17.** This corrects the previous diagnostic's “no nonmissing” count, which erroneously counted only households appearing in a nonmissing group. No H1_17 special-code semantics or prepared-income formula was recovered.

Conditional checks: H1_13 has 954 nonmissing values, of which 0 occur outside status 8. Among 2,592 H1_05 Yes rows, 0 have all month flags missing and 0 have at least one missing month flag. Current candidate representations (any eligible member, count, proportion among eligible respondents, or person-level reference only) remain alternatives. Each changes household-size sensitivity and missing-data requirements. No employment aggregate was created.
