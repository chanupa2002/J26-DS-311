# market_risk: retrain report (cleaned data)

Generated 2026-10-21T16:12:20 by `ml/training/train_from_cleaned.py`. Aggregates only: no rows, IDs or data values.

> **Data basis: SYNTHETIC panel (70 households, 9 categories). Not real-world evidence.** Candidate models are NOT_READY and are stored outside the repo. The deployed models in `ml/models/` were not changed.
>
> **Update 2026-10-21:** the deployed-settings candidate (section 3) was later promoted to `ml/models/`, for coverage, with the trade-off accepted. See section 5. Sections 1–4 are unchanged.

## Input checks

| Check | Result |
|---|---|
| cleaned_rows | 649 |
| keyed_rows_used | 550 |
| unkeyed_rows_excluded | 99 |
| households | 70 |
| categories | 9 |
| rows_matched_to_original_panel | 448 |
| original_panel_rows | 448 |
| new_category_rows | 102 |
| t_signal_mismatches_vs_original | {"T_Business_Not_Running": 0, "T_No_Profit_Last_Month": 0, "T_Not_Progressing_Well": 0, "T_Revenue_Lowest_Band": 0, "T_Sales_Below_Expected": 0, "T_High_Input_Cost": 0, "T_Inputs_Unavailable": 0, "T_Market_Stress_Any": 0} |
| visit_date_agreement_vs_original | 1.000 |
| grant_dates_available | 166 |
| rows_without_market_evidence | 254 |
| leakage_truncation_test | 0 differences in 28050 values |
| eligible_3M_448_rows | 219 {'Low': 83, 'Medium': 59, 'High': 77} |
| eligible_6M_448_rows | 116 {'Low': 32, 'Medium': 26, 'High': 58} |
| eligible_3M_550_rows | 269 {'Low': 101, 'Medium': 76, 'High': 92} |
| eligible_6M_550_rows | 138 {'Low': 37, 'Medium': 33, 'High': 68} |

## 1. Reproduction gate (448 original synthetic rows)

| Horizon | Train/test | Training statistics = deployed pipeline | Test Macro-F1, deployed config | Test High recall | Section 29 walk-forward RF / persistence | Result |
|---|---|---|---|---|---|---|
| 3M | 102/39 (expected 102/39) | yes | 0.3026 (expected 0.3026) | 0.5600 (expected 0.56) | 0.356 / 0.295 (expected 0.356 / 0.295) | PASS |
| 6M | 77/39 (expected 77/39) | yes | 0.4302 (expected 0.4302) | 0.8800 (expected 0.88) | 0.431 / 0.179 (expected 0.431 / 0.179) | PASS |

**Gate: PASS**. Required: the same split sizes; training statistics equal to the deployed pipeline's (imputer medians, scaler means/scales, missing indicators, one-hot levels); test Macro-F1 and High recall of the deployed configuration within 5e-05 of `ml/models/*/metadata.json`; and the notebook section 29 walk-forward means reproduced.

Grid search on this machine (reported, not gated):

| Horizon | Grid-selected RF params here | Notebook (Colab) params | Same | Test Macro-F1 with params selected here |
|---|---|---|---|---|
| 3M | {"max_depth": 3, "min_samples_leaf": 5} | {"max_depth": 3, "min_samples_leaf": 10} | no | 0.313 |
| 6M | {"max_depth": 3, "min_samples_leaf": 1} | {"max_depth": 3, "min_samples_leaf": 10} | no | 0.461 |

The grid search does not reproduce the Colab choice exactly. The data are identical, but about 10 of 300 trees choose differently between exactly tied, duplicate columns (for example the missing flags of `F_Mkt_Volatility_t` and `F_Mkt_Volatility_Tier_Ord_t`, or diesel price and diesel change), which is floating-point and platform dependent. On the small folds this re-orders near-tied CV scores. Hyperparameter choice is therefore unstable at this sample size.

