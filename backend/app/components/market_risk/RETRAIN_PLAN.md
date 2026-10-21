# market_risk: retrain plan from the cleaned monitoring data

Status: **STEP 2 DONE**: implemented and run (see §8 and `RETRAIN_REPORT.md`). Decisions are in §6. Branch: `chamoda-cleaned-retrain` (as stated by the owner; not checked, because no git commands were run).
Goal: retrain the 3M and 6M models from the team's **cleaned** monitoring data, **without touching the deployed models** in `ml/models/`.

> **Data basis for every result in this plan and in the future script: SYNTHETIC panel (70 households, 9 categories).**
> Every row with a `household_id` is synthetic (`is_synthetic=True`). The 99 rows without `household_id` are the real rows. They cannot be followed over time, so they get no 3M/6M target and are **never used for training**. No result may be called real-world performance.

All numbers below come from profiling the two files locally. Only counts and aggregates were printed, never rows. Neither file is, or will be, in the repo.

---

## 0. Inputs and how they link

| File (outside repo) | Env var | What is used |
|---|---|---|
| `~/Documents/sustain_data/monitoring_visits_clean.csv` | `SUSTAIN_CLEANED` | 649 rows × 48 columns (dictionary: `livelihood_planning/data_prep/r_cleaning/reference/monitoring_data_dictionary.csv`). 550 keyed rows (70 households `HH-001..HH-070`, 2026-01..2026-09) + 99 unkeyed (real) rows |
| `~/Documents/sustain_data/combined.xlsx` | `SUSTAIN_COMBINED` | `Training_Table_HH_Month` (547 rows: 448 `SYN-HH-*` synthetic + 99 real; used only for the grant date and for verification), `Category_Month_Table` (140 rows: market + macro by month × category × `Row_Basis`) |

**Link between the files (verified):**
- **The 99 real rows:** `source_uuid` = `_uuid`. They are not used for training.
- **The 448 synthetic rows:** `household_id` `HH-n` ↔ `household_key` `SYN-HH-n` (same number) **and** `monitoring_period` = `Month`. This matches exactly 448 rows, one-to-one. On those rows district, category, participant gender, age, visit date (after converting the Excel serial date), all 8 `T_*` signals and all the codings below agree 100%. The keyed rows' `source_uuid` does **not** match the synthetic `_uuid`, so uuid cannot be the key.
- **The 102 extra keyed rows** are 12 new households (`HH-059..HH-070`) in **BEAUTY AND WELLNESS (52)** and **TRANSPORT & LOGISTICS (50)**. They have no counterpart in `combined.xlsx`.
- **Districts:** keyed rows have the same 4 as before (Badulla, Ampara, Monaragala, Colombo). Ratnapura (27 rows) appears only in real rows.

---

## 1. Column mapping

### 1.1 `T_*` signals (cleaned → notebook §5 `T_RULES`)

| `T_*` signal | From cleaned column | Rule (1 / 0 / blank) | Check on the 448 matched rows |
|---|---|---|---|
| `T_Business_Not_Running` | `business_running` | False→1, True→0 (never blank in cleaned) | 0 mismatches |
| `T_No_Profit_Last_Month` | `profit` | False→1, True→0, NA→blank | 0 mismatches (37 blank in both) |
| `T_Not_Progressing_Well` | `coach_progressing` | False→1, True→0, NA→blank | 0 mismatches |
| `T_Revenue_Lowest_Band` | `revenue_band` | `"LKR 0-10,000"`→1, other bands→0, NA→blank | 0 mismatches |
| `T_Sales_Below_Expected` | `problem_sales_low` | True→1, False→0, NA→blank | 0 mismatches |
| `T_High_Input_Cost` | `problem_input_cost` | same | 0 mismatches |
| `T_Inputs_Unavailable` | `problem_input_unavailable` | same | 0 mismatches |
| `T_Market_Stress_Any` | the three above | 1 if any = 1; 0 if all three = 0; else blank | 0 mismatches (140 blank in both) |

