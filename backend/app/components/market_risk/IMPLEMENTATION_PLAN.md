# market_risk — Backend Implementation Plan

Status: **ALL STEPS DONE** (step 8, final). See §7 for progress. The NDA check is **pending supervisor sign-off**.
Owner: @Chamosithmini. Every file below is inside `backend/app/components/market_risk/`.

---

## 0. Facts found while reading the repo (these shape the design)

| Fact | Source | Consequence |
|---|---|---|
| The market_risk URL prefix is **`/api/risk`**, not `/api/market-risk`. A PR that changes a prefix is rejected. | `docs/CONTRACTS.md` §1, existing `router.py` | All endpoints are `/api/risk/...` |
| `main.py` already does `app.include_router(risk_router)` from `market_risk/router.py`. | `backend/app/main.py` | New routes on the existing `router` are registered **automatically**, so `main.py` needs no change |
| The 3M and 6M models use **identical** `feature_names_in_order`, `numeric_features`, `categorical_levels` and `feature_schema.json`. | diff of both `metadata.json` / `feature_schema.json` | One request schema serves both horizons |
| The pipeline is `ColumnTransformer` → numeric: `SimpleImputer(median, add_indicator=True)` + `StandardScaler`; categorical: `SimpleImputer(constant "missing")` + `OneHotEncoder(handle_unknown="ignore")` → `RandomForestClassifier`. `classes_ = [0,1,2]` → Low/Medium/High via `metadata.classes`. | `joblib.load` inspection | Null numerics are safe (median-imputed). Null or unknown categories are safe (encoded as all zeros). No extra preprocessing is needed in the API |
| Both models are `deployment_status: "NOT_READY"` with different `deployment_reason`s. | `metadata.json` | Each per-horizon result carries its own `model_status` and `deployment_reason` |
| `metadata.json` has a `category_mapping` (raw survey names such as `"TRADE"` → `"Trade"`). | `metadata.json` | Decided (Q3): raw names are accepted and converted, with a warning |
| `ml/sustain_predict.py` reloads the model from disk on **every** `predict()` call and reports issues through `warnings.warn`. Its `validate_input(df, meta)` returns `(X, issues)`. | `ml/sustain_predict.py` | Reuse `validate_input` as it is. Add cached loading in `ml/loader.py`. Do not call `sustain_predict.predict()` from the API |
| The model was trained with scikit-learn 1.6.1, which matches `requirements.txt`. joblib is 1.6.0 at training vs 1.4.2 pinned; numpy is 2.1.3 vs 2.0.2 pinned. Loading was already tested and works. | `metadata.software_versions`, `requirements.txt` | The loader checks the sklearn version strictly, like livelihood's loader. joblib/numpy differences are only noted |
| `livelihood_planning`'s loader raises `RuntimeError` on an sklearn version mismatch and uses `lru_cache(maxsize=1)`. Its router dumps the request with `model_dump()` and calls a function. Its responses carry `placeholder`, `confidence` and `notes`. | `livelihood_planning/router.py`, `schemas.py`, `model_1_recommend/loader.py` | Same style here |
| The Postman `market_risk` folder is empty. The livelihood request is `POST http://127.0.0.1:8000/api/livelihood/recommend` with a raw JSON body. | `J26-DS-311.postman_collection.json` | Bodies are designed below. The Postman file is shared, so adding requests is listed under "outside my folder" |
| `*.csv` is gitignored, so `sample_data/*.csv` and `ml/models/*/example_input.csv` exist only on this machine. | `.gitignore` line 46 | Tests build their input inline from `metadata.json` |
| The committed notebook had outputs (45 cells, in commit `ab7c997`). The owner checked them: aggregate counts and rates plus synthetic example rows only, with no real row-level records, NIC, names or GPS. | owner review | **Done in step 2:** all outputs were cleared in place and the cell source was not changed. Git history is **not** rewritten |

---

## 1. Endpoints

All of these live on the existing `router = APIRouter(prefix="/api/risk", tags=["Market Risk"])`.

### 1.1 `GET /api/risk/health` (existing, unchanged)

```json
{ "component": "market_risk", "status": "ok" }
```

### 1.2 `POST /api/risk/predict` (new)

**Request**

```json
{
  "horizon": "both",
  "features": {
    "F_Business_Not_Running_t": 0,
    "F_No_Profit_Last_Month_t": 1,
    "F_Not_Progressing_Well_t": 0,
    "...": "... all 53 F_* keys, see below ...",
    "F_Macro_Diesel_Change_1M_pct": null,
    "F_Category": "Trade",
    "F_District": "Badulla"
  }
}
```