Notebook section 29 walk-forward on the same 448 rows (notebook: 3M RF 0.356 vs persistence 0.295, High recall 0.44 vs 0.19; 6M RF 0.431 vs 0.179):

| Horizon | Model | Folds | Macro_F1_mean | High_Recall_mean |
|---|---|---|---|---|
| 3M | Persistence baseline | 5 | 0.295 | 0.191 |
| 3M | Random Forest (current) | 5 | 0.356 | 0.439 |
| 6M | Persistence baseline | 2 | 0.179 | 0.156 |
| 6M | Random Forest (current) | 2 | 0.431 | 0.912 |

## 2. Candidate: grid search, as in the notebook (550 keyed synthetic rows)

| Horizon | Design | Train_n | Test_n | Train classes | Test classes |
|---|---|---|---|---|---|
| 3M | Embargoed: train prediction months whose target month <= test prediction month; test = prediction month 2026-06 | 127 | 49 | {"Low": 63, "Medium": 41, "High": 23} | {"Low": 9, "Medium": 10, "High": 30} |
| 6M | NO EMBARGO POSSIBLE (embargoed train would have 0 rows): train = all earlier prediction months; test = prediction month 2026-03; train targets overlap test period -> optimistic | 91 | 47 | {"Low": 29, "Medium": 24, "High": 38} | {"Low": 8, "Medium": 9, "High": 30} |

2.1 Final test month (all candidates as in the notebook; **only the Random Forest is saved**):

| Horizon | Model | Params | CV Macro-F1 (train) | Test Macro-F1 | Test High recall | Test High precision | Selected by CV | Saved |
|---|---|---|---|---|---|---|---|---|
| 3M | Baseline: majority class | class=Low | 0.220 | 0.103 | 0.000 | 0.000 | False | False |
| 3M | Baseline: persistence | - | 0.293 | 0.366 | 0.267 | 0.727 | False | False |
| 3M | LogisticRegression | {"C": 0.01} | 0.447 | 0.251 | 0.967 | 0.617 | False | False |
| 3M | RandomForest | {"max_depth": null, "min_samples_leaf": 5} | 0.448 | 0.420 | 0.433 | 0.650 | True | True |
| 6M | Baseline: majority class | class=High | 0.193 | 0.260 | 1.000 | 0.638 | False | False |
| 6M | Baseline: persistence | - | 0.167 | 0.174 | 0.267 | 0.533 | False | False |
| 6M | LogisticRegression | {"C": 0.1} | 0.500 | 0.403 | 0.867 | 0.722 | False | False |
| 6M | RandomForest | {"max_depth": 3, "min_samples_leaf": 1} | 0.513 | 0.341 | 0.667 | 0.714 | True | True |

2.2 Walk-forward, current vs this candidate (mean over test months). Current = the deployed RF settings retrained per fold on the original-category rows only; candidate = this candidate's RF settings retrained per fold on all rows; both are scored on the same test months.

| Horizon | Scope | Model | Folds | Macro_F1_mean | High_Recall_mean |
|---|---|---|---|---|---|
| 3M | all test rows | Persistence baseline | 5 | 0.292 | 0.207 |
| 3M | all test rows | Current RF (original 448-row panel) | 5 | 0.350 | 0.397 |
| 3M | all test rows | Candidate RF (550-row panel) | 5 | 0.347 | 0.301 |
| 3M | original-category test rows | Persistence baseline | 5 | 0.295 | 0.191 |
| 3M | original-category test rows | Current RF (original 448-row panel) | 5 | 0.356 | 0.439 |
| 3M | original-category test rows | Candidate RF (550-row panel) | 5 | 0.356 | 0.318 |
| 6M | all test rows | Persistence baseline | 2 | 0.193 | 0.181 |
| 6M | all test rows | Current RF (original 448-row panel) | 2 | 0.422 | 0.876 |
| 6M | all test rows | Candidate RF (550-row panel) | 2 | 0.382 | 0.667 |
| 6M | original-category test rows | Persistence baseline | 2 | 0.179 | 0.156 |
| 6M | original-category test rows | Current RF (original 448-row panel) | 2 | 0.431 | 0.912 |
| 6M | original-category test rows | Candidate RF (550-row panel) | 2 | 0.404 | 0.721 |

