# Stage 6 evaluation report

Research output - not an eligibility determination

## Purpose and design

This is a comparative agreement, ranking-stability and missing-evidence robustness study. There is no independent outcome reference. No method is calibrated or selected using the proxy fields. The fuzzy rules, BN structure, tables, baseline outputs, and approved specification were read-only. No eligibility interpretation is supported.

The Stage 4b and Stage 5 inputs aligned on 6,847 unique household keys. The Stage 5 network score itself does not store a percentile; F1 percentile is derived from the expected-vulnerability ranking. A 200-call synthetic `score_record` benchmark averaged 0.010609 seconds per call.

## Methods compared

- **F1:** current v0.2 interim Bayesian framework expected vulnerability (primary); P(high) reported separately.
- **F0:** equal-weight available-case mean of the four Stage 4 domain degrees.
- **B1:** available-case unweighted mean of all 14 Stage 4b `mu_*` memberships, including the published exposure membership.
- **B2:** first principal component of standardized Stage 4b memberships, complete cases only; sign oriented to agree with B1. Complete-case coverage: 4,739; variance explained: 0.155; pre-orientation PC1/B1 correlation: 0.860.
- **B3:** equal-weight four-domain counting score, within-domain equal indicator weights, deprivation threshold 0.5, and available-indicator rescaling. It is a transparent counting baseline, not the official MPI. Threshold sensitivities at 0.4 and 0.6 are in `b3_threshold_sensitivity.csv`.

All scores are oriented higher = more vulnerable. Coverage, tie resolution, and distributions are reported in `method_score_distributions.csv` and `m6_ties_resolution.csv`.

## Results per metric

### M1 — Agreement between methods

Spearman, Kendall tau, and top-10/20/30% Jaccard are in `m1_method_agreement.csv`; heatmaps are in `figures/method_agreement_heatmap.png`.

Highest five pairwise Spearman values:

| method_a | method_b | n_common | spearman | kendall_tau | top_10_jaccard |
| -------- | -------- | -------- | -------- | ----------- | -------------- |
| F1       | B1       | 6847     | 0.927    | 0.770       | 0.489          |
| F0       | B3       | 6847     | 0.919    | 0.774       | 0.527          |
| B1       | B2       | 4739     | 0.860    | 0.670       | 0.510          |
| F0       | B2       | 4739     | 0.834    | 0.638       | 0.423          |
| F1       | F0       | 6847     | 0.809    | 0.610       | 0.380          |

Lowest five pairwise Spearman values are also shown to give less-aligned results equal prominence:

| method_a | method_b | n_common | spearman | kendall_tau | top_10_jaccard |
| -------- | -------- | -------- | -------- | ----------- | -------------- |
| B1       | B3       | 6847     | 0.741    | 0.563       | 0.278          |
| F1       | B3       | 6847     | 0.745    | 0.564       | 0.309          |
| B2       | B3       | 4739     | 0.772    | 0.596       | 0.306          |
| F0       | B1       | 6847     | 0.802    | 0.604       | 0.389          |
| F1       | B2       | 4739     | 0.804    | 0.604       | 0.413          |

### M2 — Perturbation stability of F1

Ran 200 replicates with crowding midpoint U(2.5, 4.0), half-width U(0.5, 1.5), bootstrap-refitted income/assets/dependency TFR references, and independent Dirichlet weight draws for each exposed BN node-parent vector. Network input weights are exposed and were perturbed. Per-household rank p05/p50/p95 and interval width are stored in the ignored local `scores_all_methods.csv` and `m2_household_rank_intervals.csv`. Stratified sample plot: `figures/rank_intervals_stratified_sample.png`.

| replicates | spearman_mean | spearman_sd | spearman_p05 | spearman_median | spearman_p95 | top_decile_retention_mean | top_decile_retention_p05 | top_decile_retention_p95 |
| ---------- | ------------- | ----------- | ------------ | --------------- | ------------ | ------------------------- | ------------------------ | ------------------------ |
| 200        | 0.951         | 0.032       | 0.888        | 0.962           | 0.990        | 0.808                     | 0.686                    | 0.897                    |

