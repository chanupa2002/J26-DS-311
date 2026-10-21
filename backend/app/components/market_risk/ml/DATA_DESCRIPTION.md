# Dataset description: market_risk

WARNING: describe the data here. NEVER paste real records or real values. Column names, types and meanings only.

| Item | Details |
|------|---------|
| Dataset name | **Deployed models (version 2.0):** the team's cleaned monitoring data (one CSV), joined to `SUSTAIN_Model_Training_Combined_Dataset.xlsx` for the market (`Category_Month_Table`) and macro features and the grant date. **Version 1.0 (replaced 2026-10-21):** `SUSTAIN_Model_Training_Combined_Dataset.xlsx` only (main sheet `Training_Table_HH_Month`, plus `Column_Dictionary` and documentation sheets) |
| Source | SUSTAIN livelihood monitoring forms (monthly household visits), left-joined to category × month market features and national macro indicators from an upstream notebook |
| Owner / who has access | Project team under the NDA; supervisor controls access |
| Approx. number of rows and time period | **Version 2.0:** cleaned data, 649 household-month rows. 99 rows have no household key (not used) and 550 keyed rows form the **SYNTHETIC panel (70 households, 9 categories)**, 2026-01..2026-09. These are the earlier 448 synthetic rows (58 households) plus 102 rows in Beauty & Wellness and Transport & Logistics. **Version 1.0:** 547 rows, 99 real (2026-01..2026-03) and 448 synthetic |
| Target variable(s) | `Risk_Label_3M`, `Risk_Label_6M`: household risk class (Low/Medium/High) at calendar month t+3 / t+6, from SUSTAIN-HH-Risk-Rule v1.0 (provisional). Eligible rows, all synthetic: version 2.0 3M = 269, 6M = 138 (version 1.0: 219, 116) |
| Where the real data is stored (private location, NOT in this repo) | Private Google Drive of the project team, plus a private local folder outside the repo for retraining (paths passed in the `SUSTAIN_CLEANED` / `SUSTAIN_COMBINED` environment variables). Never in this repo |
| Notebook(s) and scripts that use it | `notebooks/SUSTAIN_3M_6M_Risk_Prediction.ipynb` (Google Colab, version 1.0); `ml/training/train_from_cleaned.py` (version 2.0) |

## Columns

### Source column groups (raw table)
| Column group | Type | Meaning | Allowed values or format (no real data) |
|--------|------|---------|------------------------------------------|
| Monitoring-form answers (sections 1–6, e.g. `1.6` gender, `1.7` age, `1.10` district, `3.2` primary activity, `3.4` hours, `3.5` records, `3.6` borrowing, `3.10.x` shocks, `4.4` saving, `6.1` grant status) | text / number | Answers from the monthly visit form | Fixed answer options (Yes/No, ordinal bands, district names, livelihood categories); age in years |
| `T_*` derived outcomes (8 columns, e.g. `T_Business_Not_Running`, `T_No_Profit_Last_Month`, `T_Not_Progressing_Well`, `T_Market_Stress_Any`) | 0/1, blank | Household outcome signals built from the form answers | 1 = signal present, 0 = absent, blank = unanswered |
| `Primary_*`, `Category_*` market features | number / ordinal | Category × month market-price pressure and volatility, and their tiers, at t and t−1 | Continuous index values; tiers Low/Medium/High as ordinals |
| `Macro_*` | number | National macro indicators at t and t−1: CCPI YoY inflation, CCPI food index, auto diesel price | Continuous |
| Keys and identifiers (`Month`, `monitoring_period`, `Category_Key`, `Row_Basis`, `household_key`, `_uuid`, visit and grant dates) | text / date | Month, category key, real/synthetic flag, household key (synthetic rows only), submission IDs | `YYYY-MM`; `Row_Basis` starts with `REAL` for real rows |

### Model input features (53, used by the API)
| Column | Type | Meaning | Allowed values or format (no real data) |
|--------|------|---------|------------------------------------------|
| `F_*_t` household signals (8) | numeric | `T_*` signals at visit t | 0/1 or null |
| `F_Risk_Ord_t`, `F_Risk_Signal_Count_t`, `F_Risk_Unknown_t` | numeric | Current risk class by rule v1.0; count of positive and of blank signals | 0/1/2; 0–3 |
| `F_Hours_Ord_t`, `F_Records_Ord_t`, `F_Grant_Status_Ord_t` | numeric | Ordinal codings of form answers 3.4 / 3.5 / 6.1 | 1–3; 0–3; 0–3 |
| Yes/No conditions (`F_Borrowed_t`, `F_Saved_t`, `F_Cyclone_Affected_t`, `F_Female_Head`, `F_Asset_Lost_t`, `F_Storage_Transport_Issue_t`, `F_Machinery_Issue_t`, `F_Natural_Disaster_t`) | numeric | Operating conditions at t | Yes=1, No=0, else null |
| `F_Age`, `F_Female_Participant` | numeric | Participant age; gender | years; Female=1, Male=0 |
| History (`F_Prev_*`, `F_Months_Since_Prev_Visit`, `F_Risk_Change_vs_Prev`, `F_Tenure_Months`, `F_N_Prior_Visits`, `F_*_Window`, `F_Months_Since_Grant`) | numeric | Same household's earlier visits only (windows [t−2, t] and [t−5, t]) | counts, rates 0–1, months |
| Market (`F_Mkt_*`) and macro (`F_Macro_*`) | numeric | Category market pressure/volatility and national macro indicators at t, and t vs t−1 changes | continuous; `F_Mkt_Evidence_Missing` 0/1 |
| `F_Category` | categorical | Programme livelihood category | 9 trained levels, including Beauty & Wellness and Transport & Logistics (see `GET /api/risk/model-info`) |
| `F_District` | categorical | Participant district | 4 trained levels (see `GET /api/risk/model-info`) |

The full list with descriptions is in `ml/models/<horizon>/metadata.json` (`feature_names_in_order`) and is served by `GET /api/risk/model-info`.

## Cleaning and preprocessing summary
- Answer text normalised (apostrophes, whitespace). District stripped and title-cased. `Category_Key` mapped to programme categories (Fisheries/Miscellaneous → Other; Beauty and Wellness and Transport & Logistics are their own levels; blank → Unassigned).
- `T_*` outcome columns rebuilt from the raw answers and matched exactly (0 mismatches).
- Household risk class at each visit from rule v1.0. Targets = class at exact calendar month t+3 / t+6 (no tolerance).
- Features use only visit t and earlier visits of the same household. A leakage check (features recomputed on data cut off at each month) found 0 differences.
- Model pipeline: numeric median imputation (with missing indicators) + scaling; categorical constant imputation + one-hot (unknown → all-zero).

## Known issues
- **No real household can be followed over time**: real rows have no persistent household ID, so no real 3M/6M outcome exists. Models are trained and tested on synthetic rows only. The source says synthetic rows must not be used as evidence.
- The target rule is new and not validated by experts. The market-tier thresholds are only partly verified.
- Small samples: 3M train/test 127/49, 6M 91/47 (version 1.0: 102/39, 77/39). The 6M test split could not be embargoed (optimistic).
- The 102 Beauty & Wellness and Transport & Logistics rows have no category market evidence and no grant date.
- Version 2.0 was promoted for category coverage although it catches fewer High cases: walk-forward High recall fell from 0.397 to 0.307 (3M) and from 0.876 to 0.771 (6M). See `RETRAIN_REPORT.md`.
- Coverage gaps: Garment/Handicrafts are combined. "Other" is mixed. Only 4 districts.
- Many market features are missing for some categories and months (`F_Mkt_Evidence_Missing`).
