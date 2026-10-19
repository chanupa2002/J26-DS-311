# D2 food-security score lineage audit

## Conclusion

**Lineage classification: Not reproducible from available evidence.** The prepared `d2_fies_raw` is present in `Data/processed/hh_indicators.csv`, and the source item fields are present in `Data/bright_csv/mod_l1_food_security_w.csv`, `Data/bright_csv/mod_l2_food_security_m.csv`, and their cleaned counterparts. The delivered raw-export and cleaned core item fields match cell-for-cell after unique-key joins; this verifies item preservation through that step only. No available transformation script or authoritative scoring/combination specification reproduces `d2_fies_raw`.

A repository search of `component1_audit/scripts/`, `component1_audit/R/`, and the available pipeline code found references for candidate documentation and validation, but no derivation of `d2_fies_raw`. `Data/processed/variable_map.csv` calls it a raw FIES score 0–8 from L1/L2; the map is a provisional description, not a transformation specification. `component1_audit/outputs/pipeline_v0/fies_item_responses_pending.csv` preserves L1 and L2 separately and does not score them. The R scripts audit codes/outputs; they do not derive the prepared score. The RDS `Data/processed/bright_prepared.rds` is present but cannot establish lineage in this environment because no usable R transformation source is available (R runtime is not configured).

## Questionnaire facts and data checks

Questionnaire PDF pp.178–182: L1 is the women’s form and L2 the men’s form. Core items L1_01–08/L2_01–08 ask about household food-access experiences due to lack of money/resources over the previous 12 months. Codes are 1 Yes, 2 No, 3 Don’t know, 4 Refused. Items 06–08 have frequency and month follow-ups; the instrument contains some cross-form/cross-item references in follow-up skip text, so those gates require source-version clarification. Forms remain separate.

There are 6,847 master households and both forms contain 6,847/6,847 unique household keys; each key set matches the master and the item joins preserve all 6,847 rows. Export-to-clean checks for 16 core item fields passed exact cell equality.

Prepared `d2_fies_raw`: **39 missing** and **3 fractional** values. Fractional value counts: {0.5: 1, 1.5: 1, 2.5: 1}. L1/L2 answered flags sum to 4,163/2,696; these are form-level flags, not independent sampled households.

### Item response distributions

Counts are household-form records (denominator 6,847 per item); missing is a separate count.

### L1 core items

| Item | 1 | 2 | 3 | 4 | Missing |
| --- | --- | --- | --- | --- | --- |
| l1_01 | 1646 | 2516 | 0 | 0 | 2685 |
| l1_02 | 1958 | 2200 | 3 | 1 | 2685 |
| l1_03 | 2047 | 2111 | 2 | 2 | 2685 |
| l1_04 | 1125 | 3035 | 0 | 2 | 2685 |
| l1_05 | 1440 | 2719 | 0 | 3 | 2685 |
| l1_06 | 722 | 3437 | 1 | 2 | 2685 |
| l1_07 | 486 | 3668 | 2 | 7 | 2684 |
| l1_08 | 185 | 3972 | 2 | 3 | 2685 |
### L2 core items

| Item | 1 | 2 | 3 | 4 | Missing |
| --- | --- | --- | --- | --- | --- |
| l2_01 | 1030 | 1657 | 0 | 2 | 4158 |
| l2_02 | 1326 | 1361 | 3 | 0 | 4157 |
| l2_03 | 1399 | 1290 | 0 | 1 | 4157 |
| l2_04 | 777 | 1913 | 0 | 0 | 4157 |
| l2_05 | 974 | 1715 | 2 | 0 | 4156 |
| l2_06 | 916 | 1772 | 1 | 0 | 4158 |
| l2_07 | 417 | 2272 | 1 | 3 | 4154 |
| l2_08 | 117 | 2570 | 0 | 3 | 4157 |

## Fractional and missing-score diagnostics

The three fractional records were inspected only through aggregate patterns, without exporting identifiers. Pattern groups by prepared value, count of Yes responses in each form, and whether all eight core items are binary-complete:

| Prepared value | L1 Yes count | L2 Yes count | L1 complete binary | L2 complete binary | Records |
| --- | --- | --- | --- | --- | --- |
| 0.5 | 0 | 1 | True | True | 1 |
| 1.5 | 3 | 0 | True | True | 1 |
| 2.5 | 4 | 1 | True | True | 1 |

Fractional rows with both forms binary-complete: 3; equal to L1 Yes count: 0; equal to L2 Yes count: 0; equal to the mean of the two Yes counts: 3. These are diagnostic comparisons only, not an inferred derivation. Among the 39 prepared-score-missing records, L1/L2 answered flags are true for 23/21; all eight core items are blank for 16/18 records respectively. The score-missing group therefore cannot be assigned a single explanation from available evidence.

## Alternative approaches for review (none selected)

- **Keep form-specific raw items for description (existing approved boundary DEC-20).** This preserves respondent perspective, special codes and partial response. It does not yield one household score.
- **Select one respondent/form per household using a documented survey-design rule.** This avoids combining potentially distinct informants but requires evidence on respondent eligibility/selection and intended target population, which is not in the available files.
- **Combine form-level evidence using a pre-specified protocol.** This may use complementary reports but needs an approved combination rule, duplicate-report handling, missing/DK/refusal rules and a validated source denominator. No such specification was found.

Do not implement or recommend a conventional 0–8 sum, average, or imputation until an authoritative scoring/combination specification and respondent-universe decision are supplied. The bottom-quintile consumption proxy was not used as truth or as a feature.