Per fold (all test rows):

| Horizon | Test_month | Design | Model | Train_n_current | Train_n_candidate | Test_n | Macro_F1 | High_Recall |
|---|---|---|---|---|---|---|---|---|
| 3M | 2026-02 | no embargo (optimistic) | Persistence baseline | 35 | 43 | 46 | 0.308 | 0.250 |
| 3M | 2026-02 | no embargo (optimistic) | Current RF (original 448-row panel) | 35 | 43 | 46 | 0.456 | 0.500 |
| 3M | 2026-02 | no embargo (optimistic) | Candidate RF (550-row panel) | 35 | 43 | 46 | 0.404 | 0.500 |
| 3M | 2026-03 | no embargo (optimistic) | Persistence baseline | 71 | 89 | 38 | 0.248 | 0.250 |
| 3M | 2026-03 | no embargo (optimistic) | Current RF (original 448-row panel) | 71 | 89 | 38 | 0.342 | 0.333 |
| 3M | 2026-03 | no embargo (optimistic) | Candidate RF (550-row panel) | 71 | 89 | 38 | 0.291 | 0.083 |
| 3M | 2026-04 | embargoed | Persistence baseline | 35 | 43 | 45 | 0.363 | 0.176 |
| 3M | 2026-04 | embargoed | Current RF (original 448-row panel) | 35 | 43 | 45 | 0.371 | 0.471 |
| 3M | 2026-04 | embargoed | Candidate RF (550-row panel) | 35 | 43 | 45 | 0.354 | 0.353 |
| 3M | 2026-05 | embargoed | Persistence baseline | 71 | 89 | 48 | 0.178 | 0.091 |
| 3M | 2026-05 | embargoed | Current RF (original 448-row panel) | 71 | 89 | 48 | 0.255 | 0.182 |
| 3M | 2026-05 | embargoed | Candidate RF (550-row panel) | 71 | 89 | 48 | 0.264 | 0.136 |
| 3M | 2026-06 | embargoed | Persistence baseline | 102 | 127 | 49 | 0.366 | 0.267 |
| 3M | 2026-06 | embargoed | Current RF (original 448-row panel) | 102 | 127 | 49 | 0.324 | 0.500 |
| 3M | 2026-06 | embargoed | Candidate RF (550-row panel) | 102 | 127 | 49 | 0.420 | 0.433 |
| 6M | 2026-02 | no embargo (optimistic) | Persistence baseline | 37 | 44 | 47 | 0.212 | 0.095 |
| 6M | 2026-02 | no embargo (optimistic) | Current RF (original 448-row panel) | 37 | 44 | 47 | 0.455 | 0.952 |
| 6M | 2026-02 | no embargo (optimistic) | Candidate RF (550-row panel) | 37 | 44 | 47 | 0.422 | 0.667 |
| 6M | 2026-03 | no embargo (optimistic) | Persistence baseline | 77 | 91 | 47 | 0.174 | 0.267 |
| 6M | 2026-03 | no embargo (optimistic) | Current RF (original 448-row panel) | 77 | 91 | 47 | 0.389 | 0.800 |
| 6M | 2026-03 | no embargo (optimistic) | Candidate RF (550-row panel) | 77 | 91 | 47 | 0.341 | 0.667 |

2.3 Promotion bar:

| Horizon | Current Macro-F1 | Candidate Macro-F1 | Macro-F1 within 0.02 | Current High recall | Candidate High recall | High recall not lower |
|---|---|---|---|---|---|---|
| 3M | 0.350 | 0.347 | yes | 0.397 | 0.301 | no |
| 6M | 0.422 | 0.382 | no | 0.876 | 0.667 | no |