### M3 — Missing-evidence stress

For F1, F0, B1, and B3, 100 replicates at each rate mask exactly the rounded requested fraction of known membership cells completely at random. Unknown values remain unknown. Results report Spearman against each method's unmasked score and top-decile retention; curve: `figures/masking_curve.png`.

| method | masked_fraction | replicates | spearman_mean | top_decile_retention_mean |
| ------ | --------------- | ---------- | ------------- | ------------------------- |
| F1     | 0.100           | 100        | 0.947         | 0.815                     |
| F0     | 0.100           | 100        | 0.954         | 0.877                     |
| B1     | 0.100           | 100        | 0.950         | 0.811                     |
| B3     | 0.100           | 100        | 0.954         | 0.837                     |
| F1     | 0.200           | 100        | 0.890         | 0.708                     |
| F0     | 0.200           | 100        | 0.902         | 0.778                     |
| B1     | 0.200           | 100        | 0.896         | 0.715                     |
| B3     | 0.200           | 100        | 0.905         | 0.752                     |
| F1     | 0.300           | 100        | 0.831         | 0.626                     |
| F0     | 0.300           | 100        | 0.842         | 0.691                     |
| B1     | 0.300           | 100        | 0.838         | 0.643                     |
| B3     | 0.300           | 100        | 0.850         | 0.655                     |

### M4 — Evidence and uncertainty relationship

Evidence count is the number of observed BN leaves. Uncertainty is Stage 5 normalized posterior entropy; no posterior interval is provided. Associations are descriptive and do not establish that changing evidence causes score changes.

| relationship                                  | n    | spearman | kendall_tau | direction                                   |
| --------------------------------------------- | ---- | -------- | ----------- | ------------------------------------------- |
| available BN leaves vs expected_vulnerability | 6847 | -0.045   | -0.037      | higher evidence associated with lower value |
| available BN leaves vs posterior_entropy      | 6847 | -0.053   | -0.043      | higher evidence associated with lower value |

### M5 — Subgroup behaviour

Province, district, and stored sector-code summaries include sample and `hhweight`-weighted views. Statistics for cells below MIN_CELL=10 are suppressed. See `m5_subgroups.csv`; a province sample plot is `figures/subgroup_province_F1.png`. Weighted rank agreement uses weighted Pearson correlation of within-subgroup midranks.

### M6 — Tie and resolution check

Counts and share of households in tied score groups are in `m6_ties_resolution.csv`.

## Where F1 has higher and lower agreement/stability

The pairwise results above show both closer and weaker agreement between F1 and baselines; interpret the complete table, not only the strongest comparisons. Perturbation stability and missing-evidence degradation are reported alongside the baselines. No method is described as accurate or validated.

## Separate descriptive sensitivity proxy

Proxy agreement is isolated in `proxy_reference/` and includes all methods. `label_high_vuln` is the weighted bottom-quintile classification of `pc_cons`; `pc_cons` is documented as `total_month / hh_size`. Exact upstream consumption construction is incomplete. Economic inputs may overlap conceptually or through source components. These are descriptive sensitivity comparisons, not independent outcome measurements and not headline findings.

## Limitations

- No independent outcome data exist; calibration and outcome validation are not performed.
- The interim D-03a shelter-material rule remains a limitation.
- BN conditional tables are expert-set research tables.
- FIES form comparability remains pending.
- Inputs are missing for some households; no missing value was imputed.
- Baseline estimates are research composites and are not eligibility determinations.

## Appendix: parameters and seeds

Seeds: perturbation 20261022; missingness 20261023; stratified figure sample 20261024. Replicates: perturbation 200; missingness 100 per rate. MIN_CELL=10. B3 threshold 0.5 primary, with 0.4/0.6 sensitivity. Full hashes and package versions are in `manifest.json`; unresolved choices are listed in `open_questions.md`.
