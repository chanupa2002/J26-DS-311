# Reproducibility and scope

## Inherited evidence reviewed (not rerun as part of consolidation)

- D1 housing audit: `component1_audit/outputs/d1_housing_material_validation/housing_classification_audit.md`, `housing_combination_feasibility.csv`, `housing_material_crosswalk.csv`, `housing_material_frequency_report.csv`; builder `component1_audit/scripts/build_housing_material_validation.py`. The reported 30/6,847 exact matches are inherited from that audited crosswalk; this consolidation reads its aggregate feasibility CSV, not the source microdata or Census PDF.
- Existing candidate/preprocessing registry: `component1_audit/outputs/indicator_registry_review.csv` (43 candidates), `implementation_status.csv`, `research_decisions_status.csv`, and `updated_issue_register.csv`.
- D1-D7 validation: `component1_audit/outputs/d2_d7_validation/d2_d7_validation_report.md`, `cross_domain_overlap_register.csv`, and builder `component1_audit/scripts/build_d2_d7_validation.py`. The earlier report's debt-zero value 20 is retained as a historical claim. Its builder diagnostics only computed N1 raw all-blank and explicit-zero amount slots; they did not compute prepared zero totals.
- D2-D7 resolution: four domain reports and `research_decisions_pending.csv` in `component1_audit/outputs/d2_d7_resolution/`; builder `component1_audit/scripts/build_d2_d7_resolution.py`; tests `component1_audit/scripts/test_d2_d7_resolution.py`.
- Questionnaire: `Data/BRIGHT_questionnaire_English.pdf`; page/item references appear in the candidate and issue registers. DCS reference cited by inherited D1 audit: Department of Census and Statistics, Census of Population and Housing 2024 Final Report, section 11.5, printed p.189.

## Checks executed for this consolidation

- Read the inherited 43-row candidate registry and decision register; wrote a consolidated 43-row register without touching source registers.
- Read the inherited D1 aggregate combination table and summed the exact-match status: 30 classifiable households; total of all listed triplet frequencies is 6,847. The underlying D1 material-code mapping was not rerun here.
- Reviewed the earlier D7 validator implementation: its reported 20 prepared zeros were cited in its prose but not calculated by that script. The latest resolution builder joins N1 and prepared totals on unique `hhcode`, validates one-to-one cardinality, and reproduced 31. Therefore the earlier 20 cannot be reconciled from existing audited predicates; denominator/predicate are absent.
- No source microdata, questionnaire records, free text, identifiers, prepared variables or pipeline artifacts were changed. No new diagnostic aggregation was run for this consolidation.

## Output data dictionary

- `candidate_indicator_register.csv`: one row per inherited candidate; includes source/module/page fields, proposed prepared column, source/unit/universe, lineage and missingness limits, overlap, alternatives, evidence needed, and inherited scope decision. The prepared-variable column exists in `Data/processed/hh_indicators.csv`; existence does not establish derivation or approval.
- `cross_domain_overlap_register.csv`: one row per documented pair; columns describe concepts/questions/periods, relationship evidence limits, double-counting or information-loss risks, options, and remaining evidence.
- `unresolved_measurement_issues.csv`: one row per issue; records urgency group, evidence/denominator, alternatives, pros/cons, and deferral consequence.
- `researcher_decisions_required.md`: decisions grouped by the four requested urgency classes, with alternatives and tradeoffs.
- `consolidated_measurement_review.md`: summary and consolidated findings.
- `reproducibility_and_scope.md`: provenance, inherited versus executed checks, and CSV dictionaries.

No new substantive decision is marked approved. Validation-scope approvals in prior records do not authorize final indicator inclusion.
