# Stage 4b v0.2 fuzzy integration

Research output - not an eligibility determination

- Scored 6,847 unique households. D-10a all-18-valid is applied; current valid count is 6,847/6,847.
- Integrated approved fuzzy leaves: exposure, legacy housing (for reference), economic, food, demographic, shelter quality, sanitation, crowding and tenure, health, and financial resilience.
- Housing split uses the addendum rule: shelter=mean wall/floor/roof, sanitation=toilet, crowding/tenure=mean crowding/tenure. N-01 bank no and N-02 debt yes map to deprivation 1.
- N-01/N-02 flag agreement check: 6847/6847 household codes agree with the source-flag cross-tab.
- Health coverage status: valid 6,170; partial 666; missing 11.
- O1 all-20-valid households: 26; all-20 validity is not required for the mean. User assumption applies the past-12-month period to all 20 items. Raw responses, valid-item count, and exposure mean severity are carried; no valid items yields unknown.
- Domain coverage and n_used: `domain_coverage_v0_2.csv`. Sensitivity score comparisons: `sensitivity_comparison_v0_2.csv` and `sensitivity_v0_2/`.
- This is a fuzzy-layer integration only. No Bayesian Network, CPT, vulnerability node, overall score, or ranking was produced.

## Sensitivity results

| Scenario | Spearman vs primary | N | Mean absolute degree change | Changed N / share |
|---|---:|---:|---:|---:|
| financial_exclude_N01 | 0.935404 | 6847 | 0.225792 | 3092 / 45.158% |
| financial_exclude_N02 | 0.268167 | 6847 | 0.225792 | 3092 / 45.158% |
| financial_reverse_N02 | -0.812923 | 6847 | 0.500000 | 6847 / 100.000% |
| health_any_chronic_binary | 0.823483 | 6836 | 0.359259 | 4012 / 58.689% |
| shelter_quality_max | 0.999695 | 6845 | 0.022717 | 262 / 3.828% |
| crowding_tenure_max | 0.995377 | 6847 | 0.087486 | 2266 / 33.095% |

## Domain coverage

| Leaf/domain | Degree known | Degree unknown | n_used distribution |
|---|---:|---:|---|
| legacy_housing | 6847 | 0 | 3:21; 4:121; 5:650; 6:6055 |
| economic | 6847 | 0 | 1:1519; 2:5328 |
| food | 6801 | 46 | 0:46; 1:6801 |
| demographic | 6847 | 0 | 1:6847 |
| shelter_quality | 6845 | 2 | 0:2; 1:116; 2:638; 3:6091 |
| sanitation | 6825 | 22 | 0:22; 1:6825 |
| crowding_tenure | 6847 | 0 | 1:57; 2:6790 |
| health | 6836 | 11 | 0:11; 1:6836 |
| financial_resilience | 6847 | 0 | 2:6847 |
| exposure | 6847 | 0 | 12:2637; 13:506; 14:42; 18:3162; 19:474; 20:26 |

## Open questions

- User assumption: all 20 O1 items refer to the past 12 months (item 20 states this explicitly; items 1-19 are covered by the assumption). Approved mean severity maps 1 severe=1, 2 moderate=0.5, 3 none=0 and averages valid answers only; no valid answers remains unknown.
- H-01 uses b3_01-derived share_chronic. B3 status counts are valid=6170, partial=666, missing=11; partial-coverage shares are included and flagged, as permitted by 9.6.
- N-02 has-debt direction follows the approved researcher judgement (yes=deprivation); exclusion and reversal sensitivities are reported.
- O2 coping remains conditional because code handling for 3, 4, 997 is unresolved. L3 energy and L5 water remain candidate-only pending evidence and scale/skip review; P wellbeing is descriptive only; livelihood remains deferred.
- This run produces fuzzy leaf memberships and domain degrees only. The hierarchical Bayesian Network in M-06/M-07, its CPTs, priors, and sensitivity runs have not been calculated here.
- Stage 4 v0.1 frozen income, asset and dependency references are reused. D-10a masks asset membership unless all 18 items are valid; current Stage 3 has all 18 valid for every household.
- A domain degree is the available-input mean; missing inputs remain unknown and are excluded from n_used. No cross-domain composite, overall vulnerability score, or ranking is produced.