- `horizon`: `"3M" | "6M" | "both"`. Default `"both"`. Any other value → 422.
- `features`: an object with exactly the 53 names in `metadata.feature_names_in_order`.
  - The 51 numeric features are `float | null`. A null value is median-imputed by the pipeline and **listed in `warnings`**.
  - `F_Category` and `F_District` are `str | null`. An unknown value or null → **200 with a warning** (the encoder treats it as all-zero, via `handle_unknown="ignore"`).
  - **Category conversion (Q3):** before validation, `F_Category` is first compared with the allowed levels, case-sensitively. If it does not match, it is trimmed and upper-cased and looked up in `metadata.category_mapping` (for example `"TRADE"` → `"Trade"`, `"FISHERIES & AQUACULTURE"` → `"Other"`). Each conversion adds a warning: `"F_Category: converted 'TRADE' -> 'Trade' using category_mapping"`. A value that is still unknown afterwards (for example `"TRANSPORT & LOGISTICS"`) gets the normal unseen-category warning.
  - An unknown extra key (for example a typo such as `F_Agee`) → **422** (`extra="forbid"`), so a misspelled feature cannot be silently imputed.
  - **Missing key (Q1):** all 53 keys are **required**, and each may be `null`. A missing key → **422**. In pydantic, every field is `float | None` / `str | None` with **no default**.
- Features are nested under `"features"` rather than placed at the top level, so `horizon` and possible future options (Q2: batch) do not collide with feature names.

**Response 200**

```json
{
  "horizon": "both",
  "predictions": [
    {
      "horizon": "3M",
      "model_name": "SUSTAIN_Model_3M",
      "predicted_risk": "High",
      "probabilities": { "Low": 0.21, "Medium": 0.30, "High": 0.49 },
      "model_status": "NOT_READY",
      "deployment_reason": "trained and tested only on SYNTHETIC rows ...; does not beat the persistence baseline on the test month"
    },
    {
      "horizon": "6M",
      "model_name": "SUSTAIN_Model_6M",
      "predicted_risk": "Medium",
      "probabilities": { "Low": 0.25, "Medium": 0.41, "High": 0.34 },
      "model_status": "NOT_READY",
      "deployment_reason": "trained and tested only on SYNTHETIC rows ...; test split could not be embargoed (optimistic)"
    }
  ],
  "warnings": [
    "F_Category: converted 'TRADE' -> 'Trade' using category_mapping",
    "F_District: unseen categories ['Galle'] -> encoded as all-zero (handle_unknown='ignore')",
    "3 numeric features were null and will be median-imputed: F_Age, F_Months_Since_Grant, F_Macro_Diesel_t"
  ],
  "placeholder": false
}
```

- `predictions` is a list: it has 1 item for `"3M"` or `"6M"` and 2 items for `"both"`, in the order 3M then 6M.
- `probabilities` keys are always `Low`, `Medium`, `High`, rounded to 4 decimals. They sum to about 1.
- `model_status` and `deployment_reason` are copied from that horizon's `metadata.json`. They appear in **every** prediction, as required.
- `warnings` is a list of strings without duplicates. It comes from `validate_input` issues plus the API's own null-feature note.
- `placeholder: false` follows livelihood's `RecommendResponse` (the model is real, even though it is NOT_READY).

**Errors**

| Case | Status | Body |
|---|---|---|
| Bad `horizon`, wrong type, extra or missing key | 422 | FastAPI's default validation error |
| Model file, metadata or feature schema missing | 503 | `{"detail": "market_risk model 3M is unavailable: <reason>"}` |
| Installed sklearn ≠ 1.6.1 | 503 | `{"detail": "... requires scikit-learn 1.6.1, but X is installed"}` |
| Any other unexpected server error (for example `metadata.json` missing a key, which the loader raises as `ValueError`) | 500 | FastAPI's generic `Internal Server Error`, with no stack trace |

### 1.3 `GET /api/risk/model-info` (new, optional)

Query: `?horizon=3M|6M` (optional; returns both if omitted). This reads only the metadata files, **without loading the joblib file**.

