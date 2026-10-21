# Stage 5 summary

Research output - not an eligibility determination


- Baseline BN scored 6,847 households with `config_v02_interim()` and the eight M-07 leaves. Exposure and legacy housing degree were excluded from baseline input.
- Expected vulnerability: mean 0.4140; median 0.4075; range 0.2666–0.6890. `bn_p_high` exceeds 0.3 for 2.50% and 0.5 for 0.06%.
- Observed BN leaf count distribution: 7 leaves: 81, 8 leaves: 6766.
- Validation and printed CPTs: `bn_validation.md`; coverage correlations: `coverage_correlations.csv`.
- Additive 8-leaf index correlation with BN expected vulnerability: 0.9415; percentile ranks differ by >20 points for 352/6,847 households.
- Sensitivity scenarios run: 18 (individual outputs under `sensitivity/`); compare table: `sensitivity_comparison.csv`. Flat alternative CPT: `flat_sensitivity_cpt_729.csv` (729 rows).
- Province/district join: 6,847 rows preserved; 9 province codes and 25 district codes. Only aggregate tables are provided.
- Exposure audit found 6,847 fuzzy exposure degrees in the Stage 4 input; baseline excluded them. The UNAPPROVED exposure-included sensitivity is reported separately.
- No score is validated for decision use; BN outputs are expert-specified research composites, not eligibility decisions or calibrated probabilities of vulnerability.

## Open questions

- Exposure is excluded from baseline exactly as required. The separate include_exposure BN run is UNAPPROVED and does not change baseline outputs.
- Stage 4b O1 mean severity uses researcher-approved equal spacing (1 severe=1, 2 moderate=0.5, 3 none=0) and the assumed 12-month reference period for all items. This Stage 5 network still excludes exposure from baseline per the task rule.
- B-02 sensitivity weights were operationalized as two explicit scenarios: economic+food pathways doubled and demographic pathway doubled, with the corresponding group weight doubled at the top node. Alternative interpretations of “doubled” were not run.
- For n_states=5, the most-probable-level comparison collapses very_low+low to low, keeps medium, and combines high+very_high to high, so level-change shares are comparable with the 3-state baseline.
- Province and district aggregates use the one-to-one household identification join because geography is not a column in the Stage 4 fuzzy file; only aggregate rows are written.
- Conditional tables follow the expert-specified ranked-nodes method. They are not learned from outcome labels or data; scores are research composites and are not validated for decision use.
- Domains are treated as independent evidence in this tree even though they may be correlated; ranked-node smoothing pulls estimates toward the middle. Alternative combination functions remain for a later round.