**Promotion bar (model metrics): NOT MET**. Rule: gate passes; candidate walk-forward Macro-F1 >= current - 0.02; candidate High recall >= current (all test rows, mean over folds). All tests must also pass; that is checked separately with pytest.

2.4 Does F_Months_Since_Grant's missing flag act as a proxy for the new categories?

**3M** (candidate RF, 127 training rows, 96 model columns)

- Missing rate: new categories 1.000, original categories 0.480; share of missing rows that are new-category: 0.338.
- Permutation importance on the test month (drop in Macro-F1, 50 repeats): F_Months_Since_Grant -0.0011 ± 0.0098 (rank 36 of 53); F_Category -0.0003 ± 0.0058 (rank 33).
- SHAP (training rows), missing indicator: mean |SHAP| 0.0111 (rank 32 of 96); mean contribution to P(High): new categories -0.0056, original categories -0.0005.
- SHAP, grant-months value column: mean |SHAP| 0.0104 (rank 33).
- SHAP, all F_Category one-hot columns together: mean |SHAP| 0.0164.
- **Verdict: not a strong proxy in this model: the flag is fully confounded with the new categories, but it is outside the top-10 SHAP columns and its permutation importance is within noise**

**6M** (candidate RF, 91 training rows, 96 model columns)

- Missing rate: new categories 1.000, original categories 0.429; share of missing rows that are new-category: 0.298.
- Permutation importance on the test month (drop in Macro-F1, 50 repeats): F_Months_Since_Grant -0.0389 ± 0.0392 (rank 45 of 53); F_Category -0.0233 ± 0.0140 (rank 38).
- SHAP (training rows), missing indicator: mean |SHAP| 0.0048 (rank 42 of 96); mean contribution to P(High): new categories -0.0020, original categories +0.0007.
- SHAP, grant-months value column: mean |SHAP| 0.0160 (rank 13).
- SHAP, all F_Category one-hot columns together: mean |SHAP| 0.0216.
- **Verdict: not a strong proxy in this model: the flag is fully confounded with the new categories, but it is outside the top-10 SHAP columns and its permutation importance is within noise**

2.5 Files (outside the repo):

- `3M`: `$SUSTAIN_CANDIDATE_OUT/3M/` (model.joblib, metadata.json, feature_schema.json)
- `6M`: `$SUSTAIN_CANDIDATE_OUT/6M/` (model.joblib, metadata.json, feature_schema.json)

## 3. Candidate: deployed settings fixed (max_depth 3, min_samples_leaf 10), no grid search (550 keyed synthetic rows)

| Horizon | Design | Train_n | Test_n | Train classes | Test classes |
|---|---|---|---|---|---|
| 3M | Embargoed: train prediction months whose target month <= test prediction month; test = prediction month 2026-06 | 127 | 49 | {"Low": 63, "Medium": 41, "High": 23} | {"Low": 9, "Medium": 10, "High": 30} |
| 6M | NO EMBARGO POSSIBLE (embargoed train would have 0 rows): train = all earlier prediction months; test = prediction month 2026-03; train targets overlap test period -> optimistic | 91 | 47 | {"Low": 29, "Medium": 24, "High": 38} | {"Low": 8, "Medium": 9, "High": 30} |

3.1 Final test month (**only the Random Forest is saved**):

| Horizon | Model | Params | CV Macro-F1 (train) | Test Macro-F1 | Test High recall | Test High precision | Selected by CV | Saved |
|---|---|---|---|---|---|---|---|---|
| 3M | Baseline: majority class | class=Low | - | 0.103 | 0.000 | 0.000 | - | False |
| 3M | Baseline: persistence | - | - | 0.366 | 0.267 | 0.727 | - | False |
| 3M | RandomForest | {"max_depth": 3, "min_samples_leaf": 10} | - | 0.421 | 0.633 | 0.655 | - | True |
| 6M | Baseline: majority class | class=High | - | 0.260 | 1.000 | 0.638 | - | False |
| 6M | Baseline: persistence | - | - | 0.174 | 0.267 | 0.533 | - | False |
| 6M | RandomForest | {"max_depth": 3, "min_samples_leaf": 10} | - | 0.402 | 0.733 | 0.759 | - | True |

