# Stage 5 Bayesian Network validation

Research output - not an eligibility determination

- Input rows: 6,847; scored rows: 6,847; unique scored keys: 6,847.
- Baseline: `config_v02_interim()`; eight leaves exactly as M-07 specifies. Exposure and legacy housing columns are excluded from the input whitelist.
- Probability validation: 12 node-posterior columns checked; all in [0,1] and each node distribution sums to 1 within 1e-9.
- Scoring one household at a time matched batch scoring for 50 random households (seed 20261021); maximum absolute difference = 1.11e-16.

## Adapter column check

| research_label | leaf | soft_columns_present | n_used_total_columns_present | soft_complete_rows | soft_sum_bad_rows | soft_partial_rows | coverage_count_bad_rows | observed_leaf_rows | n_used_total_distribution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Research output - not an eligibility determination | shelter_quality | True | True | 6845 | 0 | 0 | 0 | 6845 | 0/3:2; 1/3:116; 2/3:638; 3/3:6091 |
| Research output - not an eligibility determination | sanitation | True | True | 6825 | 0 | 0 | 0 | 6825 | 0/1:22; 1/1:6825 |
| Research output - not an eligibility determination | crowding_tenure | True | True | 6847 | 0 | 0 | 0 | 6847 | 1/2:57; 2/2:6790 |
| Research output - not an eligibility determination | food | True | True | 6801 | 0 | 0 | 0 | 6801 | 0/1:46; 1/1:6801 |
| Research output - not an eligibility determination | demographic | True | True | 6847 | 0 | 0 | 0 | 6847 | 1/1:6847 |
| Research output - not an eligibility determination | health | True | True | 6836 | 0 | 0 | 0 | 6836 | 0/1:11; 1/1:6836 |
| Research output - not an eligibility determination | economic | True | True | 6847 | 0 | 0 | 0 | 6847 | 1/2:1519; 2/2:5328 |
| Research output - not an eligibility determination | financial_resilience | True | True | 6847 | 0 | 0 | 0 | 6847 | 2/2:6847 |

## Baseline score distributions

| measure | n | min | q1 | median | q3 | max | share_gt_0.3 | share_gt_0.5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bn_p_high | 6847 | 0.009646 | 0.053039 | 0.089643 | 0.147897 | 0.590734 | 0.024974 | 0.000584 |
| bn_expected_vulnerability | 6847 | 0.266624 | 0.361822 | 0.407524 | 0.461936 | 0.689043 |  |  |
| bn_uncertainty_entropy | 6847 | 0.586806 | 0.785651 | 0.831660 | 0.855701 | 0.883342 |  |  |

## Households by observed BN leaves

| bn_leaves_observed | households_n |
| --- | --- |
| 7 | 81 |
| 8 | 6766 |

## Conditional probability tables

### living_conditions (27 rows)

| shelter_quality | sanitation | crowding_tenure | P(low) | P(medium) | P(high) |
| --- | --- | --- | --- | --- | --- |
| low | low | low | 0.8463 | 0.1533 | 0.0005 |
| low | low | medium | 0.6327 | 0.3624 | 0.0049 |
| low | low | high | 0.3525 | 0.6154 | 0.0322 |
| low | medium | low | 0.6327 | 0.3624 | 0.0049 |
| low | medium | medium | 0.3525 | 0.6154 | 0.0322 |
| low | medium | high | 0.1329 | 0.7341 | 0.1329 |
| low | high | low | 0.3525 | 0.6154 | 0.0322 |
| low | high | medium | 0.1329 | 0.7341 | 0.1329 |
| low | high | high | 0.0322 | 0.6154 | 0.3525 |
| medium | low | low | 0.6327 | 0.3624 | 0.0049 |
| medium | low | medium | 0.3525 | 0.6154 | 0.0322 |
| medium | low | high | 0.1329 | 0.7341 | 0.1329 |
| medium | medium | low | 0.3525 | 0.6154 | 0.0322 |
| medium | medium | medium | 0.1329 | 0.7341 | 0.1329 |
| medium | medium | high | 0.0322 | 0.6154 | 0.3525 |
| medium | high | low | 0.1329 | 0.7341 | 0.1329 |
| medium | high | medium | 0.0322 | 0.6154 | 0.3525 |
| medium | high | high | 0.0049 | 0.3624 | 0.6327 |
| high | low | low | 0.3525 | 0.6154 | 0.0322 |
| high | low | medium | 0.1329 | 0.7341 | 0.1329 |
| high | low | high | 0.0322 | 0.6154 | 0.3525 |
| high | medium | low | 0.1329 | 0.7341 | 0.1329 |
| high | medium | medium | 0.0322 | 0.6154 | 0.3525 |
| high | medium | high | 0.0049 | 0.3624 | 0.6327 |
| high | high | low | 0.0322 | 0.6154 | 0.3525 |
| high | high | medium | 0.0049 | 0.3624 | 0.6327 |
| high | high | high | 0.0005 | 0.1533 | 0.8463 |

