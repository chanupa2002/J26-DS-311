# SUSTAIN 3M/6M Risk Prediction — Methodology and Results Summary

Generated 2026-10-20 04:23 from `SUSTAIN_Model_Training_Combined_Dataset.xlsx` (SHA-256 9732f43f0e7a…).

## Bottom line
The full pipeline runs end to end and passes its leakage checks, but **the dataset cannot support real 3- or 6-month prediction**: the 99 real rows cover Jan–Mar 2026 and have no persistent household ID, so no real future outcome can be matched. All models were trained and tested on the 448 synthetic rows (58 households, Jan–Sep 2026), which the source itself says must not be used as evidence. Both saved models are flagged **NOT_READY**.

## What was verified
- The eight `T_*` outcome columns rebuild exactly from the raw form answers (0 mismatches).
- No household-level Low/Medium/High label exists. The existing Low/Medium/High columns are category × month **market tiers**. Their adverse-direction rule is verified (pressure = −Δprice for output-price categories, +Δprice for Construction's input cost). Their category-specific cut-offs are only partly verified, and the rule that aggregates them to the category tier is unknown.
- Feature leakage: features recomputed on data cut off at each month match the full-data features exactly (27897 values, 0 differences).

## Targets
- `SUSTAIN-HH-Risk-Rule v1.0 (provisional, requires expert validation)`: High = business not running or ≥2 of {no profit, not progressing, market stress}; Medium = 1; Low = 0; Unassigned if blanks leave the class undetermined.
- Exact calendar-month matching (t+3, t+6). Eligible rows: 3M = 219, 6M = 116 (all synthetic).
- Sensitivity of the rule to alternative signal sets and thresholds: rule A vs B [3M labels] agreement 0.724; rule A vs C [3M labels] agreement 0.891; rule A vs E [3M labels] agreement 0.827; rule A vs B [6M labels] agreement 0.871; rule A vs C [6M labels] agreement 0.846; rule A vs E [6M labels] agreement 0.788.

## Results (synthetic test month — pipeline verification only)

| Horizon | Split | Selected model | Test macro-F1 [95% CI] | Persistence baseline macro-F1 | Majority baseline macro-F1 | High recall | n train / test |
|---|---|---|---|---|---|---|---|
| 3M | embargoed | RandomForest | 0.303 [0.194, 0.407] | 0.356 | 0.113 | 0.560 | 102 / 39 |
| 6M | no embargo (optimistic) | RandomForest | 0.430 [0.298, 0.530] | 0.157 | 0.260 | 0.880 | 77 / 39 |

Group-aware sensitivity (GroupKFold by household, all months): 3M RandomForest macro-F1 0.416±0.088 vs persistence 0.301; 6M RandomForest macro-F1 0.416±0.136 vs persistence 0.19.

Top permutation-importance features: 3M: F_No_Profit_Last_Month_t, F_Tenure_Months, F_High_Count_6M_Window, F_MarketStress_Rate_3M_Window, F_N_Prior_Visits; 6M: F_NoProfit_Rate_3M_Window, F_Mkt_Pressure_Tier_Ord_t, F_Age, F_Risk_Ord_t, F_Risk_Signal_Count_t.

## What is needed before deployment
1. Real monitoring data with a stable household/project ID over ≥12 months (≥6 months beyond the first prediction date for 6M).
2. Expert validation of the household risk rule (and of the market-tier thresholds and the v2 notebook).
3. Data for Transport & Logistics and Beauty & Wellness; finer categories for Garment/Handicrafts and 'Other'.
4. An embargoed chronological test on real data in which the model beats the persistence baseline, including High-risk recall.

Outputs: notebook, `SUSTAIN_3M_6M_Risk_Prediction_Outputs.xlsx`, `SUSTAIN_Model_3M/`, `SUSTAIN_Model_6M/`, `sustain_predict.py`, `figures/`.