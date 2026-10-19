# Validation methods and tests

## Inputs inspected

- Candidate inventory: `component1_audit/outputs/consolidated_measurement_review/candidate_indicator_register.csv` and source `component1_audit/outputs/indicator_registry_review.csv` (43 candidate IDs).
- Existing decisions: `component1_audit/outputs/research_decisions_status.csv`; no decision was altered.
- D1: `component1_audit/outputs/d1_housing_material_validation/housing_classification_audit.md`, `housing_material_crosswalk.csv`, `housing_combination_feasibility.csv`, and `housing_material_frequency_report.csv`; builder `component1_audit/scripts/build_housing_material_validation.py`.
- D2-D7: `component1_audit/outputs/d2_d7_resolution/d2_lineage_report.md`, `d3_d4_source_semantics_report.md`, `d5_d6_period_applicability_report.md`, `d7_financial_semantics_report.md`, `d2_d7_resolution_summary.md`; builder `component1_audit/scripts/build_d2_d7_resolution.py`, regression file `component1_audit/scripts/test_d2_d7_resolution.py`.
- Cross-domain and prior issues: `component1_audit/outputs/d2_d7_validation/cross_domain_overlap_register.csv`, `d2_d7_validation_report.md`, and `component1_audit/outputs/consolidated_measurement_review/cross_domain_overlap_register.csv`, `unresolved_measurement_issues.csv`, `researcher_decisions_required.md`.
- Questionnaire: `Data/BRIGHT_questionnaire_English.pdf`; DCS reference used by inherited D1 audit: Census of Population and Housing 2024 Final Report, section 11.5, printed p.189.
- Prepared values: `Data/processed/hh_indicators.csv`, read only to confirm prepared columns and count each column's missing values over its full row count (6,847). These are full-master denominators, not eligible-case denominators and do not distinguish structural skip from nonresponse.

## Assessment method

The original stable candidate IDs and order were retained, partitioned D1 through D7, and assessed using identical columns. Evidence and readiness classifications are separate from approval status. Every prepared-column missingness count uses the full 6,847-row prepared file denominator; observed nonmissing values may include special/unresolved codes. Item eligibility denominators are reported only where inherited diagnostics establish them. Unknowns are explicitly stated; no new recode, imputation, household aggregation, score, model feature, association test or feature selection was computed.

## Checks executed in this run

1. Candidate inventory: 43 source rows, 43 unique IDs; consolidated register has 43 unique IDs; no duplicates or omissions. All 43 candidate names exist as columns in `hh_indicators.csv`.
2. Per-candidate prepared missingness count: one aggregate count per variable with explicit full-file denominator; this does not imply an eligible denominator or valid construct.
3. D1 inherited feasibility table aggregate was summed: 30 exact classifiable cases and total frequency 6,847. Underlying material mapping was inherited, not rerun.
4. Ran `python -m unittest component1_audit.scripts.test_d2_d7_resolution -v`: three tests passed (D2 missing/fractional values, D3 B3 coverage/D4 income missingness, D7 status/amount/zero diagnostics). These tests print no records or identifiers.
5. D7 historical 20-vs-31 test: inspected `component1_audit/scripts/build_d2_d7_validation.py` and its report. The earlier validator calculates raw amount blank/explicit-zero counts but does not calculate prepared debt-total zeros. The latest resolution diagnostic is key-aligned and reports 31; preserve 20 as unreconciled, not resolved.
6. Output schema check: seven domain files share the combined file schema; values in evidence/construct/readiness classifications are checked against the requested vocabularies; all reported missing counts include `/full denominator`; no IDs or raw responses are written.
7. Preservation check: SHA-256 hashes of inherited candidate registry, decision register, prepared `hh_indicators.csv`, D1 feasibility output, D2-D7 reports, prior validation report and `.gitignore` were captured before/after generation and remained unchanged.

## Checks not performed / limits

The D1 raw source mapping was not recomputed, D5/D6 raw module counts were not rerun, no questionnaire PDF was re-extracted in this run, and no correlation, predictive validity, fairness, reliability, causal, or model analysis was performed. D2/D7 lineage searches and questionnaire interpretation are inherited from the cited audits. No valid eligible denominator is inferred from a full-file missingness count.

## CSV data dictionary

- `D1_candidate_assessment.csv` through `D7_candidate_assessment.csv`: same fields as the combined register, domain-filtered and in original candidate order.
- `all_43_candidate_assessment.csv`: one record per candidate. `prepared_missing_count_full_master_denominator` and `prepared_nonmissing_count_full_master_denominator` show count/full prepared row denominator; these are not eligible-case percentages.
- `cross_domain_redundancy_review.csv`: eight documented relationships, source concepts/periods, overlap type, risk, alternatives and evidence needed; no empirical associations were tested.
- `evidence_gaps_and_blockers.csv`: one record per domain-level evidence issue, checks actually run/inherited, alternatives and consequence if unresolved.

No final indicator is approved by this assessment. Existing decisions are preserved verbatim in the candidate register; validation approval is not model-inclusion approval.