The current class at each visit comes from rule v1.0 variant A (the notebook's `risk_rule`, the same rule as `services.identify_current_risk`). Keyed rows: Low 179, Medium 133, High 116, Unassigned 122.

### 1.2 The 53 features (cleaned → notebook §13 `build_features`)

All features use visit *t* and **earlier visits of the same `household_id`** only, sorted by `month_index` (= `Month_Ord`).

| Feature(s) | Built from (cleaned unless stated) | Check on the 448 matched rows |
|---|---|---|
| 8 × `F_*_t` (business not running … market stress any) | the `T_*` signals above at *t* | 100% |
| `F_Risk_Ord_t`, `F_Risk_Signal_Count_t`, `F_Risk_Unknown_t` | rule A on the `T_*` signals at *t* | follows from `T_*` |
| `F_Hours_Ord_t` | `hours_band`: 1-4→1, 5-8→2, 9+→3 | 100% |
| `F_Records_Ord_t` | `record_keeping_level` (0–3, already coded) | 100% |
| `F_Grant_Status_Ord_t` | `grant_use_status`: Not received→0, Received, not fully used→1, Received, fully used, bills not settled→2, Received, fully used→3 | 100% vs the notebook's 6.1 coding |
| `F_Borrowed_t`, `F_Saved_t`, `F_Cyclone_Affected_t`, `F_Female_Head`, `F_Asset_Lost_t`, `F_Storage_Transport_Issue_t`, `F_Machinery_Issue_t`, `F_Natural_Disaster_t` | `borrowed_money`, `saved_money`, `cyclone_affected`, `female_headed`, `problem_asset_lost`, `problem_storage_transport`, `problem_equipment`, `problem_disaster` (True→1, False→0, NA→blank) | 100% each |
| `F_Age` | `age` (NA if missing or outside 18–90) | 100% (197 blank in both; 241 of 550 keyed blank) |
| `F_Female_Participant` | `participant_gender`: Female→1, Male→0 | 100% |
| `F_Months_Since_Prev_Visit`, 5 × `F_Prev_*`, `F_Risk_Change_vs_Prev`, `F_Tenure_Months`, `F_N_Prior_Visits` | household history by `household_id` + `month_index` | same logic as §13 |
| `F_Risk_Mean_3M_Window`, `F_NoProfit_Rate_3M_Window`, `F_MarketStress_Rate_3M_Window`, `F_High_Count_6M_Window` | calendar-month windows [t−2, t] and [t−5, t] | same logic as §13 |
| **`F_Months_Since_Grant`** | **No grant date in the cleaned file.** Decided (Q2): take `6.2. Grant Received date` from `combined.xlsx` for the 448 matched rows (166 have a date), carry it forward within the household as §13 does, and leave it blank for the 102 new rows | see risk R3 / Q2 |
| 8 × `F_Mkt_*` | §1.3 join | 100% |
| 5 × `F_Macro_*` | §1.3 join | 100% |
| `F_Category` | `category` mapped with the notebook's `KEY_TO_PROG`, **plus** `BEAUTY AND WELLNESS`→`Beauty & Wellness` and `TRANSPORT & LOGISTICS`→`Transport & Logistics` (the names in the notebook's `PROG_CATS`) | 100% for the 7 old levels |
| `F_District` | `district` (already title case) | 100% |

Excluded, as in the notebook: identifiers (`visit_id`, `source_uuid`, `household_id`), dates, `month_index` as a predictor, `ds_division`, `activity`, the amount columns, and the wellbeing columns that are not among the 53 features (`skipped_meal`, `children_in_school`, …). **The feature list stays exactly the 53 in `feature_names_in_order`**, so the API request schema does not change.

### 1.3 Market and macro joins

- **Market** (`F_Mkt_*`): join `Category_Month_Table` rows with `Row_Basis == "ALL"` on (`Month` = `monitoring_period`, `Category_Key` = cleaned `category`). Use `Primary_Pressure_t`, `Primary_Volatility_t`, their `_t_minus_1`, `Category_Pressure_Tier_Ord_t`, `Category_Volatility_Tier_Ord_t` and `Category_Pressure_Tier_Ord_t_minus_1`, with the same formulas as §13. `F_Mkt_Evidence_Missing` = 1 when `Primary_Pressure_t` is blank. On the 448 rows this reproduces the original row values 100%. The market values are identical across the `ALL` / `SYNTHETIC` / `REAL` bases.
- **Macro** (`F_Macro_*`): national values, the same for every category. Join **by month only**, so they are available for all rows including the new categories (all 9 months complete; 100% match).
- **Categories with no market evidence** (all `F_Mkt_*` blank, `F_Mkt_Evidence_Missing` = 1):
  - `OTHER`, `TRADE`: in the table, but "Insufficient Evidence" with no pressure values or tier ordinals.
  - `BEAUTY AND WELLNESS`, `TRANSPORT & LOGISTICS`: **not in `Category_Month_Table` at all.**
  - Evidence exists for Agriculture, Construction, Food Processing, Garment/Handicrafts and Livestock, in 8 of 9 months (none for 2026-09).
  - So **254 of 550 keyed rows (46%)** have no market evidence: the 4 categories above in every month, plus all categories in 2026-09. In the original 448 rows the figure was 34%.

