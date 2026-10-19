# Component 1 — Indicator Specification v0.1 and Decision Log

**Status:** APPROVED as proposed by the researcher on 2026-10-19, recorded by Claude on the researcher's instruction. Each approval is conditional on the Section 5 checks: if a check changes a rule, that row is reopened and the change logged.

**Purpose:** fix the inputs for the first end-to-end fuzzy–Bayesian prototype (Stages 2–5 of the work breakdown). Scenario modelling and human oversight are out of scope for this milestone.

**Boundary:** all outputs are research outputs. They are not eligibility determinations. `label_high_vuln` and the consumption proxy remain a separate descriptive sensitivity reference (existing decision DEC-13) and are never ground truth or a training target.

## 1. Scope decision

| ID | Decision | Rationale | Approval |
| --- | --- | --- | --- |
| S-01 | Version 0.1 covers four domains: housing (D1), economic capacity (D1/D4 income and assets), food insecurity (D2) and demographic dependency (D3 age). D3 health, D4 work, D5 shocks, D6 coping and D7 finance are deferred to a later version. | The deferred domains carry the hardest open issues (ISS-04 to ISS-12). Four domains are enough to demonstrate the full workflow. | ☑ |

## 2. Input decisions

Each row gives the proposed rule, the published anchor, what the data and questionnaire show, and the sensitivity run that tests the choice.

### D-01 Food insecurity score (ISS-03)

