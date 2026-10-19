# D2–D7 coordinated research resolution audit

## Status

This is an evidence and decision-options audit only. It does not implement or approve model indicators. Previously recorded approvals (DEC-20 through DEC-25) authorize limited raw validation/preservation; final inclusion, recoding, aggregation and modeling remain unapproved. No bottom-quintile consumption proxy was used as ground truth or core feature.

## Reproduced findings

- **D2:** 39 missing and 3 fractional `d2_fies_raw` values are reproduced. Core L1/L2 item fields match source export to cleaned files exactly after validated one-to-one keys. No score derivation is present; lineage is **not reproducible from available evidence**. Form separation remains the approved boundary.
- **D7:** `n1_0=1` occurs 2,947 times; all 13 amount slots are blank for 11, no positive slot occurs for 12, and the prepared total is zero for 31. N2/N3 have 5,393 paired nonmissing records and 1,453 differences. Counts have different predicates and are not expected to match. Field values are preserved export-to-clean; questionnaire recode direction and prepared total logic remain unknown.
- **D3:** B0/B1 keys and age data match; B3 contains 27,021 members, all within B0, with 854 roster members lacking a B3 record. B3 code/skip conflict persists.
- **D4:** H1/H2 person keys match exactly. H1_17 values are never summed. Rechecked consistency shows 5,328 households with one nonmissing value, 0 conflicting, and 1,519 with none. The prior audit’s “no nonmissing” diagnostic was incorrect: it counted only households present in the nonmissing group.
- **D5/D6:** item code and period findings are retained; gates were rechecked against cleaned F1/G1/G2/I/O1/O2 sources. Explicit no impact, no-need, N/A, refusal/non-disclosure, structural skip, gate missing and response blank are not collapsed. F3/F7 remain separate.

## Source lineage established

Available input files are listed in the four domain reports. Source-export-to-clean comparisons establish preservation for selected D2 item fields and selected D7 code fields only. They do not recover questionnaire platform recodes. No derivation source was found for `d2_fies_raw` or prepared D7 totals/ratios. `Data/processed/bright_prepared.rds` exists, but without the original R derivation/runtime it does not establish transformation lineage. `component1_audit/pipeline/prepare_household_core.py` keeps D2 forms separate and does not calculate scores; it is not the original preparation script.

## Decisions blocking indicator approval/modeling

1. D2 respondent/form selection, score rule, and DK/refusal/partial-response handling.
2. D7 questionnaire-to-export code direction, outstanding-balance construct, amount slot selection, and N2/N3 respondent rule.
3. D3 B3_01 skip/code discrepancy and B3_03 period/category issue; age bands and household denominators.
4. D4 H2_02 mapping, H1_17 missing/special/repetition handling, and person-to-household representation.
5. D5 common period/applicability and season target; D6 category/skip treatment.
6. Cross-domain construct boundaries and later redundancy/sensitivity treatment.

## Small decision set for researcher review

- Confirm whether D2 remains form-separated raw-only or whether a validated respondent/scoring protocol should be obtained before further work.
- For D7, decide whether to defer debt burden until outstanding balance is evidenced, and whether N2/N3 should remain separate form-specific references.
- Confirm that D3 should remain member-level until B3 instrument/export discrepancy and age-band rules are resolved.
- Decide whether D4 unemployment items are only person-level references or should later be represented at household level; approve a mapping investigation for H2_02.
- Request instrument/export clarification for O1 period and B3/N1/N2/N3 source semantics.

The full option tradeoffs and approval flags are in `research_decisions_pending.csv`. Statuses are unresolved, evidence-gathering or ready for review; no new substantive decision is marked approved.