3.2 Walk-forward, current vs this candidate (mean over test months). Current = the deployed RF settings retrained per fold on the original-category rows only; candidate = this candidate's RF settings retrained per fold on all rows; both are scored on the same test months.

| Horizon | Scope | Model | Folds | Macro_F1_mean | High_Recall_mean |
|---|---|---|---|---|---|
| 3M | all test rows | Persistence baseline | 5 | 0.292 | 0.207 |
| 3M | all test rows | Current RF (original 448-row panel) | 5 | 0.350 | 0.397 |
| 3M | all test rows | Candidate RF (550-row panel) | 5 | 0.331 | 0.307 |
| 3M | original-category test rows | Persistence baseline | 5 | 0.295 | 0.191 |
| 3M | original-category test rows | Current RF (original 448-row panel) | 5 | 0.356 | 0.439 |
| 3M | original-category test rows | Candidate RF (550-row panel) | 5 | 0.336 | 0.334 |
| 6M | all test rows | Persistence baseline | 2 | 0.193 | 0.181 |
| 6M | all test rows | Current RF (original 448-row panel) | 2 | 0.422 | 0.876 |
| 6M | all test rows | Candidate RF (550-row panel) | 2 | 0.429 | 0.771 |
| 6M | original-category test rows | Persistence baseline | 2 | 0.179 | 0.156 |
| 6M | original-category test rows | Current RF (original 448-row panel) | 2 | 0.431 | 0.912 |
| 6M | original-category test rows | Candidate RF (550-row panel) | 2 | 0.443 | 0.789 |

Per fold (all test rows):

| Horizon | Test_month | Design | Model | Train_n_current | Train_n_candidate | Test_n | Macro_F1 | High_Recall |
|---|---|---|---|---|---|---|---|---|
| 3M | 2026-02 | no embargo (optimistic) | Persistence baseline | 35 | 43 | 46 | 0.308 | 0.250 |
| 3M | 2026-02 | no embargo (optimistic) | Current RF (original 448-row panel) | 35 | 43 | 46 | 0.456 | 0.500 |
| 3M | 2026-02 | no embargo (optimistic) | Candidate RF (550-row panel) | 35 | 43 | 46 | 0.306 | 0.000 |
| 3M | 2026-03 | no embargo (optimistic) | Persistence baseline | 71 | 89 | 38 | 0.248 | 0.250 |
| 3M | 2026-03 | no embargo (optimistic) | Current RF (original 448-row panel) | 71 | 89 | 38 | 0.342 | 0.333 |
| 3M | 2026-03 | no embargo (optimistic) | Candidate RF (550-row panel) | 71 | 89 | 38 | 0.264 | 0.333 |
| 3M | 2026-04 | embargoed | Persistence baseline | 35 | 43 | 45 | 0.363 | 0.176 |
| 3M | 2026-04 | embargoed | Current RF (original 448-row panel) | 35 | 43 | 45 | 0.371 | 0.471 |
| 3M | 2026-04 | embargoed | Candidate RF (550-row panel) | 35 | 43 | 45 | 0.353 | 0.294 |
| 3M | 2026-05 | embargoed | Persistence baseline | 71 | 89 | 48 | 0.178 | 0.091 |
| 3M | 2026-05 | embargoed | Current RF (original 448-row panel) | 71 | 89 | 48 | 0.255 | 0.182 |
| 3M | 2026-05 | embargoed | Candidate RF (550-row panel) | 71 | 89 | 48 | 0.311 | 0.273 |
| 3M | 2026-06 | embargoed | Persistence baseline | 102 | 127 | 49 | 0.366 | 0.267 |
| 3M | 2026-06 | embargoed | Current RF (original 448-row panel) | 102 | 127 | 49 | 0.324 | 0.500 |
| 3M | 2026-06 | embargoed | Candidate RF (550-row panel) | 102 | 127 | 49 | 0.421 | 0.633 |
| 6M | 2026-02 | no embargo (optimistic) | Persistence baseline | 37 | 44 | 47 | 0.212 | 0.095 |
| 6M | 2026-02 | no embargo (optimistic) | Current RF (original 448-row panel) | 37 | 44 | 47 | 0.455 | 0.952 |
| 6M | 2026-02 | no embargo (optimistic) | Candidate RF (550-row panel) | 37 | 44 | 47 | 0.456 | 0.810 |
| 6M | 2026-03 | no embargo (optimistic) | Persistence baseline | 77 | 91 | 47 | 0.174 | 0.267 |
| 6M | 2026-03 | no embargo (optimistic) | Current RF (original 448-row panel) | 77 | 91 | 47 | 0.389 | 0.800 |
| 6M | 2026-03 | no embargo (optimistic) | Candidate RF (550-row panel) | 77 | 91 | 47 | 0.402 | 0.733 |