---

## 2. Expected modelling data (computed)

| | 448 original synthetic rows (reproduction check) | **All 550 keyed rows (candidate)** |
|---|---|---|
| 3M eligible rows | 219 (Low 83 / Medium 59 / High 77), 52 households — **equals the notebook** | **269** (Low 101 / Medium 76 / High 92), 64 households |
| 6M eligible rows | 116 (32 / 26 / 58), 51 households — **equals the notebook** | **138** (37 / 33 / 68), 62 households |
| Prediction months | 3M 2026-01..06; 6M 2026-01..03 | same |

3M by category: Agriculture 49, Garment/Handicrafts 36, Trade 33, Livestock 29, Food Processing 27, Construction 26, Beauty & Wellness 25, Transport & Logistics 25, Other 19.
6M by category: 23, 19, 16, 16, 13, 16, 11, 11, 13 (same order).

**Final split (notebook §19–21 design)**

| Horizon | Test month | Test rows | Train | Train rows (old) | Embargo |
|---|---|---|---|---|---|
| 3M | 2026-06 | 49 (old 39) | prediction months whose target month ≤ 2026-06 (Jan–Mar) | **127** (102) | yes |
| 6M | 2026-03 | 47 (old 39) | all earlier prediction months (Jan–Feb) | **91** (77) | **no**: an embargo would leave 0 rows, so the result is optimistic |

**Walk-forward (§29 E1; MIN_TRAIN 30, MIN_TEST 15):**
- **3M:** 5 folds (test months Feb–Jun). Feb and Mar have no embargo; Apr, May and Jun are embargoed.
- **6M:** 2 folds (Feb, Mar), both without embargo.

---

## 3. Training script design

**Files (all inside `market_risk/`):**

| File | Contents |
|---|---|
| `ml/training/__init__.py` | empty |
| `ml/training/features.py` | Pure functions, unit-testable on tiny inline frames: `t_signals(cleaned)`, `risk_rule_a(T)` (vectorised notebook rule), `build_features(df, market, macro, grant_dates)`, `build_targets(df, horizons)`, `category_level(key)` |
| `ml/training/xlsx_reader.py` | Small standard-library `.xlsx` reader (Q4: no openpyxl) and Excel serial-date conversion |
| `ml/training/train_from_cleaned.py` | CLI / orchestration (below) |
| `tests/test_training_features.py` | Inline toy data only: mappings, rule A equals `services.identify_current_risk` on all 81 combinations, history and window features, exact t+h target matching, leakage truncation test, category mapping, panel matching and its guards, xlsx reader. There is no end-to-end test with the real files: that is the script itself |

**Run (from `backend/`, in the shared `.venv` with scikit-learn 1.6.1):**
```bash
SUSTAIN_CLEANED=~/Documents/sustain_data/monitoring_visits_clean.csv \
SUSTAIN_COMBINED=~/Documents/sustain_data/combined.xlsx \
SUSTAIN_CANDIDATE_OUT=~/Documents/sustain_data/models_candidate \
python -m app.components.market_risk.ml.training.train_from_cleaned [--gate-only] [--report app/components/market_risk/RETRAIN_REPORT.md]
```

**Steps:**
1. **Load and guard.** Read the env vars. Stop with a clear message if they are missing, or if the output folder resolves to **anywhere inside the repository** (Q5). The default output is `~/Documents/sustain_data/models_candidate/` (`SUSTAIN_CANDIDATE_OUT`).
2. **Verify inputs.** Stop if any of these fail:
   - The 448 HH-n ↔ SYN-HH-n + month match is still one-to-one.
   - The `T_*` signals rebuilt from cleaned equal the original on those rows (0 mismatches).
   - No duplicate (`household_id`, month).
   - Every keyed row gets `is_synthetic=True`, and unkeyed rows are excluded.
   - The SHA-256 of both inputs is recorded.
