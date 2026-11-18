# market_risk v2: gap analysis and outcome

Status: **implemented.** Source of truth: `artifacts_v2/SUSTAIN_FE_and_Model_Training.ipynb` (code cells only were read; outputs were not opened).
All checks report counts only. No visit rows appear in this file.

## 1. Library versions

| Library | Used for training | `requirements.txt` | Installed in `backend/.venv` | Result |
|---|---|---|---|---|
| scikit-learn | 1.6.1 | 1.6.1 | 1.6.1 | Match |
| shap | 0.54.1 | 0.54.1 | 0.54.1 | Match |
| numpy | unknown (Colab default) | 2.0.2 | 2.0.2 | Pinned; predictions reproduce |
| pandas | unknown (Colab default) | 2.2.3 | 2.2.3 | Pinned; predictions reproduce |
| joblib | unknown (Colab default) | 1.4.2 | 1.4.2 | Pinned; all 4 models load |
| xgboost | 3.4.1 (model selection only) | not listed | not installed | Not needed: all 4 saved models are RandomForest |
| Python | Colab | team rule: 3.11 | **3.13.7** | **Open point:** kept at 3.13.7 for now by owner decision |

**Action: no change to `requirements.txt` and no retraining.**

## 2. What v1 does, and what changed

| Area | v1 | v2 | Reuse |
|---|---|---|---|
| Models | 2 three-class pipelines, 53 `F_*` features sent by the caller | 4 RandomForests: `core` (39 inputs) for P(High), `all` (71 inputs) for classes | Loader pattern |
| Features | Caller supplies them; helper endpoints fill some | Backend computes them from visit answers | None: names and formulas differ |
| Current risk | `identify_current_risk`, own reason wording | Notebook `classify()` and `reasons()` | Rule logic as reference |
| History | 14 `F_*` features | 13 notebook features | None |
| Market | Category × month JSON | District × category × month table, 25 districts | None |
| SHAP | `TreeExplainer`, summed columns, additivity check | Same approach on the binary 3M warning model | Approach and check |
| Errors | 503 without paths or traces | Same | Style |

v1 endpoints, models and tests are unchanged. The only v1 file edited is `router.py`, which now includes the v2 router.

## 3. Owner decisions

1. **URL prefix:** `/api/risk/v2/...`. `main.py` and `docs/CONTRACTS.md` are unchanged.
2. **Macro and evidence data:** built by `v2/build_artifacts.py` from the unzipped outputs.
   - `macro_anomalies_monthly.csv` comes from `SUSTAIN_Features_Model_Table.csv`. All 9 months have exactly one value.
   - `model_evidence.json` comes from 7 allow-listed sheets of `SUSTAIN_Model_Results.xlsx`. The household sheets are not parsed.
3. **Real visits:** scored one at a time through `POST /api/risk/v2/risk/visit`, marked `indicative - no history`, and never stored, listed or logged. Household endpoints return synthetic households only.
4. **Blank `business_running`:** Unassigned, unless the other signals already give High. This differs from the notebook, but no visit has this blank, so parity is unaffected.
5. **Months outside the market data:** 503 with a clear message.

## 4. Implementation notes

- **`UNASSIGNED` category:** not in the market table. It uses the `OTHER` row, which has the same CCPI series in the notebook.
- **Districts:** the market table has 25, but the models were trained on 5. Other districts get a response warning.
- **Version check:** scikit-learn removes the recorded version while unpickling, so `v2/artifacts.py` detects a difference through `InconsistentVersionWarning` during load.
- **History:** the 3M and 6M windows include the current visit and never later ones. A visit with no `household_key` gets null history, which differs from a first visit (`n_prior_visits = 0`).
- **Note text:** the API uses `indicative - no history`. The notebook's wording differs and is not part of the parity comparison.
- **Parity failures:** `tests/conftest.py` removes tracebacks from parity test reports, because pytest can otherwise print data frames.

## 5. Model evidence

| Comparison | Metric | Model | Persistence | Better than persistence |
|---|---|---:|---:|---|
| 3M warning, single test month | ROC AUC | 0.781 | 0.659 | Yes |
| 3M warning, rolling origin | ROC AUC | 0.652 | 0.638 | Yes, narrowly |
| 3M classes, single test month | Balanced accuracy | 0.502 | 0.442 | Yes |
| 3M classes, rolling origin | Balanced accuracy | 0.452 | 0.431 | Yes, narrowly |
| 6M warning, grouped CV | ROC AUC | 0.556 | 0.592 | **No** |
| 6M classes, grouped CV | Balanced accuracy | 0.324 | 0.424 | **No** |

6M responses therefore carry a `reliability_note` and no alert. Outcome labels exist only for simulated households, so none of this is real-world validation.

## 6. Future work

- **Monthly market-data update job.** The market table and macro file end at 2026-09, so later months return 503 until a job refreshes `SUSTAIN_District_Category_Market_Risk_25.csv`, `macro_anomalies_monthly.csv` and `DCS_OPL_2026.csv`.
- **Replace the CSV visit store** with the visits database. `v2/pipeline.py` has no data access, so only the loading code changes.
- **Run on Python 3.11** to meet the team rule, then re-run the parity test.