3.3 Promotion bar:

| Horizon | Current Macro-F1 | Candidate Macro-F1 | Macro-F1 within 0.02 | Current High recall | Candidate High recall | High recall not lower |
|---|---|---|---|---|---|---|
| 3M | 0.350 | 0.331 | yes | 0.397 | 0.307 | no |
| 6M | 0.422 | 0.429 | yes | 0.876 | 0.771 | no |

**Promotion bar (model metrics): NOT MET**. Rule: gate passes; candidate walk-forward Macro-F1 >= current - 0.02; candidate High recall >= current (all test rows, mean over folds). All tests must also pass; that is checked separately with pytest.

3.4 Does F_Months_Since_Grant's missing flag act as a proxy for the new categories?

**3M** (candidate RF, 127 training rows, 96 model columns)

- Missing rate: new categories 1.000, original categories 0.480; share of missing rows that are new-category: 0.338.
- Permutation importance on the test month (drop in Macro-F1, 50 repeats): F_Months_Since_Grant +0.0072 ± 0.0068 (rank 29 of 53); F_Category +0.0051 ± 0.0126 (rank 30).
- SHAP (training rows), missing indicator: mean |SHAP| 0.0077 (rank 28 of 96); mean contribution to P(High): new categories -0.0032, original categories +0.0000.
- SHAP, grant-months value column: mean |SHAP| 0.0036 (rank 43).
- SHAP, all F_Category one-hot columns together: mean |SHAP| 0.0029.
- **Verdict: not a strong proxy in this model: the flag is fully confounded with the new categories, but it is outside the top-10 SHAP columns and its permutation importance is within noise**

**6M** (candidate RF, 91 training rows, 96 model columns)

- Missing rate: new categories 1.000, original categories 0.429; share of missing rows that are new-category: 0.298.
- Permutation importance on the test month (drop in Macro-F1, 50 repeats): F_Months_Since_Grant +0.0077 ± 0.0063 (rank 9 of 53); F_Category +0.0000 ± 0.0000 (rank 27).
- SHAP (training rows), missing indicator: mean |SHAP| 0.0058 (rank 28 of 96); mean contribution to P(High): new categories -0.0026, original categories +0.0005.
- SHAP, grant-months value column: mean |SHAP| 0.0059 (rank 27).
- SHAP, all F_Category one-hot columns together: mean |SHAP| 0.0022.
- **Verdict: not a strong proxy in this model: the flag is fully confounded with the new categories, but it is outside the top-10 SHAP columns and its permutation importance is within noise**

3.5 Files (outside the repo):

