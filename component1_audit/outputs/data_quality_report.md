# BRIGHT Component 1 — data-quality and implementation audit

Audit date: 2026-10-18  
Purpose: research decision support for human review; not an automated Aswesuma or Samurdhi eligibility system.

## Source files found

- 65 cleaned CSV files in `C:\data\processed\clean`.
- Prepared outputs in `C:\data\processed`: `hh_indicators.csv` (6847 rows × 44 columns), `hh_context.csv` (6847 × 18), `cleaning_log.csv`, `preprocessing_validation_report.csv`, `missingness_recomputed.csv`, `outlier_report.csv`, `sentinel_log.csv`, and `variable_map.csv`.
- Questionnaire: `Data/BRIGHT_questionnaire_English.pdf` (243 pages). It provides question text and item codes for the domains used below. No separate codebook was found.
- No original preprocessing or mechanical validation R script was found in the workspace or the supplied processed-data directory. Existing CSV/RDS reports were inspected, but they do not permit exact transformation replay.

## Inventory and grain

The full per-file inventory, including dimensions, exact column names, observed data types, nonmissing-key status, duplicate-key rows, and variable-level missingness, is in `module_inventory.csv` and the workbook. In this cleaned export, the household ID file and most single-row modules are household-shaped; B0–B3 are person/member records; H1/H2 are employment/person records; E and selected F modules are plot/crop-season records; J1 and J2 are food-item records; K is expenditure-item-by-period; R support files use program/support identifiers; and S2/S3 are person/measurement records. A one-row household export is not proof every item is household-level; respondent and applicability rules still require instrument crosswalks.

## Current mechanical checks

- Prepared household indicators and context each have 6,847 rows. Household keys are unique/nonmissing in both: True / True. Key-set difference: 0.
- The indicator table contains 43 D1–D7 candidates plus `hhcode`. Previous validation says output IDs match, no infinite/NaN indicators, and weighted proxy prevalence is 0.2001.
- IFPRI describes 6,850 interviewed households (https://www.ifpri.org/project/bright-sri-lanka/); the 6,847-row analytic set must be reconciled to sample disposition before claiming full sample coverage.
- Existing `cleaning_log.csv` reports row/key checks for modules. Notable transformations include padded rows removed from B2/B3; J1/K stray rows removed; a duplicate F3 underscore export recorded as identical and skipped; and sentinel recoding in several modules. These checks do not establish semantic correctness.

## Findings requiring review

1. **Special values:** 997/998/999 do not have global meanings. The questionnaire uses 999 for “Other” on many questions and has item-specific “Don’t know,” “Refused,” and “Prefer not to say.” Review every recode against the question, not just numeric value. The sentinel log lists counts/recode status but cannot replace item documentation.
2. **Employment income:** questionnaire H1_17 asks total monthly household income while H1 is represented on person rows. There are 6,663 households with multiple H1 person records, and 5,328 have the same nonmissing H1_17 repeated. Summing these rows would multiply income. The existing outlier report flags H1_17 with maximum 27,000,000 and four records above ten times p99. Treat those as review cases; do not cap or delete them.
3. **Food/non-food expenditure:** J1 asks past-7-day item consumption/value; among 255,605 item rows coded consumed, 65,573 have missing `j1_08`; another 641,230 rows are coded not consumed and have missing value. K has 36,286 missing amounts in 472,443 item-period rows and 257,691 recorded zero amounts. Validate each period conversion and missing-to-zero decision. Missing data and “no expenditure” are not interchangeable.
4. **FIES:** the prepared score contains three fractional values (0.5, 1.5, and 2.5, one household each) and 39 missing value(s). L1/L2 contain eight experience items with separate DK/refusal responses and follow-ups. The partial-response, respondent-merging, and scoring rule remain unapproved.
5. **Roster:** B0/B1 contain 27,875 person rows each and unique `hhcode+pid`; no ages are missing in these exports, but one age is 101. B2/B3 are partial/question-specific records; their smaller row counts follow removal of padded rows in the cleaning log and do not by themselves prove person loss.
6. **Debt/savings:** N1 is a one-row household export with multiple creditor-source amount slots, not a loan-row table. Eleven debt-positive households have every amount blank and 20 debt-positive households have a zero aggregate. The prepared total records all 6,847 as nonmissing. Verify status/source selection before treating these as zero. Debt-income ratios are nonmissing for 5,281 households, with 36 values above 10 and a maximum of 50,000; no capping was applied. N2 and N3 are separate savings instruments; questionnaire No/Yes codes are 1/2, while cleaned N2_05/N3_5 values are 0/1, so the recode needs to be traced. N2_06/N3_06 are percent bands, not continuous measured savings.
7. **Structural skips:** O1 agriculture/livestock/fishing/business shocks are conditional on participation. Preserve applicability. Maha versions include 2023–24 F3 and 2024–25 F7; these are different reference seasons, not interchangeable duplicates. The workspace mirror also has a duplicate underscore-named F3 long export that is absent from the configured C:\data cleaned directory.
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
