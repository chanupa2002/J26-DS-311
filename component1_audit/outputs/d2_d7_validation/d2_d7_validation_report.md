# Coordinated D2–D7 indicator validation audit

**Status:** descriptive validation only. Domains remain provisional; none of these results approves a final model feature. No fuzzy membership, Bayesian dependency, weight, ranking, eligibility decision, deprivation score, household aggregate, or recoded item was produced.

## Provenance and method

Cleaned inputs read from `Data/processed/clean/`: `mod_l1_food_security_w.csv`, `mod_l2_food_security_m.csv`, `mod_b0_roster_long.csv`, `mod_b1_roster_long.csv`, `mod_b3_roster_long.csv`, `mod_h1_primary_employment_long.csv`, `mod_h2_secondary_employment_lon.csv`, `mod_o1_shocks.csv`, `mod_f3_ag_maha_2023-2024.csv`, `mod_f7_ag_maha_2024-2025.csv`, `mod_f1_ag_seasons.csv`, `mod_g1_livestock.csv`, `mod_g2_fish.csv`, `mod_i_nonfarm_business.csv`, `mod_o2_coping.csv`, `mod_n1_debt.csv`, `mod_n2_savings.csv`, `mod_n3_savings_w.csv`. Prepared comparison input: `Data/processed/hh_indicators.csv` (only for read-only diagnostics of existing D2/D7 prepared values). Questionnaire: `Data/BRIGHT_questionnaire_English.pdf`. Outputs contain aggregate frequencies and validation notes only; no identifiers or personal free-text. The builder is `component1_audit/scripts/build_d2_d7_validation.py`.

## Results by domain

- **D2 Food insecurity.** L1 women and L2 men forms were profiled separately across eight core items and available follow-ups. Questionnaire pp.177–182 specify 12-month food-access experiences with 1 Yes, 2 No, 3 Don't know, 4 Refused. Follow-up wording contains cross-form/item references that need verification. The existing prepared `d2_fies_raw` has 39 missing and 3 fractional values; fractional values: {'1.5': 1, '2.5': 1, '0.5': 1}. L1 answered flag totals 4163; L2 2696. No source transformation reproduces these prepared outputs; do not score or combine forms.
- **D3 Household needs.** B0 age years and months remain separate; B3 condition and activity responses are profiled at member level. Roster has 27,875 rows; B3 has 27,021 rows and 0 B3 keys outside B0. Questionnaire B3_01 lists 1 No/2 Yes but its skip text says B3_01=1; B3_03 code 7 describes complete interruption more than 12 months ago despite the question's last-year frame. No age thresholds, age conversion, or household rollup was applied. Candidate formulas remain alternatives only: age-band shares use an approved age threshold and roster denominator; a dependency ratio needs approved dependent and working-age bands plus denominator.
- **D4 Livelihood/income.** H1/H2 person records have 27,883/27,883 rows; unique `hhcode+hhmember` checks passed. H1/H2 person key sets: 0 H1-only and 0 H2-only. H1_17 is total monthly household income in LKR, repeated in employment rows; household diagnostics: {'households': 6847, 'households_multiple_h1_records': 6663, 'households_repeated_nonmissing_h1_17': 5328, 'households_conflicting_nonmissing_h1_17': 0, 'households_no_nonmissing_h1_17': 0}. It was not summed. H1_05 is past-12-month unemployment; H1_13 is job search in last 4 weeks conditional on H1_01=8. H2_02 wording does not map transparently to cleaned H2 `h1_02`; crosswalk remains unresolved.
- **D5 Shocks.** O1 response distributions are retained by item; 1=severe, 2=moderate, 3=no impact. Questionnaire explicitly gives past 12 months for item 20; items 1–19 period remains unverified. Gate blanks are not interpreted as no shock. F3 (Maha 2023–24) and F7 (Maha 2024–25) remain separate source modules.
- **D6 Coping.** O2 items are profiled individually. Preserve distinctions among Yes, No because unnecessary, discontinued action, Not applicable and Prefer not to say; do not reduce these to used/exhausted flags. O2_05/O2_06 have the F1_00a=1 gate, and follow-up checkboxes depend on Yes responses. The O2 source is separate from O1.
- **D7 Financial resilience.** N1, N2 and N3 remain separate. N1_00 cleaned values and questionnaire codes differ; raw amount slots are preserved as frequency/missingness summaries. Among 2,947 records with cleaned N1 status `1`, 11 have all amount slots missing and 2 contain an explicit zero amount slot. N1_03 asks amount of loan taken, not verified outstanding balance. The prior issue review also records 20 debt-positive prepared totals at zero and 12 debt-positive cases without positive raw amount slots; this audit did not calculate or replace those totals. N2_01 is bank-account access; N2_02 is savings location. N3 is a separate women's form and field names differ; the existing review found N2/N3 savings responses disagree in 1,453 of 5,393 paired records. No debt/savings sums or ratios were computed.

## Checks actually executed

- Key completeness and uniqueness checked for household master, each household module, and person keys in B0/B1/B3 and H1/H2; 19 file/grain checks passed with zero missing-key rows and zero duplicate-key rows.
- B3 person keys are a subset of B0; H1/H2 keys compared; no join was performed that could multiply records.
- Every reported field has frequency and missingness counts with explicit module-record and nonmissing denominators. Explicit 0 values remain separate from blanks.
- Existing prepared D2 fractional/missing counts and raw N1 amounts were inspected as aggregate diagnostics only. No prepared feature was changed.
- No aggregation/score reproduction, sample disposition reconciliation, or raw-to-clean transformation replay was possible from available scripts; those were not executed.

## Priority issues and researcher review choices

1. **Critical – D2 score provenance:** recover respondent selection, item-level scoring, partial response and DK/refusal handling; alternatively leave L1/L2 item-level only.
2. **Critical – D7 debt meaning:** decide whether N1 amount-taken fields can support a debt-burden construct; obtain current balance/source lineage before any total.
3. **High – D3 and D4 semantic crosswalks:** resolve B3 code/skip contradictions and H2_02-to-clean-field mapping.
4. **High – D5 applicability/reference periods and D6 response semantics:** verify gated missingness and periods; retain category detail.
5. **Medium – form combinations, age thresholds and overlap:** choose only after evidence review; N2/N3 and F3/F7 remain separate until an approved crosswalk/target period exists.

Candidate alternatives are: (a) keep raw items/form-specific descriptions; (b) define a documented item-level construct and eligible denominator after source clarification; or (c) defer the candidate. These are review choices, not recommendations to implement now. The cross-domain register explains overlap without removing correlated items. The bottom-quintile consumption proxy was not used as ground truth or a model feature.
