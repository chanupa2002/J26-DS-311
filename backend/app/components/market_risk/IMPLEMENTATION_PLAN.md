# market_risk — Backend Implementation Plan

Status: plan agreed (step 2). The open questions are answered in §5. In step 2 the notebook outputs were cleared and `sample_data/predict_request_example.json` was added. No API code has been written yet.
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
| `metadata.json` has a `category_mapping` (raw survey names such as `"TRADE"` → `"Trade"`). | `metadata.json` | Optional: accept raw names and map them (see open question Q3) |
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
| `validate_input` raises `ValueError` (should be unreachable after pydantic) | 422 | `{"detail": "<message>"}` |

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
| `ml/loader.py` | **Edit** (replace the template `NotImplementedError`) | `MODELS_DIR = ML_DIR / "models"`, `HORIZONS = ("3M", "6M")`. `load_metadata(horizon)` (lru_cache) reads `metadata.json` + `feature_schema.json` and needs no sklearn. `load_model(horizon)` (lru_cache) checks that the files exist (`FileNotFoundError`), checks `sklearn.__version__ == metadata.software_versions["scikit-learn"]` (`RuntimeError`, as livelihood does), then calls `joblib.load`. Heavy imports stay inside the function, so the server starts fast. Rejects any horizon that is not in `HORIZONS` |
| `ml/sustain_predict.py` | **No change** | This is the Colab export. The API imports only `validate_input`. It stays as the record of the notebook's logic |
| `schemas.py` | **Edit** (keep `HealthResponse`) | `Horizon = Literal["3M","6M"]`, `HorizonOption = Literal["3M","6M","both"]`. `MarketRiskFeatures(BaseModel)` has 53 explicit fields (51 `float \| None`, 2 `str \| None`, all **required with no default**, per Q1) in the same order as metadata, with `model_config = ConfigDict(extra="forbid")` and a `Field(description=...)` taken from `feature_schema.json`, so Swagger documents each one. `PredictRequest {horizon: HorizonOption = "both", features: MarketRiskFeatures}` with a `json_schema_extra` example. `HorizonPrediction`, `PredictResponse`, `ModelSummary`, `FeatureInfo`, `ModelInfoResponse` match §1. Fields are written out explicitly, not made with `create_model`, so the contract is readable and diff-able. A test guards it against drift from metadata |
| `services.py` | **Edit** (keep `get_status`) | Public `predict_market_risk(features: dict, horizon: str = "both") -> dict` replaces the placeholder and returns the §1.2 response dict. Steps: resolve horizons → convert `F_Category` with `category_mapping` and add a warning when it converts (Q3; private helper `_normalise_category`) → build a 1-row `pd.DataFrame` in `feature_names_in_order` → collect the null-numeric warning → for each horizon `load_model`, `validate_input` (with `warnings.catch_warnings()`, so issues are returned rather than printed twice) → `predict_proba` → map class indices through `metadata.classes`. Public `get_model_info(horizon: str \| None = None) -> dict`. The module docstring documents both functions for `docs/CONTRACTS.md` |
| `router.py` | **Edit** (keep `/health`) | `POST /predict` (`response_model=PredictResponse`) calls `services.predict_market_risk(request.features.model_dump(), request.horizon)`. `GET /model-info` (`response_model=ModelInfoResponse`, `horizon: Horizon \| None = None`). This file maps `FileNotFoundError` / `RuntimeError` → `HTTPException(503)` and `ValueError` → `HTTPException(422)` |
| `run_dev.py` | **No change** | It already includes `router` (port 8004) |
| `tests/test_health.py` | **No change** | It must keep passing |
| `tests/test_predict.py` | **Create** | Inputs are built **inline** from `ml/models/3M/metadata.json` (`feature_names_in_order`: numerics = 0.0, `F_Category` / `F_District` = first allowed level). It never reads a CSV. Tests: predict 3M / 6M / both (status 200, 1 or 2 items, keys Low/Medium/High, sum ≈ 1, `predicted_risk` is in the classes, `model_status == "NOT_READY"`, `deployment_reason` is not empty); all numerics null → 200 + warning; unknown district → 200 + warning that mentions `F_District`; `F_Category: "TRADE"` → 200 + conversion warning, with the same probabilities as `"Trade"`; `F_Category: "TRANSPORT & LOGISTICS"` → 200 + unseen-category warning; bad horizon → 422; extra key → 422; missing key → 422 (Q1); `/model-info` returns both models, 53 features, levels; **drift guard**: `list(MarketRiskFeatures.model_fields) == metadata["feature_names_in_order"]` for both horizons; `services.predict_market_risk` called directly (the public contract) |
| `tests/test_loader.py` | **Create** (small) | `load_model("3M")` is cached (same object twice), an unknown horizon raises, and 3M/6M metadata agree on features and levels (this guards the "one schema" assumption) |
| `ml/model_info.json` | **Edit** | Fill in `model_name` (both), `trained_on: "SYNTHETIC panel (58 households, 2026-01..2026-09)"`, `trained_in: "Google Colab"`, test metrics per horizon, `library_versions` (from `software_versions`), `deployment_status: "NOT_READY"`, `download_location: null` (files are small: 364 KB / 316 KB) |
| `ml/DATA_DESCRIPTION.md` | **Edit** | Dataset name, source and target (`Risk_Label_3M/6M`, rule v1.0), the 53 feature names / types / meanings from `feature_schema.json`, cleaning summary, known issues (from `Methodology_Results_Summary.md`). **No real values or rows** |
| `sample_data/predict_request_example.json` | **Created in step 2** | One `PredictRequest` body (`horizon: "both"`) built from synthetic example row 1 of the former `example_input_3M.csv`. Floats are rounded to 4 decimals, blanks become `null` (12 nulls), and keys are in metadata order. Both models score it without error. For Swagger, Postman and the docs only: **tests do not read it** (they build their input inline) |
| `sample_data/example_input_3M.csv`, `example_input_6M.csv` | **Deleted in step 2** | CSV files are not allowed in `sample_data/` (DATA_AND_MODELS_RULES §5). They were gitignored, so nothing was tracked. `ml/models/*/example_input.csv` stay on this machine only, still gitignored |
| `notebooks/SUSTAIN_3M_6M_Risk_Prediction.ipynb` | **Outputs cleared in step 2** | `outputs: []` and `execution_count: null` in all code cells (45 had outputs). All 86 cell sources were checked as unchanged, and the JSON formatting (indent 2, UTF-8) was kept |
| `IMPLEMENTATION_PLAN.md` | This file | |

