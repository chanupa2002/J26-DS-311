Research output - not an eligibility determination

# Fuzzy validation report

Input rows: 6,847. Input SHA-256: `fe77147166a0093fbdd64215be9cc85d949f87c77a120e1da1246721318a6f47`.
Proxy columns present in Stage 3 table: [].
Membership value distributions and per-domain n_used distributions are in `membership_distributions.csv` and `domain_n_used_distributions.csv`.
Households with all domains unknown: 0.
Scoring one household alone equals its full-batch score: True.

## Range checks

| Output | Within [0,1] | Observed | Min | Max |
|---|---:|---:|---:|---:|
| mu_food | True | 6801 | 0.0 | 1.0 |
| mu_crowding | True | 6792 | 0.0 | 1.0 |
| mu_dependency | True | 6847 | 0.15267115776280746 | 1.0 |
| mu_income | True | 5328 | 9.38438438438105e-05 | 0.995777027027027 |
| mu_assets | True | 6847 | 0.0003651234117131308 | 0.9991237038118884 |
| mu_tenure | True | 6845 | 0.0 | 1.0 |
| mu_toilet | True | 6825 | 0.0 | 1.0 |
| mu_wall | True | 0 | None | None |
| mu_floor | True | 0 | None | None |
| mu_roof | True | 0 | None | None |
| dom_housing | True | 6847 | 0.0 | 1.0 |
| dom_economic | True | 6847 | 0.0028479626113626644 | 0.9991237038118884 |
| dom_food | True | 6801 | 0.0 | 1.0 |
| dom_demographic | True | 6847 | 0.15267115776280746 | 1.0 |
| soft_housing_low | True | 6847 | 0.0 | 1.0 |
| soft_housing_medium | True | 6847 | 0.0 | 1.0 |
| soft_housing_high | True | 6847 | 0.0 | 1.0 |
| soft_economic_low | True | 6847 | 0.0 | 0.9943040747772747 |
| soft_economic_medium | True | 6847 | 0.001752592376223161 | 0.9986249896383896 |
| soft_economic_high | True | 6847 | 0.0 | 0.9982474076237768 |
| soft_food_low | True | 6801 | 0.0 | 1.0 |
| soft_food_medium | True | 6801 | 0.0 | 1.0 |
| soft_food_high | True | 6801 | 0.0 | 1.0 |
| soft_demographic_low | True | 6847 | 0.0 | 0.694657684474385 |
| soft_demographic_medium | True | 6847 | 0.0 | 0.9722700924330252 |
| soft_demographic_high | True | 6847 | 0.0 | 1.0 |

## Coverage

Known and unknown counts by engine input are in `input_coverage.csv`. Explicit `unknown` strings and blanks are passed as unknown by the adapter.

No overall vulnerability score or ranking is produced. These engineering and software checks do not validate indicators or domains for decision use.
