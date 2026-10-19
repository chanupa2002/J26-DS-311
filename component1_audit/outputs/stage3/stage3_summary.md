# Stage 3 modelling inputs v0.1 — engineering audit

## Scope and outputs

Built a household-level table with 6,847 rows and 75 columns, preserving the 6,847-row v0.1 household core. The work is data engineering only. No model, vulnerability ranking/score, imputation, or eligibility decision was created. `pc_cons` and `label_high_vuln` are excluded. FIES item responses remain in a separate raw-response extract.

Outputs include `modelling_inputs_v0_1.csv`, `fies_item_responses_pending.csv`, three lookups, a column dictionary, missingness report, Part A checks, and a SHA-256 manifest.

## Part A checks and decision-log comparison

- FIES form coverage: {'L1 only': 4148, 'L2 only': 2681, 'both': 15, 'neither': 3} households (master denominator 6,847).
- Code 999 counts: {'c1_01': 1, 'c1_04': 1, 'c1_05': 0, 'c1_06': 0, 'c1_07': 2, 'c1_08': 22}.
- FIES complete 8-item forms: {'L1': 4140, 'L2': 2675}; no-form/both-form cases are retained separately.
- Households with no observed working-age member: 464 for ages 15–64 and 690 for ages 15–59.
- Asset register: 13 count items pass their registered value rule; 5 binary items mismatch the registered 1=No/2=Yes coding (0/1 observed). Their ownership flags remain blank.
- The A2 code-999 count matches the prior 22-household register figure; all-code C1_08 Other text frequency totals match the previously reported 24. Raw free text is suppressed.
- C1_10 exists in the cleaned housing file and is included in the A6 code/missingness table. DCS durability classification is unavailable locally; all three material outputs remain unknown.

These checks do not validate or approve any indicator for a model. Decision references and item-level details are in `checks/decision_log_comparison.csv` and the check tables.

## Open questions

See `open_questions.md`; the unresolved items are: local DCS rule availability; suppressed C1_08 Other text; FIES denominator for both/no form; binary asset code mismatch; sensitivity-ratio definitions and interpretation of no observed working-age members; proposed C1_08 codes 5 and 10; and the missing standalone decision-log file.