3. **Build data.** `T_*` → rule A → the 53 features (§1) → targets `Risk_Label_3M/6M` (exact calendar month t+h, same household, Unassigned target → excluded). Run the **leakage truncation test** from §17 (features recomputed on data cut off at each month must be identical) and stop on any difference.
4. **Model selection (same as §19–21):**
   - **Pipeline:** `ColumnTransformer(num: SimpleImputer(median, add_indicator) + StandardScaler; cat: SimpleImputer("missing") + OneHotEncoder(handle_unknown="ignore"))`.
   - **Candidates:** LogisticRegression (C ∈ {0.01, 0.1, 1, 10}, balanced) and RandomForest (300 trees, balanced_subsample, max_depth ∈ {3, 5, None}, min_samples_leaf ∈ {1, 5, 10}).
   - **Tuning:** `GridSearchCV(scoring="f1_macro", cv=GroupKFold(4) by household)` on the **training set only**. The selected model is the best CV macro-F1, and the test month is used once.
   - **Reported:** majority and persistence baselines, test metrics (accuracy, macro P/R/F1, balanced accuracy, High precision/recall), a bootstrap 95% CI, and per-category test counts.
   - XGBoost is **not** a candidate (see R5). **Only the Random Forest is saved** (Q3), whichever model wins CV; the winner is recorded as `selected_by_cv`.
5. **Walk-forward** (§29 E1) for the selected configuration, with persistence and LR alongside. Per fold: macro-F1, High recall and High precision.
6. **Reproduction gate** (on the 448 original rows, run first; with `--gate-only`, only the gate runs). As run, the gate requires all of the following:
   - **Split sizes:** 3M 102/39, 6M 77/39.
   - **Training statistics:** equal to the deployed pipeline's (imputer medians, scaler means/scales, missing indicators, one-hot levels).
   - **Test metrics:** the test Macro-F1 and High recall of the **deployed configuration** (`max_depth` 3, `min_samples_leaf` 10) reproduce 3M 0.3026 / 0.56 and 6M 0.4302 / 0.88.
   - **Walk-forward:** the notebook §29 means are reproduced.

   The grid search's own choice of hyperparameters is **reported but not gated**, because it does not reproduce across machines (see §8). The candidate is trained only if the gate passes (`--force` overrides).
7. **Save** to `$SUSTAIN_CANDIDATE_OUT/{3M,6M}/` (outside the repo):
   - **`model.joblib`.**
   - **`feature_schema.json`:** the same 53 names, types and descriptions.
   - **`metadata.json`:** the same keys the loader requires and the current files have: `feature_names_in_order`, `numeric_features`, `categorical_features`, `categorical_levels` (from the training rows), `classes`, `class_encoding`, `category_mapping` (+2 new keys), `deployment_status` and `deployment_reason`, `software_versions`, `test_metrics`, `persistence_baseline_test_macro_f1`, `training_period`, `validation_methodology`, `target_rule`, `target_generation_method`. Added: `data_basis: "SYNTHETIC panel (70 households, 9 categories)"`, `model_version: "2.0-cleaned-candidate"`, `input_sha256` for both files, and `source: "train_from_cleaned.py"`.
   - **`training_report.json`** at the top level, plus the Markdown report `RETRAIN_REPORT.md` in this folder (`--report`): aggregates only (counts, metrics, walk-forward table, checks). **No rows, no IDs, no CSV, no local paths.**
   - **Walk-forward comparison:** *current* = the deployed RF configuration retrained per fold on the original-category rows; *candidate* = the candidate RF configuration retrained per fold on all rows. Both are scored on the same test months (all rows, and original-category rows).
   - **Proxy check for `F_Months_Since_Grant`:** missing rates by category group, permutation importance on the test month, and SHAP mean |contribution| and rank of its missing flag.
8. **Deployment status.** Always `NOT_READY`, with reasons: synthetic only, unvalidated rule, no real follow-up, no embargo for 6M, plus "does not beat persistence" where true.

**Not changed:** `ml/models/`, the notebook (its §13 stays the reference), `ml/sustain_predict.py`, and the API code. This step adds training code only.

---

## 4. What changes in the API if `F_Category` has 9 levels

Almost all of it is already **metadata-driven**:

