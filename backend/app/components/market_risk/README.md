# market_risk: 3-month and 6-month household market-risk prediction

Owner: @Chamosithmini · URL prefix: `/api/risk` · Public service functions: `predict_market_risk`, `get_model_info`, `identify_current_risk`

> **Status: NOT_READY.** Both models were trained and tested on **synthetic data only**.
> Every prediction includes `model_status` and `deployment_reason`, and they must be shown to users.
> Do not use these predictions for real decisions. See [Limitations](#limitations).

## What it does

For one SUSTAIN household at monitoring month *t*, the component predicts the household's market-risk class
(**Low / Medium / High**) at month *t+3* (3M model) and/or *t+6* (6M model).

- **Input:** 53 engineered `F_*` features. These include the household's current answers, its history from earlier visits, category market evidence and national macro indicators.
- **Models:** scikit-learn Pipeline + RandomForest.
- **Target rule:** SUSTAIN-HH-Risk-Rule v1.0 (provisional).

It also **identifies the household's current risk class** (Low / Medium / High / Unassigned) from four current-visit answers. This uses the rule-based SUSTAIN-HH-Risk-Rule v1.0, with no ML model.

The prediction input is the engineered features, not raw survey answers, because many features need the household's earlier visits. They are built as in `notebooks/SUSTAIN_3M_6M_Risk_Prediction.ipynb`, section 13 (`build_features`).

## Folder layout

| Path | Contents |
|---|---|
| `router.py` | FastAPI endpoints (`/api/risk/...`) |
| `schemas.py` | Pydantic request/response models (53 explicit feature fields) |
| `services.py` | Public functions `predict_market_risk`, `get_model_info`, `identify_current_risk` |
| `ml/loader.py` | Cached loading of models and metadata, plus the scikit-learn version check |
| `ml/sustain_predict.py` | Colab export; the API reuses its `validate_input` |
| `ml/models/3M/`, `ml/models/6M/` | `model.joblib`, `metadata.json`, `feature_schema.json` |
| `ml/model_info.json`, `ml/DATA_DESCRIPTION.md`, `ml/Methodology_Results_Summary.md` | Model card, data description (no real values), methodology |
| `sample_data/predict_request_example.json` | One synthetic example request |
| `tests/` | Loader, service, endpoint and identification tests (inputs built inline) |

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

**Response 200** (a real output for the sample with `F_Category` set to `"TRADE"`; the reasons and warnings are shortened here):

```json
{
  "horizon": "both",
  "predictions": [
    {
      "horizon": "3M",
      "model_name": "SUSTAIN_Model_3M",
      "predicted_risk": "Low",
      "probabilities": { "Low": 0.3742, "Medium": 0.2544, "High": 0.3714 },
      "model_status": "NOT_READY",
      "deployment_reason": "trained and tested only on SYNTHETIC rows ...; does not beat the persistence baseline on the test month"
    },
    {
      "horizon": "6M",
      "model_name": "SUSTAIN_Model_6M",
      "predicted_risk": "Low",
      "probabilities": { "Low": 0.3594, "Medium": 0.3346, "High": 0.3061 },
      "model_status": "NOT_READY",
      "deployment_reason": "trained and tested only on SYNTHETIC rows ...; test split could not be embargoed (optimistic)"
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
| `F_Category` written as an upper-case survey name (`"TRADE"`, `"FISHERIES & AQUACULTURE"`) | Converted with `category_mapping`, with a warning |
| Unknown or `null` category or district | Accepted. It is encoded as all-zero, with a warning |
| Missing key, extra or misspelled key, non-numeric or infinite value, bad `horizon` | **422** |
| Model files missing, or scikit-learn ≠ 1.6.1 | **503**, with a short message. Details go only to the server log |

### `POST /api/risk/identify`

This identifies the **current** risk class with SUSTAIN-HH-Risk-Rule v1.0 (notebook section 12, variant A). It is **rule-based, not ML**, and the rule is **provisional** (not yet validated by experts).

**Request.** All four keys are required. Each is `0`, `1` or `null` (not answered); `true`/`false` and `1.0`/`0.0` are also accepted as 1/0. Extra keys, missing keys and other values → **422**.

```json
{
  "business_not_running": 0,
  "no_profit_last_month": 1,
  "not_progressing_well": 1,
  "market_stress_any": null
}
```

**Response 200**

```json
{
  "risk_class": "High",
  "risk_ord": 2,
  "signal_count": 2,
  "unknown_count": 1,
  "reasons": [
    "No profit last month",
    "Not progressing well",
    "Not answered: market stress",
    "2 or more risk signals -> High"
  ],
  "rule_version": "SUSTAIN-HH-Risk-Rule v1.0 (provisional, requires expert validation)"
}
```

| Class | Rule |
|---|---|
| High | Business not running, **or** at least 2 of {no profit last month, not progressing well, market stress} |
| Medium | Business running and exactly one signal |
| Low | Business running and all three signals answered 0 |
| Unassigned | The class would differ between blanks = 0 and blanks = 1, **or** business status is blank (unless the signals alone already give High, as in the notebook) |

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

## Limitations

- **NOT_READY.** Both models are flagged `deployment_status: "NOT_READY"`. The API always returns `model_status` and `deployment_reason`. Never hide them in the UI.
- **Synthetic training data only.** All training and test rows come from a synthetic panel (58 households, Jan–Sep 2026). The source says these rows must not be used as evidence.
- **No persistent household ID in real data.** The 99 real rows (Jan–Mar 2026) cannot be linked across months, so no real 3- or 6-month outcome exists to train or test on.
- **The 3M model is below the persistence baseline.** On its embargoed test month, its macro-F1 is 0.303 [95% CI 0.194–0.407], while "predict the current class" scores 0.356.
- **The 6M result is optimistic.** Its macro-F1 is 0.430, against a baseline of 0.157, but its test split could not be embargoed.
- **The target rule is provisional.** SUSTAIN-HH-Risk-Rule v1.0 has not been validated by experts, and the market-tier thresholds are only partly verified. This affects both the predictions and `/identify`.
- **`/identify` follows the notebook code where it differs from the written rule.** If the business status is blank but 2 or more signals are 1, the class is High. The written rule in `metadata.json` would say Unassigned.
- **Coverage.** The models know only 4 districts and 7 categories. Transport & Logistics and Beauty & Wellness are unseen (they get a warning). Garment and Handicrafts are combined, and "Other" is mixed.
- **Small samples.** The 3M model has 102 training and 39 test rows; the 6M model has 77 and 39.
- **No per-prediction explanations yet.** Global feature importance is in `ml/Methodology_Results_Summary.md`.
- **The NDA sign-off for committing the models is pending supervisor approval.**

The steps needed before deployment are listed in `ml/Methodology_Results_Summary.md`: real data with a stable household ID covering at least 12 months, expert validation of the rule, and an embargoed real-data test that beats the persistence baseline.
