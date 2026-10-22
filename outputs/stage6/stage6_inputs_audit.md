# Stage 6 inputs audit

Research output - not an eligibility determination

## Frozen inputs and alignment

- Stage 5 score file: `component1_audit/outputs/stage5/bn_scores_v0_2_interim.csv`.
- Stage 4b memberships: `component1_audit/outputs/stage4b/fuzzy_scores_v0_2.csv`.
- Both tables contain 6,847 rows, unique nonmissing household keys, and identical key sets. Stage 3 and Stage 3b modelling inputs plus prepared context also passed one-to-one key-set alignment.
- Stage 5 columns include expected vulnerability (`bn_expected_vulnerability`), posterior high probability (`bn_p_high`), and normalized posterior entropy (`bn_uncertainty_entropy`). It does not store a rank percentile or a rank interval. The percentile is derived from the saved expected scores; rank intervals are calculated in Stage 6 perturbations.
- Stage 5 runner: `component1_audit/outputs/stage5/build_stage5.py` calls `bn_v0_1.score(network, config_v02_interim())` over the full table. The single-record interface is `bn_v0_1.score_record(record, cfg)`. A 200-call synthetic one-record benchmark averaged 0.010609 seconds per call on this machine; this is an engine microbenchmark, not a full-pipeline or household-specific timing.
- Stage 5 summary describes 6,847 baseline households. It reports expected vulnerability, P(high), entropy, and aggregate sensitivity outputs. No interval is stored in the Stage 5 score file.

## Proxy documentation and circularity

- Existing data-quality and proposed-resolution notes document `pc_cons` as `total_month / hh_size`; the component construction upstream of `total_month` is not fully reproducible from available source documentation.
- `label_high_vuln` is documented as a household-weighted bottom-quintile indicator of `pc_cons`, with approximate weighted prevalence 0.20. It is a descriptive sensitivity proxy.
- Stage 3, Stage 4b and Stage 5 explicitly exclude both proxy fields from the model-input/scoring tables. Exact overlap between proxy construction components and income/asset features is not fully documented; consumption and economic-capacity features may be related, so proxy agreement is potentially circular and is kept in its own folder.

## Subgroup fields

- Prepared context provides province code, district code, `sector`, and `hhweight`. The codebook also confirms `hhweight` exists.
- Stage 5 scores themselves contain `hhcode` and network scores; subgroup fields are joined from the prepared context for aggregate analysis only. `sector` is reported by its stored code; urban/rural/estate meanings are not assumed.
- Household identifiers are used only in the ignored local score output and are not printed in logs, reports, or figures.

## Input columns

- Stage 5: research_label, bn_living_conditions_low, bn_living_conditions_medium, bn_living_conditions_high, bn_sensitivity_low, bn_sensitivity_medium, bn_sensitivity_high, bn_adaptive_capacity_low, bn_adaptive_capacity_medium, bn_adaptive_capacity_high, bn_vulnerability_low, bn_vulnerability_medium, bn_vulnerability_high, bn_p_high, bn_expected_vulnerability, bn_uncertainty_entropy, bn_leaves_observed, bn_leaves_total, bn_model_version, bn_sigma, bn_blend
- Stage 4b includes 97 columns, including the `mu_*` membership fields and `dom_*` coverage fields used by the frozen framework and baselines.
