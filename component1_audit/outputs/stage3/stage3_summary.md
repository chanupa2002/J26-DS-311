# Stage 3 modelling inputs v0.1 — engineering audit

## Scope and outputs

Built a household-level table with 6,847 rows and 75 columns, preserving the 6,847-row v0.1 household core. The work is data engineering only. No model, vulnerability ranking/score, imputation, or eligibility decision was created. `pc_cons` and `label_high_vuln` are excluded. FIES item responses remain in a separate raw-response extract.

Outputs include `modelling_inputs_v0_1.csv`, `fies_item_responses_pending.csv`, three lookups, a column dictionary, missingness report, Part A checks, and a SHA-256 manifest.

The cleaned-file rule confirmation table is in `codebook_rule_confirmation.md`; the codebook crosscheck and decision log are both hashed in the manifest.

## Part A checks and decision-log comparison

- FIES form coverage: {'L1 only': 4148, 'L2 only': 2681, 'both': 15, 'neither': 3} households (master denominator 6,847).
- Code 999 counts: {'c1_01': 1, 'c1_04': 1, 'c1_05': 0, 'c1_06': 0, 'c1_07': 2, 'c1_08': 22}.
- FIES complete 8-item forms: {'L1': 4140, 'L2': 2675}; no-form/both-form cases are retained separately.
- Households with no observed working-age member: 464 for ages 15–64 and 690 for ages 15–59.
- Asset register: 18 explicitly selected items; d_07/d_09/d_11 and all a/b/c follow-ups excluded. For d_12-d_16 only, codebook rule 0=No, 1=Yes (owned=1) is applied. Other direct items retain their registered rules.
- Roster flag counterfactuals (flag=0 assumed failing, not applied): b0_01a has 751 failing roster rows; size would change in 600 households and dependency ratio in 422. b0_01b has 1608 failing roster rows; size would change in 1283 households and dependency ratio in 850.
- The A2 code-999 count matches the prior 22-household register figure; all-code C1_08 Other text frequency totals match the previously reported 24. Raw free text is suppressed.
- D-04b codebook correction applied to C1_10 only: 0=not shared; 1=shared; other/missing=unknown. The questionnaire convention remains 1=No/2=Yes but is overridden for this cleaned file; C1_08 type classes are unchanged.
- D-03a material lookup is applied exactly; all unlisted source codes remain unknown.

These checks do not validate or approve any indicator for a model. Decision references and item-level details are in `checks/decision_log_comparison.csv` and the check tables.

## Open questions

See `open_questions.md`; the crosscheck agrees with the applied C1_10, d_12-d_16, 18-item asset, FIES and `hh_type` rules. The decision log's stale `hhtype` follow-up is recorded; the crosscheck's `hh_type` name is used. Roster flag inclusion remains undecided, so flag counterfactuals are reported but not applied. Other questions are suppressed C1_08 Other text; FIES denominator for both/no form; sensitivity-ratio definitions; and proposed C1_08 codes 5 and 10.
