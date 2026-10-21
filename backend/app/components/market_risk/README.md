# market_risk: 3-month and 6-month household market-risk prediction

Owner: @Chamosithmini · URL prefix: `/api/risk` · Public service functions: `predict_market_risk`, `explain_market_risk`, `get_model_info`, `identify_current_risk`

> **Status: NOT_READY.** Both models were trained and tested on **synthetic data only**.
> Every prediction includes `model_status` and `deployment_reason`, and they must be shown to users.
> Do not use these predictions for real decisions. See [Limitations](#limitations).

## What it does

For one SUSTAIN household at monitoring month *t*, the component predicts the household's market-risk class
(**Low / Medium / High**) at month *t+3* (3M model) and/or *t+6* (6M model).

- **Input:** 53 engineered `F_*` features. These include the household's current answers, its history from earlier visits, category market evidence and national macro indicators.
- **Models:** scikit-learn Pipeline + RandomForest (version 2.0, retrained on the team's cleaned monitoring data; see [Current models](#current-models-version-20)).
- **Target rule:** SUSTAIN-HH-Risk-Rule v1.0 (provisional).

It **explains each prediction with SHAP**: which features pushed the model towards its answer, and towards High. It also **identifies the household's current risk class** (Low / Medium / High / Unassigned) from four current-visit answers. This uses the rule-based SUSTAIN-HH-Risk-Rule v1.0, with no ML model.

The prediction input is the engineered features, not raw survey answers, because many features need the household's earlier visits. They are built as in `notebooks/SUSTAIN_3M_6M_Risk_Prediction.ipynb`, section 13 (`build_features`), and in `ml/training/features.py` for the retrained models.

## Current models (version 2.0)

On 2026-10-21 the deployed models were replaced by models retrained with `ml/training/train_from_cleaned.py`:

- **Data:** SYNTHETIC panel (70 households, 9 categories), 550 rows: the earlier 448 rows plus 102 rows in Beauty & Wellness and Transport & Logistics. Not real-world evidence.
- **Settings:** the same as version 1.0. Random Forest with `max_depth=3`, `min_samples_leaf=10`, 300 trees and seed 42, with no grid search.
- **Status:** still **NOT_READY**.
- **Why promoted (owner decision):** consistency with the team's cleaned data, and coverage of all 9 livelihood categories in the proposal. Version 1.0 knew only 7.
- **Trade-off accepted:** the agreed promotion bar was **not met**. Walk-forward results (mean over test months, all test rows):

| Horizon | Metric | Version 1.0 (previous) | Version 2.0 (deployed) | Change |
|---|---|---|---|---|
| 3M | Macro-F1 | 0.350 | 0.331 | −0.019 |
| 3M | High recall | **0.397** | **0.307** | **−0.090** |
| 6M | Macro-F1 | 0.422 | 0.429 | +0.007 |
| 6M | High recall | **0.876** | **0.771** | **−0.105** |

Version 2.0 misses more households that later turn High, on both horizons. With the same settings, this drop comes from the data, not from the settings. The full analysis, including the earlier "promotion bar not met" result, is in `RETRAIN_REPORT.md` and `RETRAIN_PLAN.md` §8.

Single embargoed test month (from `metadata.json`; small test sets, so the confidence intervals are wide):

| Horizon | Train / test rows | Macro-F1 [95% CI] | High recall | High precision | Persistence baseline Macro-F1 |
|---|---|---|---|---|---|
| 3M (test month 2026-06) | 127 / 49 | 0.421 [0.265, 0.563] | 0.633 | 0.655 | 0.366 |
| 6M (test month 2026-03, no embargo possible) | 91 / 47 | 0.402 [0.299, 0.500] | 0.733 | 0.759 | 0.174 |

## Folder layout

| Path | Contents |
|---|---|
| `router.py` | FastAPI endpoints (`/api/risk/...`) |
| `schemas.py` | Pydantic request/response models (53 explicit feature fields) |
| `services.py` | Public functions `predict_market_risk`, `explain_market_risk`, `get_model_info`, `identify_current_risk` |
| `ml/loader.py` | Cached loading of models and metadata, plus the scikit-learn version check |
| `ml/explainer.py` | Cached SHAP `TreeExplainer` per horizon; maps the 94 transformed columns back to the 53 features; additivity check |
| `ml/sustain_predict.py` | Colab export; the API reuses its `validate_input` |
| `ml/models/3M/`, `ml/models/6M/` | `model.joblib`, `metadata.json`, `feature_schema.json` |
| `ml/model_info.json`, `ml/DATA_DESCRIPTION.md`, `ml/Methodology_Results_Summary.md` | Model card, data description (no real values), methodology |
| `sample_data/predict_request_example.json` | One synthetic example request |
| `tests/` | Loader, service, endpoint, explanation and identification tests (inputs built inline) |

## Endpoints

### `GET /api/risk/health`
```json
{ "component": "market_risk", "status": "ok" }
```

### `POST /api/risk/predict`

**Request.** `horizon` is `"3M"`, `"6M"` or `"both"` (the default). `features` must contain **all 53 keys**, and any value may be `null`.
The complete body is in `sample_data/predict_request_example.json`. Shortened:

```json
{
  "horizon": "both",
  "features": {
    "F_Business_Not_Running_t": 0,
    "F_No_Profit_Last_Month_t": 1,
    "F_Revenue_Lowest_Band_t": null,
    "...": "all 53 F_* keys",
    "F_Category": "TRADE",
    "F_District": "Badulla"
  }
}
```

**Response 200** (a real output of the version 2.0 models for the sample with `F_Category` set to `"TRADE"`; the reasons and warnings are shortened here):

```json
{
  "horizon": "both",
  "predictions": [
    {
      "horizon": "3M",
      "model_name": "SUSTAIN_Model_3M",
      "predicted_risk": "High",
      "probabilities": { "Low": 0.3043, "Medium": 0.2555, "High": 0.4402 },
      "model_status": "NOT_READY",
      "deployment_reason": "trained and tested only on SYNTHETIC rows ...; promoted for consistency with the cleaned data and coverage of all 9 livelihood categories; trade-off accepted: ..."
    },
    {
      "horizon": "6M",
      "model_name": "SUSTAIN_Model_6M",
      "predicted_risk": "Low",
      "probabilities": { "Low": 0.3881, "Medium": 0.3155, "High": 0.2964 },
      "model_status": "NOT_READY",
      "deployment_reason": "trained and tested only on SYNTHETIC rows ...; test split could not be embargoed (optimistic); promoted for ...; trade-off accepted: ..."
    }
  ],
  "warnings": [
    "F_Category: converted 'TRADE' -> 'Trade' using category_mapping",
    "12 numeric features were null and will be median-imputed: F_Revenue_Lowest_Band_t, ..."
  ],
  "placeholder": false
}
```

**Input rules**

| Input | Result |
|---|---|
| Numeric value `null` | Accepted. It is median-imputed by the pipeline and listed in `warnings` |
| `F_Category` written as an upper-case survey name (`"TRADE"`, `"TRANSPORT & LOGISTICS"`, `"FISHERIES & AQUACULTURE"`) | Converted with `category_mapping`, with a warning |
| Unknown or `null` category or district | Accepted. It is encoded as all-zero, with a warning |
| Missing key, extra or misspelled key, non-numeric or infinite value, bad `horizon` | **422** |
| Model files missing, or scikit-learn ≠ 1.6.1 | **503**, with a short message. Details go only to the server log |

### `POST /api/risk/explain`

This explains each horizon's prediction with SHAP. **SHAP shows what drives the model, not real-world causes, and the models are NOT_READY.**

**Request.** The same body as `/predict`, plus `top_k` (1–20, default 5). For example: `{"horizon": "3M", "top_k": 3, "features": { ...all 53 F_* keys... }}`.

**Response 200** (version 2.0 models, the sample request with `"horizon": "3M"` and `"top_k": 3`; numbers rounded and long text shortened here):

```json
{
  "horizon": "3M",
  "explanations": [
    {
      "horizon": "3M",
      "model_name": "SUSTAIN_Model_3M",
      "predicted_risk": "High",
      "explained_class": "High",
      "base_value": 0.3333,
      "probability": 0.4428,
      "top_factors": [
        { "feature": "F_Age", "label": "Participant age in years", "value": 37.0, "contribution": 0.0226, "direction": "increases risk" },
        { "feature": "F_Grant_Status_Ord_t", "label": "Grant status: 0=not received, 1=not fully utilized, ...", "value": 1.0, "contribution": 0.0143, "direction": "increases risk" },
        { "feature": "F_Macro_CCPI_YoY_Change_1M", "label": "CCPI YoY inflation at t minus t-1 (percentage points)", "value": 1.3, "contribution": 0.0136, "direction": "increases risk" }
      ],
      "other_features_contribution": 0.059,
      "high_risk_probability": 0.4428,
      "high_risk_factors": [
        { "feature": "F_Age", "label": "Participant age in years", "value": 37.0, "contribution": 0.0226, "direction": "increases risk" },
        { "feature": "F_Grant_Status_Ord_t", "label": "Grant status: 0=not received, 1=not fully utilized, ...", "value": 1.0, "contribution": 0.0143, "direction": "increases risk" },
        { "feature": "F_Macro_CCPI_YoY_Change_1M", "label": "CCPI YoY inflation at t minus t-1 (percentage points)", "value": 1.3, "contribution": 0.0136, "direction": "increases risk" }
      ],
      "model_status": "NOT_READY",
      "deployment_reason": "trained and tested only on SYNTHETIC rows ..."
    }
  ],
  "warnings": ["12 numeric features were null and will be median-imputed: ..."],
  "note": "SHAP shows what drives the model, not real-world causes; models are NOT_READY (synthetic data)"
}
```

**How to read it**

- **`high_risk_factors` are the easiest to read:** `+` pushes towards High and `-` pushes away from High.
- **In `top_factors`,** `contribution` is towards the **predicted** class. For a Low prediction, `+` means towards Low, which is lower risk. (In the example the prediction is High, so both lists are the same.)
- **`direction`** always describes the effect on the expected risk score 0·P(Low) + 1·P(Medium) + 2·P(High), so it reads the same for any class.
- **Additivity:** `base_value` + all contributions = `probability`, with all contributions = `top_factors` + `other_features_contribution`. The server checks this to within 1e-6 and returns **503** if it fails.
- **How features are combined:** contributions of the 94 model columns are summed back to the 53 input features. A numeric feature's value and its missing indicator are added together, and all one-hot columns of `F_Category` / `F_District` are added together.
- **Errors:** input errors → **422**. Missing model files, a scikit-learn mismatch, a missing `shap` library or a failed check → **503**, with a short message and no paths.

### `POST /api/risk/identify`

This identifies the **current** risk class with SUSTAIN-HH-Risk-Rule v1.0 (notebook section 12, variant A). It is **rule-based, not ML**, and the rule is **provisional** (not yet validated by experts).

**Request.** All four keys are required. Each is `0`, `1` or `null` (not answered); `true`/`false` and `1.0`/`0.0` are also accepted as 1/0. Extra keys, missing keys and other values → **422**.

```json
{
  "business_not_running": 0,
  "no_profit_last_month": 1,
  "not_progressing_well": 0,
  "market_stress_any": null
}
```

**Response 200** (an Unassigned case: the blank market-stress answer decides between Medium and High)

```json
{
  "risk_class": "Unassigned",
  "risk_ord": null,
  "signal_count": 1,
  "unknown_count": 1,
  "reasons": [
    "No profit last month",
    "Not answered: market stress",
    "Blank answers could change the class -> Unassigned",
    "Could be up to High if blank answers are Yes; follow-up visit recommended"
  ],
  "rule_version": "SUSTAIN-HH-Risk-Rule v1.0 (provisional, requires expert validation)",
  "best_case_class": "Medium",
  "worst_case_class": "High",
  "possible_range": "Medium-High",
  "follow_up_needed": true
}
```

Set `not_progressing_well` to `1` and the answer is assigned: `"risk_class": "High"`, `best_case_class` = `worst_case_class` = `"High"`, `possible_range` = `"High"`, `follow_up_needed` = `false`.

| Class | Rule |
|---|---|
| High | Business not running, **or** at least 2 of {no profit last month, not progressing well, market stress} |
| Medium | Business running and exactly one signal |
| Low | Business running and all three signals answered 0 |
| Unassigned | The class would differ between blanks = 0 and blanks = 1, **or** business status is blank (unless the signals alone already give High, as in the notebook) |

**How bad could an Unassigned case be?** `risk_class` is never changed by these fields. They only show the range:

| Field | Meaning |
|---|---|
| `best_case_class` | Class if every blank signal is 0 and a blank business status means *running* |
| `worst_case_class` | Class if every blank signal is 1 and a blank business status means *not running* (→ High) |
| `possible_range` | `"<best>-<worst>"`, e.g. `"Low-Medium"` or `"Medium-High"`, or the single class when both are equal |
| `follow_up_needed` | `true` when `risk_class` is `Unassigned` (a follow-up visit should fill the blanks) |

For assigned cases `best_case_class == worst_case_class == risk_class`. For Unassigned cases the bounds always differ, and the last reason says how high the class could go.

Signals are counted, never cancelled. `risk_ord`, `signal_count` and `unknown_count` can be used directly as `F_Risk_Ord_t`, `F_Risk_Signal_Count_t` and `F_Risk_Unknown_t` in `/api/risk/predict`. Unassigned gives `risk_ord: null`, which the model median-imputes.

### `GET /api/risk/model-info[?horizon=3M|6M]`
This returns, for each model: name, horizon, algorithm, classes, `model_status`, `deployment_reason`, data basis, target rule, validation method, test metrics, persistence baseline, training period and created date. It also returns the **53 input features** (name, type, description) and the allowed `categorical_levels` for `F_Category` and `F_District`. It reads metadata only, without loading the models.

## The 53 input features

The authoritative list and order is `feature_names_in_order` in `ml/models/<horizon>/metadata.json`. It is the same for 3M and 6M. Call **`GET /api/risk/model-info`** for the names, types, descriptions and allowed category levels, or see `/docs`.

| Group | Features |
|---|---|
| Household signals at t | 8 × `F_*_t` (business not running, no profit, not progressing, lowest revenue band, sales below expected, high input cost, inputs unavailable, any market stress), `F_Risk_Ord_t`, `F_Risk_Signal_Count_t`, `F_Risk_Unknown_t` |
| Operating conditions at t | `F_Hours_Ord_t`, `F_Records_Ord_t`, `F_Grant_Status_Ord_t`, 8 Yes/No flags (borrowed, saved, cyclone, female head, asset lost, storage/transport, machinery, natural disaster) |
| Participant | `F_Age`, `F_Female_Participant` |
| Household history | `F_Months_Since_Prev_Visit`, 5 × `F_Prev_*`, `F_Risk_Change_vs_Prev`, `F_Tenure_Months`, `F_N_Prior_Visits`, 4 window features, `F_Months_Since_Grant` |
| Market (category) | 8 × `F_Mkt_*` |
| Macro (national) | 5 × `F_Macro_*` |
| Categorical | `F_Category`, `F_District` |

## Run only this component

From `backend/`, with the shared virtual environment active (`pip install -r requirements.txt`):

```bash
uvicorn app.components.market_risk.run_dev:app --reload --port 8004
```

Open <http://localhost:8004/docs>. The predict endpoint has a ready-made example body.
In the full app (`uvicorn app.main:app`) the same routes are at <http://127.0.0.1:8000/api/risk/...>.

## Run the tests

From `backend/`:

```bash
python -m pytest app/components/market_risk -v   # this component only
python -m pytest -q                              # whole backend
```

The tests build their inputs from `metadata.json` and never read CSV files or `sample_data/`.

## Calling from another component

```python
from app.components.market_risk.services import (
    get_model_info,
    identify_current_risk,
    predict_market_risk,
)

result = predict_market_risk({"horizon": "6M", "features": features_dict})  # 53 keys
result.predictions[0].predicted_risk, result.predictions[0].model_status

current = identify_current_risk({
    "business_not_running": 0, "no_profit_last_month": 1,
    "not_progressing_well": 0, "market_stress_any": None,
})
current.risk_class  # "Unassigned"
```

Do not import `market_risk.ml` directly (docs/CONTRACTS.md §4).

## Improvement experiments

Notebook section 29 records these experiments. They were run on the **version 1.0** models (58 households, 7 categories) and are analysis only.

- **E1:** walk-forward validation over several test months.
- **E2:** High-risk threshold tuning, chosen on training data only.
- **E3:** top-15 feature selection, chosen on training data only.

Results (**SYNTHETIC panel only, not real-world evidence**):

| Experiment | Random Forest | Persistence baseline |
|---|---|---|
| 3M, 5 test months (E1) | Macro-F1 0.356, High recall 0.44 | Macro-F1 0.295, High recall 0.19 |
| 3M, embargoed months Apr–Jun only | Macro-F1 0.302, High recall 0.42 | Macro-F1 0.300, High recall 0.16 |
| 6M, 2 test months, no embargo | Macro-F1 0.431 | Macro-F1 0.179 |

- **E2** raised 3M High recall to 0.64 but lowered Macro-F1 to 0.21.
- **E3** lowered High recall.

**Decision at the time:** keep the Random Forest models unchanged. They were later replaced by version 2.0, trained on the cleaned data with the same settings (see [Current models](#current-models-version-20)).

## Limitations

- **NOT_READY.** Both models are flagged `deployment_status: "NOT_READY"`. The API always returns `model_status` and `deployment_reason`. Never hide them in the UI.
- **Synthetic training data only.** All training and test rows come from the SYNTHETIC panel (70 households, 9 categories, Jan–Sep 2026). The source says these rows must not be used as evidence.
- **Version 2.0 catches fewer High cases than version 1.0.** Walk-forward High recall fell from 0.397 to 0.307 (3M) and from 0.876 to 0.771 (6M). This was accepted in exchange for coverage of all 9 categories (see [Current models](#current-models-version-20)).
- **No persistent household ID in real data.** The 99 real rows (Jan–Mar 2026) cannot be linked across months, so no real 3- or 6-month outcome exists to train or test on.
- **The single-month test results are uncertain.** On its embargoed test month, the 3M model's Macro-F1 is 0.421 [95% CI 0.265–0.563], against 0.366 for "predict the current class". The interval is wide and includes the baseline. Over several walk-forward months its Macro-F1 is only 0.331.
- **The 6M result is optimistic.** Its Macro-F1 is 0.402, against a baseline of 0.174, but its test split could not be embargoed.
- **The target rule is provisional.** SUSTAIN-HH-Risk-Rule v1.0 has not been validated by experts, and the market-tier thresholds are only partly verified. This affects both the predictions and `/identify`.
- **`/identify` follows the notebook code where it differs from the written rule.** If the business status is blank but 2 or more signals are 1, the class is High. The written rule in `metadata.json` would say Unassigned.
- **Coverage.** The models know 4 districts and 9 categories. Garment and Handicrafts are combined, and "Other" is mixed. The 102 rows in Beauty & Wellness and Transport & Logistics have no category market evidence and no grant date, so the market features are blank for these categories.
- **Small samples.** The 3M model has 127 training and 49 test rows; the 6M model has 91 and 47.
- **Gender features are model inputs.** `F_Female_Head` and `F_Female_Participant` influence the predictions. In version 1.0 they were among the top 3M SHAP factors for the sample household. In version 2.0 they rank 18th and 22nd of 53 for P(High). The model learned this from **synthetic** data, so it is not evidence about real people. It needs a fairness check on real data before any use.
- **Blank inputs can be top factors.** A `null` value can have a large contribution, because the model uses the median it fills in and its missing-value indicator. A blank answer is not neutral.
- **Some directions are counter-intuitive on the small synthetic panel.** For example, in the 6M model, "no profit last month = 1" lowers P(High) for the sample household. Do not read SHAP factors as causes.
- **The NDA sign-off for committing the models is pending supervisor approval.**

The steps needed before deployment are listed in `ml/Methodology_Results_Summary.md`: real data with a stable household ID covering at least 12 months, expert validation of the rule, and an embargoed real-data test that beats the persistence baseline.
