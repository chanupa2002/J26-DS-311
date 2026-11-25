Text for the team lead to paste into docs/CONTRACTS.md §2, replacing the market_risk predict_market_risk TBD row.

```
| market_risk | predict_market_risk | PredictRequest or dict: {"horizon": "3M" \| "6M" \| "both" (default "both"), "features": {all 53 F_* keys from GET /api/risk/model-info; every key required, values may be null; F_Category accepts trained levels or upper-case survey names}} | PredictResponse: {"horizon", "predictions": [{"horizon", "model_name", "predicted_risk": "Low" \| "Medium" \| "High", "probabilities": {"Low", "Medium", "High"}, "model_status", "deployment_reason"}], "warnings": [str], "placeholder": false}. Raises pydantic ValidationError on bad input; FileNotFoundError / RuntimeError if a model cannot be loaded | Implemented (models NOT_READY: synthetic training data; show model_status and deployment_reason to users) |
| market_risk | get_model_info | horizon: "3M" \| "6M" \| None (None = both) | ModelInfoResponse: {"models": [{"horizon", "model_name", "horizon_months", "algorithm", "classes", "model_status", "deployment_reason", "data_basis", "target_generation_method", "validation_methodology", "test_metrics", "persistence_baseline_test_macro_f1", "training_period", "created"}], "features": [{"name", "type", "description"}], "categorical_levels": {"F_Category": [...], "F_District": [...]}}. Reads metadata only | Implemented |
| market_risk | identify_current_risk | IdentifyRequest or dict: {"business_not_running", "no_profit_last_month", "not_progressing_well", "market_stress_any"}; every key required, each 0 \| 1 \| null; extra keys rejected | IdentifyResponse: {"risk_class": "Low" \| "Medium" \| "High" \| "Unassigned", "risk_ord": 0 \| 1 \| 2 \| null, "signal_count", "unknown_count", "reasons": [str], "rule_version": "SUSTAIN-HH-Risk-Rule v1.0 (provisional, requires expert validation)", "best_case_class": "Low" \| "Medium" \| "High" (blanks = 0, blank business = running), "worst_case_class": "Low" \| "Medium" \| "High" (blanks = 1, blank business = not running), "possible_range": str (e.g. "Medium-High", or the single class), "follow_up_needed": bool (true when Unassigned)}; for assigned cases best_case_class = worst_case_class = risk_class. Rule-based (no ML); risk_ord / signal_count / unknown_count can be used as F_Risk_Ord_t / F_Risk_Signal_Count_t / F_Risk_Unknown_t | Implemented (rule not yet validated by experts) |
| market_risk | explain_market_risk | ExplainRequest or dict: the predict_market_risk input plus "top_k": int 1..20 (default 5) | ExplainResponse: {"horizon", "explanations": [{"horizon", "model_name", "predicted_risk", "explained_class", "base_value", "probability", "top_factors": [{"feature", "label", "value", "contribution", "direction": "increases risk" \| "decreases risk"}], "other_features_contribution", "high_risk_probability", "high_risk_factors": [same shape], "model_status", "deployment_reason"}], "warnings": [str], "note": str}. SHAP contributions of the 53 features; base_value + all contributions = probability. Raises pydantic ValidationError on bad input; FileNotFoundError / RuntimeError / ImportError if a model, shap or the explanation is unavailable | Implemented (SHAP explains the model, not real-world causes; models NOT_READY) |
| market_risk | compute_history_features | HistoryFeaturesRequest or dict: {"current_visit": {"visit_date": "YYYY-MM-DD", "business_running", "profit_last_month", "progressing_well", "market_stress" (each 1 \| 0 \| null), "grant_date": "YYYY-MM-DD" \| null}, "previous_visits": [0..12 × {"month": "YYYY-MM", same 4 answers}]}; no household IDs or names (extra keys rejected) | HistoryFeaturesResponse: {"month", "features": {the 14 history F_* features: F_Months_Since_Prev_Visit, 5 × F_Prev_*, F_Risk_Change_vs_Prev, F_Tenure_Months, F_N_Prior_Visits, 4 window features, F_Months_Since_Grant; null when not defined}, "visits": [{"month", "risk_class", "is_current"}], "rule_version"}. Same code as training; each visit's class from identify_current_risk. Raises pydantic ValidationError (HTTP 422) for a bad date/month, duplicate months, a previous visit not before the visit_date month, grant_date after visit_date, or more than 12 previous visits. HTTP: POST /api/risk/history-features | Implemented (reproduces the training features on 550 of 550 rows) |
| market_risk | get_market_context | category: str (trained F_Category level, any case, or upper-case survey name), month: str "YYYY-MM" | MarketContextResponse: {"category", "category_key", "month", "in_data_range": bool, "features": {the 8 F_Mkt_* and 5 F_Macro_* features, null without evidence}, "evidence_missing": bool, "source_note": str, "note": str \| null, "available_months": [str]}. Same join and formulas as training (aggregated public indicators only). A month outside the data returns every value null with in_data_range false (never guessed). Raises UnknownCategoryError (ValueError) for an unknown category, ValueError for a badly formatted month, FileNotFoundError if the lookup file is missing. HTTP: GET /api/risk/market-context (422 unknown category or bad month) | Implemented |
```

