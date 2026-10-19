# D7 debt and financial semantics audit

## Verified questionnaire-to-variable crosswalk

| Questionnaire item | Clean/export fields | What the item asks | Reference period / response semantics | Remaining limitation |
|---|---|---|---|---|
| N1_00 | `n1_0` in `mod_n1_debt.csv` | Whether respondent or household owes money to formal/informal institution, shop, friend or relative | Select one: 1 No, 2 Yes (questionnaire p.197) | Export and clean use 0/1, identical in delivered raw export and clean; transformation from questionnaire codes and direction are not documented. Do not infer from variable name. |
| N1_01 | `n1_01_1`–`n1_01_12`, `n1_01_999` | Institutions/sources owed money to | Multiple response; questionnaire lists 13 Other, while follow-up uses 999 (p.197) | Source and binary recode/skip behavior need source-form crosswalk. |
| N1_03 | `n1_03_1`–`n1_03_12`, `n1_03_999` | Amount of the loan taken from institution | Integer, no explicit time/balance reference stated (p.197) | Loan amount taken is not necessarily current outstanding debt; no amount totals calculated. |
| N1_05a/b | slot-specific `n1_05a_*`, `n1_05b_*` | Current interest rate and reference period | Percentage; period asked unless rate is 0, 998 or 997 (p.198) | Special values and units need item-level lineage; no conversion performed. |
| N1_06 | `n1_06_*` | Difficulty repaying debt from institution | 1 very difficult, 2 somewhat difficult, 3 not too difficult, 4 easily repayable, 5 don’t know/don’t want to say (p.198) | Slot-specific item; no across-source aggregate. |
| N2_01 | `n2_01` | Whether respondent or anyone in household has a bank account | 1 No, 2 Yes (p.198) | Household-level access question; clean/export values preserved, no direction recode. |
| N2_02 | `n2_02` plus response flags | Where household usually deposits savings | Multiple response, includes don’t know/cannot recall and Other (p.198) | Not the bank-account ownership item; Other code discrepancy in questionnaire/follow-up needs review. |
| N2_05 | `n2_05` | Whether “you” could save any money in last 12 months; N2 is men’s form | 1 No, 2 Yes (p.199) | Individual respondent perspective; export/clean 0/1 direction not documented. |
| N2_06 | `n2_06` | Approximate percent of personal total income saved | 10 ordered percentage bands; gate printed if N2_05=1 (p.199) | Gate conflicts with displayed 1=No code; band is ordinal interval, not continuous percent. |
| N3_05/06 | `n3_5`, `n3_6` | Same saving questions on women’s form | Last 12 months; 1 No, 2 Yes; bands for percent (pp.199–200) | Clean names omit 0; separate women respondent/form, not directly interchangeable with N2. |

Raw export and cleaned values for `n1_0`, `n2_05`, and `n3_5` are identical after one-to-one household-key joins. This proves only that the clean files preserve the delivered export values; it does **not** establish how numeric 0/1 maps to questionnaire 1/2. No available script specifies that recode or the prepared debt derivation. `hh_indicators.csv` contains prepared `d7_total_debt`, `d7_n_debt_sources`, `d7_hard_to_repay`, and `d7_debt_income_ratio`; available code and manifest do not reproduce their formulas.

## Reproduced diagnostics and denominators

N1 cleaned/export has 6,847 unique household records. Clean `n1_0` values are 0 for 3,900 and 1 for 2,947; these remain unlabeled response codes here. Prior review interpreted value 1 as provisional debt-positive; no questionnaire direction was inferred in this audit.

Among the 2,947 records with `n1_0=1`, of 13 institution amount slots, 11 records have all amount fields blank, 12 have no positive amount slot, 2 have at least one explicit zero slot, and 2,935 have a positive slot. These categories can overlap. No row-level records or amount totals are emitted.

| Prepared total vs. raw slot evidence, among `n1_0=1` | Count |
|---|---:|
| Prepared `d7_total_debt` equals zero | 31 |
| Prepared total missing | 0 |
| Prepared zero AND all raw slots blank | 11 |
| Prepared zero AND no raw slot positive | 12 |

The prior review's 20 prepared zeros are not reproduced in this key-aligned recheck: 31 prepared debt totals are zero among 2947 clean status-1 records. Of these, 11 also have all amount slots blank and 12 have no positive slot. These groups use different predicates and are not expected to match. A prepared zero cannot be treated as verified current debt balance. N1_03 refers to amount taken, not necessarily outstanding debt.

N2 has 6,847 household rows, N3 has 6,847; nonmissing cleaned responses are 6,847/5,393. There are 5,393 paired nonmissing records, with 1,453 disagreements. Cross-tab of paired cleaned values (not recoded):

| N2_05 cleaned value | N3_5 cleaned value | Paired records |
| --- | --- | --- |
| 0 | 0.0 | 3580 |
| 0 | 1.0 | 763 |
| 1 | 0.0 | 690 |
| 1 | 1.0 | 360 |

Question wording is similar and both ask whether “you” saved during the last 12 months, but N2 is the men’s form and N3 the women’s form. The respondent/sex universe differs; this is not evidence that one response is erroneous or that both should be combined. N2_06/N3_06 reference personal income; do not treat them as household savings amounts.

## Candidate choices for researcher review

- Keep N1 status, institution selections, amount slots and repayment categories as separate raw references (existing scope boundary DEC-25).
- If financial burden is retained, first determine whether a source field for current outstanding balance exists; if none, a historical amount-taken measure is a different construct and needs an explicit name and purpose.
- Keep N2/N3 separate, choose a respondent rule, or report them as form-specific context; each choice changes the represented person/universe.
- Use N2_01 as bank-account access only after confirming its 0/1 direction. Do not substitute N2_02 deposit location.

Debt totals, source counts, repayment aggregates, debt-to-income ratios and combined savings measures remain unimplemented.
