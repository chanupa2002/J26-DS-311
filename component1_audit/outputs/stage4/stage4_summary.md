Research output - not an eligibility determination

# Stage 4 fuzzy layer v0.1 summary

Integrated engine `fuzzy-0.1.0` with 6,847 Stage 3 households. Created frozen income, asset and dependency empirical references; per-input memberships, domain degrees, n_used/n_total and soft levels; validation and sensitivity artifacts. No overall vulnerability score or ranking was produced.

Validation: unique household keys and expected row count passed; proxy columns absent; single-household/full-batch equivalence=True; all-domain-unknown households=0. Per-output [0,1] checks are recorded in `fuzzy_validation.md`.

Toilet correction: `mu_toilet` is observed for 6,825 households. Compared with the previous score, 6651 households changed; details are in `toilet_score_correction_comparison.json`.

The `toilet_service_class` by `toilet_type_class` cross-tab is in `toilet_service_cross_tab.csv`.

Sensitivity includes four crowding ramp combinations, alternate 60+ age definition, D-05 tenure recoding, toilet type-only (sharing ignored), and domain min/max operators. Sensitivity Spearman correlations and largest-soft-membership level change shares are in `sensitivity/sensitivity_comparison.csv`. FIES prorating was not run because its scaling rule is unspecified.

## Open questions

1. FIES prorating for one or two invalid items remains unrun because D-01 does not specify a prorating formula.
2. All three Stage 3 material durability fields remain unknown because the local DCS rule was unavailable; no material memberships are observed.
3. Binary ownership fields d_12-d_16 remain partly missing under the registered 1/2 versus cleaned 0/1 mismatch; Stage 4 uses the existing asset aggregate unchanged.
4. `MIN_VALID_ASSETS=None` is retained; D-10 leaves the valid-item denominator threshold open, so no threshold is enforced.
5. Crowding midpoint 3/half-width 1, equal-spaced TENURE_DEGREE and TOILET_DEGREE, and triangular soft low/medium/high boundaries are researcher judgements retained from the engine, not validated standards; crowding alternatives are reported in sensitivity outputs.
6. Sanitation codes 5 and 10 remain unconfirmed by Stage 3; the toilet-type-only run does not resolve them.
7. Sensitivity change shares resolve exact soft-membership ties by engine output order (low, medium, high; first maximum wins); the decision log specifies no tie rule.

Results are research outputs only; no indicator or domain is validated for decision use. See `open_questions.md` for detail.