```json
{
  "models": [
    {
      "horizon": "3M",
      "model_name": "SUSTAIN_Model_3M",
      "horizon_months": 3,
      "algorithm": "RandomForest",
      "classes": ["Low", "Medium", "High"],
      "model_status": "NOT_READY",
      "deployment_reason": "...",
      "data_basis": "SYNTHETIC panel (58 households, 2026-01..2026-09)",
      "target_generation_method": "SUSTAIN-HH-Risk-Rule v1.0 (provisional, requires expert validation)",
      "validation_methodology": "...",
      "test_metrics": { "Macro_F1": 0.3026, "High_Recall": 0.56, "...": "..." },
      "persistence_baseline_test_macro_f1": 0.3558,
      "training_period": { "prediction_months": "2026-01..2026-03", "target_months": "2026-04..2026-06" },
      "created": "2026-10-20T04:23:25"
    }
  ],
  "features": [
    { "name": "F_Business_Not_Running_t", "type": "numeric", "description": "value at visit t" },
    { "name": "F_Category", "type": "categorical", "description": "..." }
  ],
  "categorical_levels": {
    "F_Category": ["Agriculture & Plantation Crops", "..."],
    "F_District": ["Ampara", "Badulla", "Colombo", "Monaragala"]
  }
}
```

`features` and `categorical_levels` are shared by both models, so they appear once. The frontend can use this endpoint to build the input form and dropdowns. `input_sha256` and `software_versions` are **left out** of the response (internal details).

---

## 2. Files to create or edit (all inside `market_risk/`)

| File | Action | Contents |
|---|---|---|
| `ml/loader.py` | ✅ **Done (step 3)** | `MODELS_DIR = ML_DIR / "models"`, `HORIZONS`. `load_metadata` / `load_feature_schema` (cached, return copies, no sklearn). `get_model_status` → `{model_status, deployment_reason}`. `load_model(horizon)` → `(model, metadata)`, cached: `FileNotFoundError` if a file is missing, `RuntimeError` if sklearn ≠ the training version or the model doesn't match its metadata. Logs a warning when the model is not READY. `clear_cache()` for tests |
| `ml/sustain_predict.py` | ✅ **No change** | Colab export. The API imports only `validate_input`. Its `load_model`/`predict` are unused by the API and kept as the notebook record |
| `schemas.py` | ✅ **Done (step 4)** | `HealthResponse` unchanged. `MarketRiskFeatures` has 53 explicit required, nullable fields (`extra="forbid"`, `allow_inf_nan=False`) with descriptions written from notebook §13, because `feature_schema.json` descriptions are generic. `PredictRequest` uses an example equal to the sample JSON. `RiskProbabilities`, `HorizonPrediction`, `PredictResponse`, `ModelSummary`, `FeatureInfo`, `ModelInfoResponse` |
| `services.py` | ✅ **Done (step 5)** | `get_status` unchanged. `predict_market_risk(request: PredictRequest \| dict) -> PredictResponse`: per horizon it converts the category, warns about nulls, builds a 1-row DataFrame, runs `validate_input` → `predict_proba`, then maps classes. Warnings are deduplicated. `validate_input`'s own `warnings.warn` is **not** silenced, because `catch_warnings` is not thread-safe. `get_model_info(horizon=None) -> ModelInfoResponse` (metadata only) |
| `router.py` | ✅ **Done (step 6)** | `/health` unchanged. `POST /predict` and `GET /model-info?horizon=` have summaries and descriptions that mention NOT_READY. `FileNotFoundError` / `RuntimeError` → 503 with a fixed message (the details are logged on the server only). Input errors → FastAPI 422 |
| `run_dev.py` | ✅ **No change** | It already includes `router` (port 8004) |
| `tests/test_health.py` | ✅ **No change** | It still passes |
| `tests/conftest.py`, `tests/test_services.py`, `tests/test_endpoints.py` | ✅ **Done (step 7)** (they replace the planned `test_predict.py`) | Inline inputs from `metadata.json` (no CSV, no `sample_data/`). Services: horizons, probabilities, NOT_READY, warnings, TRADE conversion, all-null, schema-order drift guard, `get_model_info` does not load the models. Endpoints: 200 / 422 (extra, missing, bad horizon, non-numeric) / 503 (missing files, sklearn mismatch) / no internals leaked |
| `tests/test_loader.py` | ✅ **Done (step 7)** | Load + cache, 3M/6M metadata consistency, copies cannot change the cache, status exposed, unknown horizon, missing model/metadata → `FileNotFoundError`, sklearn mismatch → `RuntimeError` |
| `ml/model_info.json` | ✅ **Done (step 8; updated for version 2.0 in step 13)** | Model names, type, target, trained 2026-10-20 in Google Colab, synthetic data basis, NOT_READY, repo locations, per-horizon test metrics + persistence baseline, library versions + notes, NDA pending, `download_location: null` (364 KB / 316 KB) |
| `ml/DATA_DESCRIPTION.md` | ✅ **Done (step 8)** | Dataset, source, row counts (99 real / 448 synthetic), period, targets, column groups, the 53 features, cleaning, known issues. **No real values or rows**. Two cells are marked "owner to confirm" |
| `sample_data/predict_request_example.json` | **Created in step 2** | One `PredictRequest` body (`horizon: "both"`) built from synthetic example row 1 of the former `example_input_3M.csv`. Floats are rounded to 4 decimals, blanks become `null` (12 nulls), and keys are in metadata order. Both models score it without error. For Swagger, Postman and the docs only: **tests do not read it** (they build their input inline) |
| `sample_data/example_input_3M.csv`, `example_input_6M.csv` | **Deleted in step 2** | CSV files are not allowed in `sample_data/` (DATA_AND_MODELS_RULES §5). They were gitignored, so nothing was tracked. `ml/models/*/example_input.csv` stay on this machine only, still gitignored |
| `notebooks/SUSTAIN_3M_6M_Risk_Prediction.ipynb` | **Outputs cleared in step 2** | `outputs: []` and `execution_count: null` in all code cells (45 had outputs). All 86 cell sources were checked as unchanged, and the JSON formatting (indent 2, UTF-8) was kept |
| `README.md` | ✅ **Done (step 8)** | What it does, endpoints with examples, run and test commands, features, limitations |
| `CONTRACTS_UPDATE.md` | ✅ **Done** | Ready-to-paste `docs/CONTRACTS.md` §2 rows for the team lead |
| `IMPLEMENTATION_PLAN.md` | ✅ This file | |