- **Proposed rule:** count of items answered 1 (Yes) across the eight FIES items of the form the household answered. Used as a continuous fuzzy input, not as bands. Items coded 3 (Don't know) or 4 (Refused) are treated as missing, never as No. Primary rule: a household score is computed only when all eight items are valid; otherwise the score is unknown.
- **Anchor:** FAO FIES (Ballard et al. 2013; Cafiero et al. 2018). The raw score is the sum of affirmed items (0 to 8); official prevalence uses Rasch calibration with global thresholds. Published raw-score bands differ between studies, so no band is adopted.
- **Verified:** questionnaire L1\_01 to L1\_08 and L2\_01 to L2\_08 use 1 Yes, 2 No, 3 Don't know, 4 Refused, with a 12-month reference period. Data: 23 L1 and 21 L2 households have a 3 or 4 on at least one item. L1 raw score is 0 for about 43% of households and 8 for about 3%.
- **Sensitivity:** (a) prorated score when one or two items are invalid; (b) Rasch-calibrated score following the FAO procedure.
- **Approval:** ☑

### D-02 FIES form comparability and respondent rule (ISS-03, ISS-20)

- **Proposed rule:** L1 (women) and L2 (men) are treated as one respondent-allocated instrument only after checking `hhtype` (1 male and female respondents, 2 same-gender, 3 one respondent) against the form answered. A form flag is kept in the dataset. The 15 households that answered both forms and the 3 that answered neither are flagged, with score unknown until a rule is approved.
- **Data:** 4,148 households answered only L1, 2,681 only L2. Item 6 (ran out of food) is endorsed by about 17% on L1 and 34% on L2, which suggests the forms may not behave identically.
- **Sensitivity:** test differential item functioning between forms; compare results with and without a form adjustment.
- **Approval:** ☑

### D-03 Housing materials: walls, floor, roof (ISS-01, ISS-19)

- **Proposed rule:** each item is a separate input, scored durable or non-durable using the DCS Census 2024 mapping already recorded in the crosswalk (exact mappings only). Approximate, unmatched and unresolved codes are not classified by analogy; they are treated as unknown evidence.
- **Anchor:** DCS Census of Population and Housing 2024 classification of permanent, semi-permanent and improvised units (as cited in the crosswalk); UN-Habitat durable-structure criterion for SDG 11.1.
- **Verified:** questionnaire code lists for C1\_04, C1\_05 and C1\_06 match the crosswalk labels. About 200 households (3%) have an unmatched or unresolved wall code.
- **Sensitivity:** compare exact-only mapping with an approximate mapping; report both coverage figures.
- **Approval:** ☑

### D-04 Sanitation (ISS-02)

- **Proposed rule:** WHO/UNICEF JMP ladder using C1\_08 (type) and C1\_10 (shared with other households: 1 No, 2 Yes). Improved and not shared is basic; improved and shared is limited; unimproved and open defecation are the most deprived. Code 999 is unknown pending the specified text.
- **Proposed mapping of C1\_08 (to be confirmed):** improved = 1, 2, 3, 5, 7, 9, 12; unimproved = 4, 6, 8, 10, 11, 13; open defecation = 14. Codes 5 and 10 are the author's reading and need confirmation.
- **Verified:** the printed code list stops at 14 with no Other option, while C1\_08\_other is triggered by 999. 22 households have 999.
- **Sensitivity:** treat shared facilities as basic instead of limited; reclassify codes 5 and 10.
- **Approval:** ☑

### D-05 Tenure security

- **Proposed rule:** ordinal input. Owned (codes 1 to 3) is secure; rent-free, gifted or employer-provided (5, 6) and rented (4) are intermediate; encroached (7) and temporarily living without ownership (8) are insecure; 999 is unknown.
- **Anchor:** UN-Habitat lists security of tenure as a housing deprivation criterion but this review did not retrieve a grading of categories. The grading above is a researcher judgement.
- **Data:** code 7 has 75 households, code 8 has 3, codes 5 and 6 together 928, code 4 has 134.
- **Sensitivity:** treat only codes 7 and 8 as insecure; exclude tenure from the fuzzy core and test its effect.
- **Approval:** ☑

### D-06 Crowding

- **Proposed rule:** persons per bedroom = unique roster members divided by C1\_02 (bedrooms). Fuzzy membership is a ramp with midpoint 3 and width of 1 person either side. A household reporting 0 bedrooms is flagged and its value is not computed until a rule is approved.
- **Anchor:** UN-Habitat SDG 11.1.1: no more than three persons per habitable room; a BRIGHT-based World Bank analysis for Sri Lanka uses more than three persons per room; bedroom-based studies also use three per bedroom.
- **Verified:** C1\_02 is the number of bedrooms. Because bedrooms are a subset of rooms, a 3-per-bedroom cutoff flags more households than the room-based standard.
- **Sensitivity:** shift the midpoint upward (for example to 4); vary ramp width; replace with floor area per person using the 8 bands of C1\_03.
- **Approval:** ☑

### D-07 Demographic dependency (ISS-13)

- **Proposed rule:** total dependency ratio = (members under 15 + members aged 65 and over) divided by members aged 15 to 64, using age in whole years from the roster. Households with no working-age member are top-coded to the maximum dependency level and flagged; they are not dropped. Youth and old-age components are retained for sensitivity.
- **Anchor:** DCS Census 2024 reports the 15 to 64 working-age group, 65 and over, and a total dependency ratio. The 2012 census used 15 to 59 and 60 and over.
- **Data:** with the 65 and over rule, 40.6% of households have an elder and 6.8% have no working-age member; with 60 and over, 54.4% and 10.1%. The two dependency rankings correlate 0.81. Household child and elderly shares correlate -0.32, so they are not redundant.
- **Sensitivity:** 60 and over definition; excluding no-worker households; youth and old-age ratios as separate inputs.
- **Approval:** ☑

### D-08 Household size

- **Proposed rule:** the validated roster member count is used as a denominator for crowding and dependency, not as a separate vulnerability input, to avoid double counting.
- **Data:** mean 4.07, median 4, range 1 to 13.
- **Approval:** ☑

### D-09 Household income (ISS-07, ISS-15)

- **Proposed rule:** use H1\_17 only where repeated person-level records agree (5,328 households, 77.8%). The other 1,519 households are unknown evidence and are not imputed. Repeated values are never summed. Fuzzy membership follows the Totally Fuzzy and Relative approach, which builds membership from the income distribution so no poverty line is needed.
- **Anchor:** Cerioli and Zani (1990); Cheli and Lemmi (1995); Betti, Cheli, Lemmi and Verma.
- **Limitation:** raw household income is not adjusted for household size. Per-capita income remains deferred (DEC-19) and is the main sensitivity run once reopened.
- **Approval:** ☑

### D-10 Assets (ISS-15, RDEC-D1-02)

- **Proposed rule:** item-specific asset ownership; a simple count of asset types owned is used as the provisional summary. No weights.
- **Status:** provisional. The asset-index literature has not yet been reviewed for this project.
- **Sensitivity:** weighted index (for example principal components) once the literature pass is done.
- **Approval:** ☑

## 3. Model design decisions

| ID | Decision | Anchor and rationale | Sensitivity | Approval |  |
| --- | --- | --- | --- | --- | --- |
| M-01 | Fuzzy layer: one sub-model per domain; memberships from standards (ramps) or the distribution (Totally Fuzzy and Relative); within-domain aggregation by equal-weight mean. | Betti et al.: membership functions and combination rules are the two added choices in fuzzy measurement, so both are documented and tested. | Perturb weights; compare mean with min/max style operators; vary ramp widths. | ☑ |  |
| M-02 | Bayesian Network: domain-level fuzzy outputs, discretised to low, medium and high, feed a vulnerability node. | Structure justified from domain knowledge. | Test alternative structures and discretisation boundaries. | ☑ |  |
| M-03 | Conditional tables built with the ranked nodes method (weighted mean, equal initial weights), not noisy-OR and not trained on `label_high_vuln`. | Noisy-OR is designed for binary nodes; ranked nodes suit ordinal nodes. With no suitable data, tables are commonly elicited from experts (Fenton et al.; Laitila and Virtanen 2022). | Vary weights; test missing evidence by leaving nodes unobserved. | ☑ |  |
| M-04 | Missing values stay missing, with explicit flags. No imputation in v0.1. | Preserves evidence of what was not observed; the Bayesian Network handles unobserved nodes. | Compare with a simple imputation as a robustness check. | ☑ |  |
| M-05 | Outputs are labelled research outputs, not eligibility decisions. | Existing project boundary. | Not applicable. | ☑ |  |

## 4. Deferred and not dropped

| Item | Reason | Issue |
| --- | --- | --- |
| D3 B3 health items | B3\_01 code and skip conflict; 854 roster members across 677 households lack B3 records | ISS-04, ISS-05 |
| D4 worker and employment constructs | H2\_02 mapping unresolved | ISS-06, ISS-14 |
| D7 debt total, debt-income ratio, N2/N3 savings | Current-balance meaning and respondent rules unresolved | ISS-08 to ISS-10 |
| Combined housing class | Only 30 of 6,847 households match one DCS combined class | ISS-01 |
| D5 shocks and D6 coping | Reference periods and response states unresolved; F3/F7 season choice open | ISS-11, ISS-12, ISS-16, ISS-17 |
| Cross-domain composite and weights | Wait for construct and overlap review | ISS-18 |

## 5. Checks to complete before approval

1. Compare `hhtype` with the FIES form answered (D-02).
2. Read the C1\_08\_other text for the 22 households coded 999 (D-04).
3. Confirm the mapping of C1\_08 codes 5 and 10 (D-04).
4. Count households reporting 0 bedrooms in C1\_02 (D-06).
5. Check the roster age fields, including months, against the questionnaire (D-07).
6. Obtain the Rasch calibration procedure for the FIES sensitivity run (D-01).
7. Review the asset-index literature (D-10).

## 6. Principle for any value not set by a standard

Where no published standard exists (tenure grading, rule base, network weights), the choice is logged as a researcher judgement, starts from an equal-weight or midpoint default, and is tested in sensitivity analysis rather than defended as correct.

## 7. References consulted

- Ballard, Kepple and Cafiero (2013). The Food Insecurity Experience Scale. FAO.
- Cafiero, Viviani and Nord (2018). Food security measurement in a global context. Measurement, 116.
- UN-Habitat. SDG indicator 11.1.1 metadata (slum household deprivations).
- WHO/UNICEF Joint Monitoring Programme. Sanitation service ladder and SDG 6.2.1 metadata.
- Department of Census and Statistics, Sri Lanka. Census of Population and Housing 2012 and 2024 releases.
- Cerioli and Zani (1990); Cheli and Lemmi (1995); Betti, Cheli, Lemmi and Verma. Fuzzy set approach to poverty measurement.
- Fenton, Neil and Caballero. Ranked nodes in Bayesian networks; Laitila and Virtanen (2022), International Journal of General Systems, 51(8).
