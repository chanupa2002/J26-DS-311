export const BASE_PATH = "/api/risk"

export const UNAVAILABLE_MESSAGE_PREFIX = "Market-risk model is unavailable"

export const RISK_CLASSES = ["Low", "Medium", "High"]

export const RISK_BADGE_VARIANT = {
  Low: "secondary",
  Medium: "default",
  High: "destructive",
  Unassigned: "outline",
}

// [test_metrics key, label] in display order.
export const METRICS = [
  ["Macro_F1", "Macro-F1"],
  ["High_Recall", "High recall"],
  ["High_Precision", "High precision"],
  ["Balanced_Accuracy", "Balanced accuracy"],
  ["Accuracy", "Accuracy"],
]

export const ABOUT_DATA = {
  summary:
    "Trained on a synthetic panel (70 households, 9 categories). For demonstration only, until validated on real data.",
  paragraphs: [
    "The models were trained and tested on a synthetic panel of 70 households in 9 livelihood categories (Jan–Sep 2026). The panel mirrors the structure of the programme's monthly monitoring data.",
    "Real monitoring records cannot be used yet, because they have no stable household ID: the same household cannot be followed from one visit to the next, so no real 3- or 6-month outcome can be measured.",
    "All results on these pages are for demonstration. The models must be validated on real data, with a stable household ID and expert review of the risk rule, before they are used for any decision.",
  ],
}

// Walk-forward means over all test rows (backend RETRAIN_REPORT.md section 5).
export const TRADE_OFF = {
  decision: "Promoted for coverage, trade-off accepted (2026-10-21)",
  reason:
    "Consistency with the team's cleaned data and coverage of all 9 livelihood categories. The agreed promotion bar was not met.",
  rows: [
    { horizon: "3M", metric: "Macro-F1", previous: 0.35, current: 0.331 },
    { horizon: "3M", metric: "High recall", previous: 0.397, current: 0.307 },
    { horizon: "6M", metric: "Macro-F1", previous: 0.422, current: 0.429 },
    { horizon: "6M", metric: "High recall", previous: 0.876, current: 0.771 },
  ],
}

// Shortened from the backend README "Limitations". The first entries are always shown.
export const LIMITATIONS = [
  "Both models are prototypes awaiting validation (model_status NOT_READY). Do not use the predictions for real decisions.",
  "Trained and tested on synthetic data only (70 households, 9 categories, Jan–Sep 2026). The source says these rows must not be used as evidence.",
  "Version 2.0 catches fewer High cases than version 1.0: walk-forward High recall fell from 0.397 to 0.307 (3M) and from 0.876 to 0.771 (6M).",
  "Real households have no persistent ID, so no real 3- or 6-month outcome exists to train or test on.",
  "Single-month test results are uncertain: the 3M confidence interval is wide, and the 6M test split could not be embargoed (optimistic).",
  "The target rule (SUSTAIN-HH-Risk-Rule v1.0) is provisional and not validated by experts. This also affects Risk Check.",
  "Only 4 districts. Garment and Handicrafts are combined, \"Other\" is mixed, and Beauty & Wellness and Transport & Logistics have no market evidence or grant date.",
  "Small samples: 3M has 127 training and 49 test rows; 6M has 91 and 47.",
  "Gender features are model inputs. A fairness check on real data is needed before any use.",
  "SHAP factors show what drives the model, not real-world causes. A blank input is not neutral: it is filled with the median.",
]

export const LIMITATIONS_SHOWN = 3