Commit order: see §7.

---

## 3. Router registration

**Automatic.** `backend/app/main.py` already imports `app.components.market_risk.router.router` as `risk_router` and calls `app.include_router(risk_router)`. New routes added to that same `router` object show up in the main app and in `run_dev.py` without any change to `main.py`. The prefix stays `/api/risk`.

---

## 4. Rules from docs/ that affect this design

- **CONTRACTS §1:** the prefix must stay `/api/risk`. `/api/market-risk` would be rejected.
- **CONTRACTS §2:** the public function is `predict_market_risk` (that name is already reserved). `get_model_info` is a second public function. Both need their Input/Output written into `docs/CONTRACTS.md` (shared → outside my folder).
- **CONTRACTS §4:** other components must call only `services.predict_market_risk` / `get_model_info`, never `market_risk.ml.*`. My own `services.py` may import my own `ml/`.
- **CONTRACTS §3:** no Supabase tables are planned for this step. Predictions are not stored (Q6).
- **DATA_AND_MODELS_RULES §3:** joblib files are about 0.35 MB each (limit about 25 MB), so they may be committed in `ml/` and `download_location` stays null. Training must match pinned versions: sklearn matches, joblib and numpy differ (see §0). `model_info.json` must be updated with training date, metrics and versions.
- **DATA_AND_MODELS_RULES §4 (NDA):** a RandomForest stores only split thresholds, not records, and these models are trained on **synthetic** rows only. The supervisor checkbox in that doc is still unticked: **pending supervisor sign-off** (Q7).
- **DATA_AND_MODELS_RULES §5:** `sample_data/` must hold **JSON only, under 50 records, anonymised or synthetic, no CSV**. Done: the CSVs were deleted and one synthetic JSON request was added.
- **DATA_AND_MODELS_RULES §2:** notebooks must have their outputs cleared. Done in step 2. Clear them again before any future notebook commit.
- **REQUIREMENTS_RULES:** no new library is needed. Everything used (`scikit-learn`, `numpy`, `pandas`, `joblib`) is already pinned in livelihood_planning's section. Rule 3 forbids editing their lines, so `requirements.txt` stays unchanged (see the "outside my folder" list for an optional comment line). Rule 9 says Python **3.11**, but the local `.venv` is Python 3.13.7 and training used 3.13. Tests should also pass on 3.11.
- **AGENTS.md §4:** never read or print `.env`. This component needs no secrets.

---

## 5. Decisions (formerly open questions)