### sensitivity (81 rows)

| living_conditions | food | demographic | health | P(low) | P(medium) | P(high) |
| --- | --- | --- | --- | --- | --- | --- |
| low | low | low | low | 0.8463 | 0.1533 | 0.0005 |
| low | low | low | medium | 0.6962 | 0.3009 | 0.0029 |
| low | low | low | high | 0.4933 | 0.4933 | 0.0133 |
| low | low | medium | low | 0.6962 | 0.3009 | 0.0029 |
| low | low | medium | medium | 0.4933 | 0.4933 | 0.0133 |
| low | low | medium | high | 0.2873 | 0.6648 | 0.0479 |
| low | low | high | low | 0.4933 | 0.4933 | 0.0133 |
| low | low | high | medium | 0.2873 | 0.6648 | 0.0479 |
| low | low | high | high | 0.1329 | 0.7341 | 0.1329 |
| low | medium | low | low | 0.6962 | 0.3009 | 0.0029 |
| low | medium | low | medium | 0.4933 | 0.4933 | 0.0133 |
| low | medium | low | high | 0.2873 | 0.6648 | 0.0479 |
| low | medium | medium | low | 0.4933 | 0.4933 | 0.0133 |
| low | medium | medium | medium | 0.2873 | 0.6648 | 0.0479 |
| low | medium | medium | high | 0.1329 | 0.7341 | 0.1329 |
| low | medium | high | low | 0.2873 | 0.6648 | 0.0479 |
| low | medium | high | medium | 0.1329 | 0.7341 | 0.1329 |
| low | medium | high | high | 0.0479 | 0.6648 | 0.2873 |
| low | high | low | low | 0.4933 | 0.4933 | 0.0133 |
| low | high | low | medium | 0.2873 | 0.6648 | 0.0479 |
| low | high | low | high | 0.1329 | 0.7341 | 0.1329 |
| low | high | medium | low | 0.2873 | 0.6648 | 0.0479 |
| low | high | medium | medium | 0.1329 | 0.7341 | 0.1329 |
| low | high | medium | high | 0.0479 | 0.6648 | 0.2873 |
| low | high | high | low | 0.1329 | 0.7341 | 0.1329 |
| low | high | high | medium | 0.0479 | 0.6648 | 0.2873 |
| low | high | high | high | 0.0133 | 0.4933 | 0.4933 |
| medium | low | low | low | 0.6962 | 0.3009 | 0.0029 |
| medium | low | low | medium | 0.4933 | 0.4933 | 0.0133 |
| medium | low | low | high | 0.2873 | 0.6648 | 0.0479 |
| medium | low | medium | low | 0.4933 | 0.4933 | 0.0133 |
| medium | low | medium | medium | 0.2873 | 0.6648 | 0.0479 |
| medium | low | medium | high | 0.1329 | 0.7341 | 0.1329 |
| medium | low | high | low | 0.2873 | 0.6648 | 0.0479 |
| medium | low | high | medium | 0.1329 | 0.7341 | 0.1329 |
| medium | low | high | high | 0.0479 | 0.6648 | 0.2873 |
| medium | medium | low | low | 0.4933 | 0.4933 | 0.0133 |
| medium | medium | low | medium | 0.2873 | 0.6648 | 0.0479 |
| medium | medium | low | high | 0.1329 | 0.7341 | 0.1329 |
| medium | medium | medium | low | 0.2873 | 0.6648 | 0.0479 |
| medium | medium | medium | medium | 0.1329 | 0.7341 | 0.1329 |
| medium | medium | medium | high | 0.0479 | 0.6648 | 0.2873 |
| medium | medium | high | low | 0.1329 | 0.7341 | 0.1329 |
| medium | medium | high | medium | 0.0479 | 0.6648 | 0.2873 |
| medium | medium | high | high | 0.0133 | 0.4933 | 0.4933 |
| medium | high | low | low | 0.2873 | 0.6648 | 0.0479 |
| medium | high | low | medium | 0.1329 | 0.7341 | 0.1329 |
| medium | high | low | high | 0.0479 | 0.6648 | 0.2873 |
| medium | high | medium | low | 0.1329 | 0.7341 | 0.1329 |
| medium | high | medium | medium | 0.0479 | 0.6648 | 0.2873 |
| medium | high | medium | high | 0.0133 | 0.4933 | 0.4933 |
| medium | high | high | low | 0.0479 | 0.6648 | 0.2873 |
| medium | high | high | medium | 0.0133 | 0.4933 | 0.4933 |
| medium | high | high | high | 0.0029 | 0.3009 | 0.6962 |
| high | low | low | low | 0.4933 | 0.4933 | 0.0133 |
| high | low | low | medium | 0.2873 | 0.6648 | 0.0479 |
| high | low | low | high | 0.1329 | 0.7341 | 0.1329 |
| high | low | medium | low | 0.2873 | 0.6648 | 0.0479 |
| high | low | medium | medium | 0.1329 | 0.7341 | 0.1329 |
| high | low | medium | high | 0.0479 | 0.6648 | 0.2873 |
| high | low | high | low | 0.1329 | 0.7341 | 0.1329 |
| high | low | high | medium | 0.0479 | 0.6648 | 0.2873 |
| high | low | high | high | 0.0133 | 0.4933 | 0.4933 |
| high | medium | low | low | 0.2873 | 0.6648 | 0.0479 |
| high | medium | low | medium | 0.1329 | 0.7341 | 0.1329 |
| high | medium | low | high | 0.0479 | 0.6648 | 0.2873 |
| high | medium | medium | low | 0.1329 | 0.7341 | 0.1329 |
| high | medium | medium | medium | 0.0479 | 0.6648 | 0.2873 |
| high | medium | medium | high | 0.0133 | 0.4933 | 0.4933 |
| high | medium | high | low | 0.0479 | 0.6648 | 0.2873 |
| high | medium | high | medium | 0.0133 | 0.4933 | 0.4933 |
| high | medium | high | high | 0.0029 | 0.3009 | 0.6962 |
| high | high | low | low | 0.1329 | 0.7341 | 0.1329 |
| high | high | low | medium | 0.0479 | 0.6648 | 0.2873 |
| high | high | low | high | 0.0133 | 0.4933 | 0.4933 |
| high | high | medium | low | 0.0479 | 0.6648 | 0.2873 |
| high | high | medium | medium | 0.0133 | 0.4933 | 0.4933 |
| high | high | medium | high | 0.0029 | 0.3009 | 0.6962 |
| high | high | high | low | 0.0133 | 0.4933 | 0.4933 |
| high | high | high | medium | 0.0029 | 0.3009 | 0.6962 |
| high | high | high | high | 0.0005 | 0.1533 | 0.8463 |