| Part | Effect |
|---|---|
| `schemas.py` | No change. `F_Category` is a free `str`, and the 53 field names are unchanged |
| `ml/sustain_predict.validate_input`, `services._convert_category` | Read `categorical_levels` and `category_mapping` from metadata. With the new mapping, `"BEAUTY AND WELLNESS"` / `"TRANSPORT & LOGISTICS"` are **converted with a warning** instead of being treated as unknown |
| `GET /model-info` | Lists 9 levels automatically |
| `ml/explainer.py` | Generic `cat__F_Category_` mapping, no change. The one-hot width grows from 94 to 96 columns |
| `ml/loader.py` | No change for promotion by copying files. **Done (Q7):** `MARKET_RISK_MODELS_DIR` points the API at another model folder **for local testing only**; the default is unchanged (`ml/models/`) |
| Tests to update **at promotion** | `test_services.test_category_not_in_mapping_stays_unknown` uses `"TRANSPORT & LOGISTICS"` as its unknown example, so it would then be converted. Switch it to a truly unknown name. The other tests read metadata and should pass. Keep `model_name` = `SUSTAIN_Model_3M/6M`, because the tests and clients check it |
| Docs at promotion | `README.md` (coverage limitation, metrics), `ml/model_info.json`, `ml/DATA_DESCRIPTION.md`, `CONTRACTS_UPDATE.md` (still accurate), `IMPLEMENTATION_PLAN.md` |