| # | Question | Decision | Decided by |
|---|---|---|---|
| — | Prefix / endpoint | Keep `/api/risk`. The endpoint is `POST /api/risk/predict` | Owner |
| Q1 | Missing keys | The client **must send all 53 keys**, and each may be `null`. A missing key → 422 | Owner |
| Q2 | Batch prediction | **Single record only** for now. Batch (`"records": [...]`) can come later if the dashboard needs it | Proposed default |
| Q3 | Raw survey category names | **Accept** them and convert them with `metadata.category_mapping` (trimmed, case-insensitive), with a warning for each conversion. A value that is still unknown afterwards gets the normal unseen-category warning | Owner |
| Q4 | Sample data | One synthetic JSON request in `sample_data/` (done). The local `sample_data/*.csv` were deleted (done) | Owner |
| Q5 | Committed notebook outputs | The owner checked them: aggregates and synthetic rows only. Outputs were cleared in place (done). Git history is **not** rewritten | Owner |
| Q6 | Store predictions in Supabase | **No**, not in this phase | Proposed default |
| Q7 | NDA sign-off for committed models | **Pending supervisor sign-off.** The owner has asked. Work continues meanwhile | Pending |
| Q8 | Per-prediction explanations | **Later step.** No SHAP now (it is not in requirements.txt). `/model-info` may expose the global top features from `Methodology_Results_Summary.md` | Proposed default |
| Q9 | joblib/numpy version mismatch (trained 1.6.0 / 2.1.3 vs pinned 1.4.2 / 2.0.2) | **Accept as it is.** Loading was tested and works, and sklearn (the part that matters) matches exactly. The loader checks only sklearn strictly. The mismatch is recorded in `model_info.json` | Proposed default |

---

## 6. CHANGES NEEDED OUTSIDE MY FOLDER (final list)

None of these is needed for the endpoints to work (router registration is automatic). All of them need the project leader's approval, and none has been made.

| # | File | Exact change | Why |
|---|---|---|---|
| 1 | `docs/CONTRACTS.md`, §2 | Replace the row `\| market_risk \| predict_market_risk \| TBD \| TBD \| Not started \|` with the three rows in `backend/app/components/market_risk/CONTRACTS_UPDATE.md` (`predict_market_risk`, `get_model_info`, `identify_current_risk`) | Public functions must be listed there. Leader-only (CONTRACTS §4) |
| 2 | `J26-DS-311.postman_collection.json`, `"market_risk"` folder (empty) | Add `risk_health` GET `http://127.0.0.1:8000/api/risk/health`; `risk_predict` POST `http://127.0.0.1:8000/api/risk/predict` (raw JSON body = `sample_data/predict_request_example.json`); `risk_model_info` GET `http://127.0.0.1:8000/api/risk/model-info` (optional `?horizon=3M`); `risk_identify` POST `http://127.0.0.1:8000/api/risk/identify` (raw JSON body with the four signals, see README) | Team testing. Repo-root shared file |
| 3 | `docs/DATA_AND_MODELS_RULES.md`, §4 | Tick `[ ] Confirmed on ____ by ____` once the supervisor agrees | NDA check for committed models: **pending supervisor sign-off** |
| 4 | `backend/requirements.txt`, `# === market_risk (@Chamosithmini) ===` (optional) | At most a comment line `# uses scikit-learn, numpy, pandas, joblib pinned in livelihood_planning section`; **no package lines** | Records the dependency without duplicating anyone's pins (REQUIREMENTS_RULES 3). Can be skipped |
| — | Not needed: git history of the notebook | The owner confirmed the old outputs had no real row-level data. They were cleared in place, and history is not rewritten | — |

Owner decision (inside my folder, not done): the notebook source still has Colab / Google Drive paths in cells 1, 3, 5 and 84–85 (`/content/drive` mount, `/content/drive/MyDrive/NEW DATA/...`, `/content/SUSTAIN_outputs`). DATA_AND_MODELS_RULES §2 says "Do not hard-code private file paths". Cell source was left unchanged as instructed. Moving these paths behind the existing `SUSTAIN_INPUT` / `SUSTAIN_OUTPUT` environment variables would need a source edit.

---

## 7. Progress