Commit order: (1) plan ✅ → (2) answered plan + cleared notebook + sample JSON ✅ → (3) `ml/loader.py` + `tests/test_loader.py` → (4) `schemas.py` → (5) `services.py` → (6) `router.py` + `tests/test_predict.py` → (7) `model_info.json` + `DATA_DESCRIPTION.md`.

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

## 6. CHANGES NEEDED OUTSIDE MY FOLDER

None of these is required to make the endpoints work. Router registration is already automatic. All of them need the project leader's approval, and I will not make any of them.

| # | File | Exact change | Why |
|---|---|---|---|
| 1 | `docs/CONTRACTS.md`, §2 table, row `market_risk \| predict_market_risk \| TBD \| TBD \| Not started` | Input: `features: dict (53 F_* keys, see GET /api/risk/model-info), horizon: "3M"\|"6M"\|"both"`. Output: `{horizon, predictions:[{horizon, model_name, predicted_risk, probabilities{Low,Medium,High}, model_status, deployment_reason}], warnings[], placeholder}`. Status: `In progress (models NOT_READY)`. Add a row for `get_model_info(horizon=None) -> dict` | CONTRACTS §2 says public functions must be listed there. Leader-only (CONTRACTS §4) |
| 2 | `J26-DS-311.postman_collection.json`, `"market_risk"` folder (currently `"item"` is missing or empty) | Add `risk_health` GET `http://127.0.0.1:8000/api/risk/health`, `risk_predict` POST `.../api/risk/predict` (body = `backend/app/components/market_risk/sample_data/predict_request_example.json`), `risk_model_info` GET `.../api/risk/model-info` | Team testing. It is a repo-root shared file |
| 3 | ~~Git history of the notebook~~ | **Not needed.** The owner checked that the outputs contain no real row-level data. They were cleared in place in step 2, and history is not rewritten | — |
| 4 | `docs/DATA_AND_MODELS_RULES.md` §4 | Tick `[ ] Confirmed on ____ by ____` once the supervisor agrees (**pending supervisor sign-off**) | NDA check for committed models |
| 5 | `backend/requirements.txt`, `# === market_risk (@Chamosithmini) ===` section (optional) | Add the comment line `# uses scikit-learn, numpy, pandas, joblib pinned in livelihood_planning section` and **no package lines** | Records the dependency without duplicating or changing anyone's pins (REQUIREMENTS_RULES 3). This can be skipped entirely |
