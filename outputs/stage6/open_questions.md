# Stage 6 open questions

Research output - not an eligibility determination

- Confirm `MIN_CELL=10` with the researcher; it is applied to every subgroup statistic.
- B3 thresholds 0.4, 0.5 and 0.6 are researcher-judgement settings, not an official MPI. The primary reporting threshold is 0.5; 0.4 and 0.6 are sensitivity views.
- B3 uses the four Stage 4 domains (housing, economic, food, demographic). The newer Stage 4b health, financial-resilience and exposure indicators do not have a single approved mapping into these four legacy domains; they are not silently assigned in B3. B1 includes every published `mu_*` field, including `mu_shock`, as specified by the task.
- The perturbation applies one Dirichlet(20 x equal weights) draw to each exposed BN node-parent weight vector. There is no separately named “domain weight” field in the engine; this interpretation perturbs each domain aggregation weight vector exposed by the BN configuration.
- `pc_cons` is documented as `total_month / hh_size`; exact upstream consumption components are not fully documented. `label_high_vuln` is the weighted bottom quintile of `pc_cons`. Their association with economic inputs may be circular; results remain isolated and descriptive.
- The `sector` values are reported by stored code because current source documentation does not establish urban/rural/estate labels.
- Stage 5 stores no percentile or interval. Percentile is derived from its expected score; perturbation intervals are new Stage 6 rank stability summaries, not uncertainty intervals from a calibrated model.
- PCA is complete-case only and may cover fewer households than other methods; missing memberships are not imputed.