| Step | What | Status |
|---|---|---|
| 1 | Implementation plan | ✅ Done |
| 2 | Decisions; notebook outputs cleared; sample JSON; local CSVs deleted | ✅ Done |
| 3 | `ml/loader.py` | ✅ Done |
| 4 | `schemas.py` | ✅ Done |
| 5 | `services.py` (+ `CONTRACTS_UPDATE.md`) | ✅ Done |
| 6 | `router.py` | ✅ Done |
| 7 | Tests (`conftest.py`, `test_loader.py`, `test_services.py`, `test_endpoints.py`) | ✅ Done: 38 passed at the time |
| 8 | Review; `model_info.json`; `DATA_DESCRIPTION.md`; `README.md`; this plan | ✅ Done |
| 9A | Current-risk identification (rule-based, SUSTAIN-HH-Risk-Rule v1.0 variant A): `IdentifyRequest` / `IdentifyResponse` in `schemas.py`, public `identify_current_risk` in `services.py`, row added to `CONTRACTS_UPDATE.md`. Follows the notebook code: blank business status + 2 or more signals → High. Checked against the notebook's `risk_rule` on all 81 input combinations (0 mismatches) | ✅ Done |
| 9B | `POST /api/risk/identify` in `router.py`; `tests/test_identify.py` (all verify-table cases via service and endpoint, 422 cases, true/false and 1.0/0.0 accepted as 1/0); README updated | ✅ Done: market_risk 81 passed at the time |
| 10 | Identify: `best_case_class`, `worst_case_class`, `possible_range`, `follow_up_needed` and a follow-up reason when Unassigned; `risk_class` unchanged. `/docs` response example; tests for all verify cases plus a check against the notebook rule with blanks filled on all 81 combinations | ✅ Done: market_risk 87 passed at the time |
| 11 | Improvement experiments (notebook section 29): E1 walk-forward, E2 High-threshold tuning, E3 top-15 features (synthetic panel only). Decision: keep the deployed Random Forest models unchanged. Cells added with empty outputs; the notebook was not run | ✅ Done |
| 12A | SHAP explanation logic: `ml/explainer.py` (cached `TreeExplainer` per horizon on `pipeline[-1]`, 94 → 53 feature mapping by summing, both shap output shapes, additivity check < 1e-6), `ExplainRequest` / `ExplainResponse` schemas, public `explain_market_risk` (shared input preparation with predict; predicted class + High class; direction from the expected risk score) | ✅ Done |
| 12B | `POST /api/risk/explain` (422 / 503, including missing shap and a failed check via `ExplanationError`); `conftest.py` also clears the explainer cache; `tests/test_explain.py`; README endpoint + limitations; `CONTRACTS_UPDATE.md` row | ✅ Done: market_risk 116 passed |
| 13 | **Promoted the retrained models (version 2.0)** to `ml/models/3M` and `ml/models/6M`: deployed RF settings (`max_depth=3`, `min_samples_leaf=10`, seed 42, no grid search), SYNTHETIC panel (70 households, 9 categories), 550 rows. Copied only `model.joblib`, `metadata.json` and `feature_schema.json` from the candidate folder outside the repo; no CSV or data rows. `metadata.json` keeps NOT_READY and records the decision and trade-off under `promotion`. **Decision (owner): promoted for coverage, trade-off accepted.** The promotion bar was not met. Walk-forward High recall fell (3M 0.397 → 0.307, 6M 0.876 → 0.771); Macro-F1 3M 0.350 → 0.331, 6M 0.422 → 0.429. Reason: consistency with the cleaned data and coverage of all 9 categories. The two tests that assumed 7 categories were updated. README, `model_info.json`, `RETRAIN_PLAN.md` and `RETRAIN_REPORT.md` were updated | ✅ Done: market_risk 142 passed, full suite 165 passed |
| 14 (B1) | **Market context lookup:** `ml/market_context.json` holds the 13 market and macro features for 11 category keys × 9 months, built by `ml/training/build_market_context.py` with the training join and formulas. The formulas moved into `features.market_macro_features`, which `build_features` now calls. Lookup = training features on 550 of 550 keyed rows (7,150 of 7,150 values). `ml/market_context.py` reads it. `GET /api/risk/market-context` and the public `get_market_context` return 422 for an unknown category or bad month, and 200 with nulls and a note for a month outside the data. `tests/test_market_context.py` (24 tests). README and `CONTRACTS_UPDATE.md` row | ✅ Done |
| 14b | **Gate fix:** the reproduction gate in `train_from_cleaned.py` compared with `ml/models/` (version 2.0 since the promotion) and always failed. It now uses the pinned version 1.0 reference `ml/training/gate_reference_v1.json`, built from the original v1.0 files with `--build-gate-reference`. `--gate-only`: PASS on 3M and 6M. Guarded by `tests/test_gate_reference.py` (17 tests, no data) | ✅ Done |
| — | NDA supervisor sign-off (Q7) | ⏳ **Pending supervisor sign-off** |
| — | Leader-approved shared changes (§6) | ⏳ Waiting for the leader |