**Promotion** (a separate, later step, owner's decision): copy the candidate files over `ml/models/{3M,6M}/` in one commit, together with the test and doc updates. Until then the deployed models and all 116 tests are untouched.

---

## 5. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **Still synthetic only.** Retraining adds coverage (2 categories, 12 households), not real-world validity. Status stays NOT_READY | State it in metadata, the report and the README. Never describe it as "real" |
| R2 | **The new categories have no market evidence**, and they are synthetic households added later, possibly by a different generator. The model may learn "category = B&W/T&L" rather than risk signals | Report per-category test counts and walk-forward by category. Check SHAP / importance for the `F_Category_*` columns |
| R3 | **`F_Months_Since_Grant` is not in the cleaned file.** Blank for all 102 new rows, so its missing indicator becomes a proxy for the new categories (spurious signal) | Best: the cleaning team adds the grant date (Q2). Otherwise join it from `combined.xlsx` for the 448 rows and report the importance of `missingindicator_F_Months_Since_Grant` |
| R4 | **The selected model could be LogisticRegression.** `/explain` uses `shap.TreeExplainer` and would fail on LR | Either restrict candidates to RandomForest (consistent with the §29 decision), or choose and record what to do if LR wins (Q3) |
| R5 | XGBoost is not in `requirements.txt` or the `.venv`. A selected XGB model could not be loaded by the API | Not a candidate |
| R6 | **Reading `combined.xlsx` needs `openpyxl`**, which is not in `requirements.txt` or the `.venv` | **Resolved (Q4):** `ml/training/xlsx_reader.py` (standard library only) |
| R7 | Small samples: 3M test 49 rows, 6M 47. The 6M split cannot be embargoed. Results remain optimistic and noisy | Report bootstrap CIs and walk-forward, and compare with persistence |
| R8 | The library and Python versions must match what the loader checks (scikit-learn 1.6.1). The rules say Python 3.11 while the `.venv` is 3.13 | Train in the shared `.venv` and record `software_versions`. The loader rejects a mismatch |
| R9 | Data leakage into the repo | Paths only from env vars; the script writes only models and aggregate reports; `*.csv` / `*.xlsx` are gitignored; review `git status` before committing |
| R10 | Category name drift: the cleaned file uses `BEAUTY AND WELLNESS`, the notebook names use `Beauty & Wellness`, and livelihood_planning uses the upper-case names | Use the notebook names as levels and map the upper-case names in `category_mapping` (Q1) |
| R11 | `n_jobs=-1` gives about 1e-16 differences between runs, and exactly tied duplicate columns make about 10 of 300 trees differ between Colab and this Mac | The gate checks data, statistics and the deployed configuration's metrics, not the grid choice (§8) |
| R12 | **Hyperparameter choice is unstable**: on the same data, grid search here picks (3, 5) / (3, 1) instead of Colab's (3, 10) | Report it, and consider fixing the deployed configuration for the candidate (§8 next steps) |

---

## 6. Decisions

| # | Question | Decision |
|---|---|---|
| Q1 | New level names | Notebook style: `Beauty & Wellness`, `Transport & Logistics`; the upper-case names are mapped in `category_mapping` |
| Q2 | Grant date | Taken from `combined.xlsx` for the 448 matched rows, null for the 102 new rows. The report checks whether the missing flag acts as a proxy (permutation importance + SHAP) |
| Q3 | Candidate models | Compare all candidates (baselines, LR, RF) as in the notebook; **save only the Random Forest** |
| Q4 | Excel reader | **No openpyxl.** A small built-in reader in `ml/training/xlsx_reader.py` |
| Q5 | Where candidates go | **Outside the repo**: `SUSTAIN_CANDIDATE_OUT`, default `~/Documents/sustain_data/models_candidate/`. The script refuses any path inside the repository |
| Q6 | Promotion bar | The reproduction gate passes; walk-forward candidate RF Macro-F1 is not lower than the current model's by more than 0.02, and High recall is not lower (all test rows, mean over folds); all tests pass |
| Q7 | Side-by-side testing | `MARKET_RISK_MODELS_DIR` in `ml/loader.py`, **local testing only**; default unchanged (`ml/models/`) |

---

## 7. CHANGES NEEDED OUTSIDE MY FOLDER

| # | File | Change | Why |
|---|---|---|---|
| 1 | ~~`backend/requirements.txt`~~ | **Not needed:** Q4 uses the built-in reader | — |
| 2 | `livelihood_planning/data_prep/` (cleaning owner, **not** me) | Optional, for a later retrain: add a `grant_date` column to the cleaned output and dictionary, so the 102 new rows also get `F_Months_Since_Grant` | Removes the confounding of the missing flag with the new categories |
| 3 | `docs/DATA_AND_MODELS_RULES.md` §4 | NDA sign-off (still pending) also covers any committed candidate model | Committed models built from the NDA dataset |

Nothing else outside `market_risk/` is needed. The data files stay in `~/Documents/sustain_data/` and are never copied into the repo.

---

## 8. Step 2 results (summary; full aggregates in `RETRAIN_REPORT.md`)

- **Reproduction gate: PASS.** The splits, the deployed pipeline's fitted training statistics, the deployed configuration's test metrics (3M Macro-F1 0.3026, High recall 0.56; 6M 0.4302 / 0.88) and the notebook §29 walk-forward (3M 0.356 vs 0.295; 6M 0.431 vs 0.179) are reproduced exactly.
- **Gate definition changed from the plan:** the plan required the grid search to pick the same RF parameters. On this machine it picks (3, 5) for 3M and (3, 1) for 6M instead of Colab's (3, 10), even though the data are identical. The cause is about 10 of 300 trees choosing differently between exactly tied, duplicate columns, which is platform-dependent floating point. That's why the gate checks the deployed configuration instead.
- **Candidate** (550 rows; 3M train/test 127/49 embargoed, 6M 91/47 not embargoed): RF 3M (`max_depth` None, `min_samples_leaf` 5), RF 6M (3, 1). Both NOT_READY; data basis "SYNTHETIC panel (70 households, 9 categories)"; saved outside the repo.
- **Promotion bar: NOT MET.** Walk-forward on all test rows:
  - 3M Macro-F1: candidate 0.347 vs current 0.350 (within 0.02).
  - 3M High recall: 0.301 vs 0.397 (lower).
  - 6M Macro-F1: 0.382 vs 0.422 (more than 0.02 lower).
  - 6M High recall: 0.667 vs 0.876 (lower).
- **Grant-date proxy:** the missing flag is fully confounded with the new categories (missing for 100% of their rows). But it is not a strong driver in either candidate (SHAP rank 32 and 42 of 96; permutation importance within noise).
- **Side-by-side** (`MARKET_RISK_MODELS_DIR` = candidate): 138 of 140 market_risk tests pass. The 2 failures are expected at promotion, because both assume the 7 deployed categories: `test_category_not_in_mapping_stays_unknown` and `test_category_mapping_keeps_the_seven_deployed_levels_and_adds_two`.
- **Next steps (not done):** separate the data effect from the hyperparameter effect by also training the candidate with the deployed configuration (3, 10). Repeat the grid with several seeds, or report CV ties. Get the grant date for the 102 new rows.
