# Candidate indicator validation summary

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