---

# market_risk v2 API (for the frontend team)

Base path: `/api/risk/v2`. All examples are synthetic. Every 200 response has `is_synthetic`, `model_version: "v2"` and `note`. Show "Simulated" when `is_synthetic` is true.

| Status | Meaning |
|---|---|
| 404 | Unknown `household_key` |
| 422 | Invalid request, unknown district or category |
| 503 | Artifacts missing, scikit-learn version mismatch, or a month outside the market data. `detail` holds the message |

## POST /risk/visit

Nothing is stored. Answers are `0`, `1` or `null` unless noted: `revenue_band` 0-3, `hours_band` 1-3, `record_keeping` 0-3, `grant_status` 0-3. Omitted answers count as `null`.

```json
{
  "monitoring_period": "2026-06",
  "district": "Ampara",
  "category": "AGRICULTURE & PLANTATION CROPS",
  "is_synthetic": true,
  "household_key": "SIM-HH-001",
  "business_running": 1,
  "profit": 0,
  "coach_progressing": 1,
  "revenue_band": 1,
  "hours_band": 2,
  "record_keeping": 1,
  "borrowed_money": 0,
  "saved_money": 0,
  "grant_status": 3,
  "problem_sales_low": 1,
  "problem_input_cost": 0,
  "problem_input_unavailable": 0
}
```

- Synthetic visits need `household_key` (`SIM-HH-…`). Earlier stored visits are used unless `previous_visits` is sent. `previous_visits: []` means a first visit.
- Each `previous_visits` item has `monitoring_period`, `business_running`, `profit`, `coach_progressing`, `revenue_band`, `problem_sales_low`, `problem_input_cost` and `problem_input_unavailable`. Months must be earlier than the visit.
- Real visits send `is_synthetic: false`, with no `household_key` or `previous_visits`. The response has `note: "indicative - no history"`.

Response (`shap_top_factors` normally has 5 items; 1 is shown here):

