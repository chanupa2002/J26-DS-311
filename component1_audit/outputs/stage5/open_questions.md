# Stage 5 open questions

Research output - not an eligibility determination

- Exposure is excluded from baseline exactly as required. The separate include_exposure BN run is UNAPPROVED and does not change baseline outputs.
- Stage 4b O1 mean severity uses researcher-approved equal spacing (1 severe=1, 2 moderate=0.5, 3 none=0) and the assumed 12-month reference period for all items. This Stage 5 network still excludes exposure from baseline per the task rule.
- B-02 sensitivity weights were operationalized as two explicit scenarios: economic+food pathways doubled and demographic pathway doubled, with the corresponding group weight doubled at the top node. Alternative interpretations of “doubled” were not run.
- For n_states=5, the most-probable-level comparison collapses very_low+low to low, keeps medium, and combines high+very_high to high, so level-change shares are comparable with the 3-state baseline.
- Province and district aggregates use the one-to-one household identification join because geography is not a column in the Stage 4 fuzzy file; only aggregate rows are written.
- Conditional tables follow the expert-specified ranked-nodes method. They are not learned from outcome labels or data; scores are research composites and are not validated for decision use.
- Domains are treated as independent evidence in this tree even though they may be correlated; ranked-node smoothing pulls estimates toward the middle. Alternative combination functions remain for a later round.
