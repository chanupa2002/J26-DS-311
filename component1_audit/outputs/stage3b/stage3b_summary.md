# Stage 3b summary

Research output - not an eligibility determination

## Built

- Read-only checks for seven modules; additions table has 6,847 unique spine households.
- Outputs include raw O1 items, approved O1 mean severity, and limited B1–B3 additions; no model, overall vulnerability score, ranking, or imputation.
- Section 9 addendum is included in the manifest and governs v0.2 candidate indicator preparation.
- N1 and N2 indicators use the addendum mapping; n1_0 agrees with the source flags for all 6,847 households (see `checks/n1_0_by_any_source_flag.csv`).
- No label_high_vuln or pc_cons fields were read into the additions.

## Module coverage

| Module | Spine households with valid/nonblank response | Status |
|---|---:|---|
| N1 | 6,847 | nonblank coverage only; Codebook.zip unavailable |
| N2 | 6,847 | nonblank coverage only; Codebook.zip unavailable |
| B3 | 6,836 | value set verified from task-specified rules |
| O1 | 6,847 | value set verified from task-specified rules |
| O2 | 6,845 | nonblank coverage only; Codebook.zip unavailable |
| L3 | 3,328 | value set verified from task-specified rules |
| L5 | 6,847 | value set verified from task-specified rules |

## B3 b3_01 by b3_03

| b3_01 | b3_03 | Count |
|---|---|---:|
| 0 | 1 | 0 |
| 0 | 2 | 0 |
| 0 | 3 | 0 |
| 0 | 4 | 0 |
| 0 | 5 | 0 |
| 0 | 6 | 0 |
| 0 | 7 | 0 |
| 0 | [BLANK] | 19,405 |
| 1 | 1 | 2,810 |
| 1 | 2 | 1,500 |
| 1 | 3 | 659 |
| 1 | 4 | 769 |
| 1 | 5 | 143 |
| 1 | 6 | 989 |
| 1 | 7 | 696 |
| 1 | [BLANK] | 50 |

The skip conflict is pronounced: all 19,405 records with b3_01=0 have b3_03 blank; 50 records with b3_01=1 also have b3_03 blank.

## O1 item completeness and mean severity

- Households with all 20 valid O1 items: 26. Per-item counts/rates are in `checks/o1_item_rates.csv`.
- Mean severity is known for 6,847/6,847 households; valid-item count is carried per household in `n_o1_items_valid`.
- User assumption: all 20 O1 items refer to the past 12 months; only item 20 states that period explicitly in the reviewed questionnaire.
- Severity mapping: 1 severe=1, 2 moderate=0.5, 3 none=0; mean over valid answers; no valid answers remain unknown.

## Validation

- Spine and additions rows: 6847; unique keys: 6847.
- Household-level module joins used one-to-one validation; B3 member keys checked for uniqueness.
- share_chronic is null when no valid b3_01; where present it is constrained to [0,1].
- Household-level CSV outputs are ignored by the repository .gitignore rule for CSVs.

## Open questions

- Codebook.zip was not found at the project root or under the project; requested cleaned-module codebook source rows could not be checked. Counts therefore show observed values, with unverified sets labeled accordingly.
- N1 n1_0 and N2 n2_01 use the task-provided 1=yes/0=no mappings; Codebook.zip was unavailable to independently verify the source row. The older domain_review note marks N1 direction unverified; the explicit mapping in this task was used and should be confirmed against the cleaned codebook when available.
- B3 b3_01 by b3_03 is a descriptive skip-conflict check only. b3_03 and b3_04 are not used in derived columns.
- O1 period assumption: the researcher directed that all 20 items be treated as past-12-month reports; only O1_01_20 explicitly states this period in the reviewed questionnaire. The approved mean-severity calculation is documented in the Stage 3b summary.
- L3 task lists l3_01..09 and frequency items but does not identify frequency item numbers or skip conditions; no activity-based skip interpretation is made without codebook/questionnaire mapping.
- O2 code categories and same-coding lead-item scope require the cleaned Codebook.zip; checks show observed raw values/counts only, and no derived O2 column is created.
- Stage 3b implementation and tests are placed under outputs/stage3b to honor the prohibition on modifying pre-existing Stage 3/4 files; no prior pipeline/test file was changed.