- `3M`: `$SUSTAIN_CANDIDATE_OUT/deployed_settings/3M/` (model.joblib, metadata.json, feature_schema.json)
- `6M`: `$SUSTAIN_CANDIDATE_OUT/deployed_settings/6M/` (model.joblib, metadata.json, feature_schema.json)

## 4. Data or settings? (walk-forward, mean over test months)

Data effect = candidate with the deployed settings minus current (only the training data differ). Settings effect = grid-search candidate minus candidate with the deployed settings (only the RF settings differ). The two add up to the total change from current to the grid candidate.

| Horizon | Scope | Metric | Current | Candidate, deployed settings | Candidate, grid settings | Data effect (same settings - current) | Settings effect (grid - same settings) |
|---|---|---|---|---|---|---|---|
| 3M | all test rows | Macro-F1 | 0.350 | 0.331 | 0.347 | -0.018 | 0.015 |
| 3M | all test rows | High recall | 0.397 | 0.307 | 0.301 | -0.090 | -0.006 |
| 3M | original-category test rows | Macro-F1 | 0.356 | 0.336 | 0.356 | -0.019 | 0.019 |
| 3M | original-category test rows | High recall | 0.439 | 0.334 | 0.318 | -0.105 | -0.016 |
| 6M | all test rows | Macro-F1 | 0.422 | 0.429 | 0.382 | 0.007 | -0.048 |
| 6M | all test rows | High recall | 0.876 | 0.771 | 0.667 | -0.105 | -0.105 |
| 6M | original-category test rows | Macro-F1 | 0.431 | 0.443 | 0.404 | 0.012 | -0.039 |
| 6M | original-category test rows | High recall | 0.912 | 0.789 | 0.721 | -0.123 | -0.068 |

**Conclusion (all test rows; effects under 0.01 count as negligible):**

- 3M Macro-F1: total change -0.003 (data -0.018, settings +0.015) -> almost no net change: the data and settings effects roughly cancel.
- 3M High recall: total change -0.096 (data -0.090, settings -0.006) -> mainly the **data**.
- 6M Macro-F1: total change -0.041 (data +0.007, settings -0.048) -> mainly the **settings**.
- 6M High recall: total change -0.210 (data -0.105, settings -0.105) -> both the data and the settings, about equally.
- Promotion bar with the deployed settings: **NOT MET**; with grid settings: **NOT MET**.

## 5. Decision

**Decision (owner, 2026-10-21): promoted for coverage, trade-off accepted.** The candidate with the deployed settings (RF `max_depth` 3, `min_samples_leaf` 10, seed 42, no grid search; SYNTHETIC panel, 70 households, 9 categories) now replaces the models in `ml/models/3M` and `ml/models/6M` as version 2.0, still **NOT_READY**.

- **Reason:** consistency with the team's cleaned data, and coverage of all 9 livelihood categories in the proposal (version 1.0 knew 7).
- **Trade-off accepted.** The promotion bar above was **not met**, and that result stands. Walk-forward means over all test rows:

| Horizon | Metric | Previous model (1.0) | Promoted model (2.0) | Change |
|---|---|---|---|---|
| 3M | Macro-F1 | 0.350 | 0.331 | −0.019 |
| 3M | High recall | 0.397 | 0.307 | −0.090 |
| 6M | Macro-F1 | 0.422 | 0.429 | +0.007 |
| 6M | High recall | 0.876 | 0.771 | −0.105 |

- **What it means:** the promoted model misses more households that later turn High, on both horizons. Most of this drop comes from the data (see the analysis above), not from the settings.
- **What was copied:** only `model.joblib`, `metadata.json` and `feature_schema.json` per horizon, with no CSV or data rows. `metadata.json` records the decision and these numbers under `promotion`, and in `deployment_reason`.
- **The grid-search candidate was not promoted**: its 6M Macro-F1 and High recall are lower still.

_This section was added by hand at promotion. Rerunning `train_from_cleaned.py --report` regenerates sections 1–4 and drops it._
