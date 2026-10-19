Research output - not an eligibility determination

# Stage 4 open questions

1. D-04b correction applied: C1_10 codebook is 0=not shared and 1=shared for this cleaned file only; other values are unknown. This overrides the questionnaire's 1/2 convention for C1_10, with no other variable recoded.

2. FIES prorated score sensitivity not run because D-01 does not specify how to prorate a raw score with one or two invalid items; no formula was invented.

3. Stage 3 material durability fields are all the literal value `unknown` because the local DCS rule was unavailable in Stage 3; the adapter passes these as NaN. No material memberships can be observed.

4. The supplied codebook rule for d_12-d_16 (0=No, 1=Yes; owned=1) is applied in Stage 3 only to those five variables. Stage 4 consumes the resulting asset_types_owned_n and asset_items_valid_n. The named docs/codebook_crosscheck_v0_1.md was not present in the workspace, so this build relies on the explicit code facts in the task.

5. Stage 3 reports b0_01a/b0_01b failure counts and household-size/dependency counterfactuals in checks/A8_roster_flag_counterfactuals.csv, assuming raw flag=0 means fail for the diagnostic. Neither flag is applied to Stage 3 or Stage 4 inputs.

6. The engine default MIN_VALID_ASSETS=None is retained: no minimum asset-item completeness threshold is enforced. D-10 leaves the denominator rule open; Stage 4 does not add a threshold.

7. The crowding midpoint 3/half-width 1, TENURE_DEGREE and TOILET_DEGREE equal-spaced ordinal mappings, and soft low/medium/high boundaries are researcher judgements retained from the reference engine, not validated standards. The requested crowding perturbations are reported separately.

8. The Stage 3 C1_08 mapping retains codes 5 and 10 as unconfirmed; the toilet-type-only sensitivity does not resolve those codes.

9. Sensitivity level-change shares assign exact soft-membership ties using the engine output order low, medium, high (first maximum wins). The decision log does not specify a tie rule; the comparison should be interpreted with this implementation convention in mind.