```json
{
  "is_synthetic": true,
  "model_version": "v2",
  "note": null,
  "household_key": "SIM-HH-001",
  "monitoring_period": "2026-06",
  "district": "Ampara",
  "category": "AGRICULTURE & PLANTATION CROPS",
  "grant_status": 3,
  "grant_status_label": "Fully used",
  "current_risk": {
    "risk_class": "High",
    "risk_ord": 2,
    "signal_count": 2,
    "reasons": ["no profit last month", "market stress (low sales / input cost / inputs unavailable)"],
    "rule_version": "SUSTAIN-HH-Risk-Rule v1.0 (provisional, requires expert validation)"
  },
  "predictions": {
    "3M": {"p_high": 0.268, "predicted_class": "Medium", "alert": false, "alert_threshold": 0.47521950949935643, "reliability_note": null},
    "6M": {"p_high": 0.292, "predicted_class": "Low", "alert": null, "alert_threshold": null,
           "reliability_note": "Indicative only: in testing this 6M model did not beat assuming risk stays the same."}
  },
  "shap_base_value": 0.5000000000000003,
  "shap_top_factors": [
    {"feature": "high_count_6m", "label": "High-risk visits in the last 6 months", "value": "5", "raw_value": 5.0,
     "group": "History", "contribution": -0.050743406265582866}
  ],
  "market": {"pressure": 0.5803769493616378, "level": "Moderate", "price_month_used": "2026-06",
             "series": "PPI A: Agriculture", "basis": "quarterly+annual"},
  "warnings": []
}
```

`grant_status` echoes the sent or stored code (0-3 or `null`). `grant_status_label` is its codebook label: 0 "Not received", 1 "Not fully used", 2 "Used, bills not settled", 3 "Fully used" (`null` when not answered). It is the same mapping the SHAP factor values use. Show the label; do not map codes in the frontend.

`group` is one of Business, Household shock, History, Market or Current risk. A positive `contribution` pushes the 3-month P(High) up. `alert: null` means no alert threshold exists, so show "no alert available", not "no alert".

## GET /risk/households?month=2026-06

`month` is optional; the default is the latest month. Simulated households only.

```json
{
  "is_synthetic": true, "model_version": "v2", "note": "Simulated household data.",
  "month": "2026-06", "count": 87,
  "households": [
    {"household_key": "SIM-HH-001", "monitoring_period": "2026-06", "district": "Ampara",
     "category": "AGRICULTURE & PLANTATION CROPS", "is_synthetic": true,
     "grant_status": 3, "grant_status_label": "Fully used", "current_risk": "Unassigned",
     "reasons": ["form incomplete: profit unknown - ask SDO"],
     "predicted_3m": "Low", "p_high_3m": 0.198, "alert_3m": false, "market_level": "Moderate"}
  ]
}
```

`reasons` are the rule reasons for `current_risk` (the same list as `current_risk.reasons` in a visit response). `grant_status` and `grant_status_label` work as in `/risk/visit`.

## GET /risk/household/SIM-HH-001

Returns `household_key`, `latest_visit` (same shape as the `/risk/visit` response) and `timeline`, oldest first:

```json
{"monitoring_period": "2026-01", "current_risk": "High",
 "reasons": ["no profit last month", "coach: not progressing", "market stress (low sales / input cost / inputs unavailable)"],
 "predicted_3m": "High", "p_high_3m": 0.694, "alert_3m": true, "market_level": "Normal"}
```

## GET /market/districts?month=2026-09

`month` is optional. Returns 225 rows (25 districts × 9 categories). `market_pressure_level` is Normal, Moderate, High or `null`.

```json
{
  "is_synthetic": false, "model_version": "v2", "note": "Public market indicators; no household data.",
  "month": "2026-09", "available_months": ["2026-01", "...", "2026-09"], "count": 225,
  "rows": [
    {"district": "Ampara", "category": "AGRICULTURE & PLANTATION CROPS", "market_pressure": -0.6216958780479793,
     "market_pressure_level": "Normal", "price_month_used": "2026-08", "series": "PPI A: Agriculture",
     "ipa_basis": "quarterly+annual", "dmc_affected_families": 39.0}
  ]
}
```

## GET /model/evidence

Returns `models`, `alert_thresholds`, `comparisons`, `results` (full result tables), `shap_group_share`, `threshold_register` and `limitations`. A `comparisons` item:

```json
{"name": "6M warning, grouped CV", "metric": "ROC_AUC", "model": 0.556, "persistence": 0.592, "model_better": false}
```

Swagger: the 5 v2 endpoints are listed once, under the "Market Risk" tag.