### adaptive_capacity (9 rows)

| economic | financial_resilience | P(low) | P(medium) | P(high) |
| --- | --- | --- | --- | --- |
| low | low | 0.8463 | 0.1533 | 0.0005 |
| low | medium | 0.4933 | 0.4933 | 0.0133 |
| low | high | 0.1329 | 0.7341 | 0.1329 |
| medium | low | 0.4933 | 0.4933 | 0.0133 |
| medium | medium | 0.1329 | 0.7341 | 0.1329 |
| medium | high | 0.0133 | 0.4933 | 0.4933 |
| high | low | 0.1329 | 0.7341 | 0.1329 |
| high | medium | 0.0133 | 0.4933 | 0.4933 |
| high | high | 0.0005 | 0.1533 | 0.8463 |

### vulnerability (9 rows)

| sensitivity | adaptive_capacity | P(low) | P(medium) | P(high) |
| --- | --- | --- | --- | --- |
| low | low | 0.8463 | 0.1533 | 0.0005 |
| low | medium | 0.4933 | 0.4933 | 0.0133 |
| low | high | 0.1329 | 0.7341 | 0.1329 |
| medium | low | 0.4933 | 0.4933 | 0.0133 |
| medium | medium | 0.1329 | 0.7341 | 0.1329 |
| medium | high | 0.0133 | 0.4933 | 0.4933 |
| high | low | 0.1329 | 0.7341 | 0.1329 |
| high | medium | 0.0133 | 0.4933 | 0.4933 |
| high | high | 0.0005 | 0.1533 | 0.8463 |

