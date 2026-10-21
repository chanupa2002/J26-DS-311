export const BASE_PATH = "/api/risk"

export const UNAVAILABLE_MESSAGE_PREFIX = "Market-risk model is unavailable"

export const RISK_CLASSES = ["Low", "Medium", "High"]

// Badge colours per class (Low green, Medium amber, High red, Unassigned grey).
export const RISK_BADGE_CLASS = {
  Low: "border-transparent bg-emerald-600 text-white dark:bg-emerald-500/80",
  Medium: "border-transparent bg-amber-500 text-black dark:bg-amber-400/90",
  High: "border-transparent bg-red-600 text-white dark:bg-red-500/80",
  Unassigned: "border-transparent bg-muted text-muted-foreground",
}

// The 4 /identify signals. Every question is phrased so that "Yes" = 1 (a risk signal).
export const SIGNALS = [
  {
    key: "business_not_running",
    label: "Has the business stopped running?",
    hint: "Yes if the business is not running at this visit.",
  },
  {
    key: "no_profit_last_month",
    label: "No profit last month?",
    hint: "Yes if the business made no profit last month.",
  },
  {
    key: "not_progressing_well",
    label: "Business not progressing well?",
    hint: "Yes if the coach judged the business as not progressing well.",
  },
  {
    key: "market_stress_any",
    label: "Any market stress?",
    hint: "Yes if sales were below expected, input costs were high or inputs were unavailable.",
  },
]

export const BLANK = "blank"

export const SIGNAL_OPTIONS = [
  { value: "1", label: "Yes" },
  { value: "0", label: "No" },
  { value: BLANK, label: "Not answered" },
]

export const EMPTY_SIGNAL_FORM = Object.fromEntries(
  SIGNALS.map(({ key }) => [key, BLANK]),
)

export const IDENTIFY_EXAMPLES = [
  {
    label: "All OK",
    values: {
      business_not_running: "0",
      no_profit_last_month: "0",
      not_progressing_well: "0",
      market_stress_any: "0",
    },
  },
  {
    label: "Two signals",
    values: {
      business_not_running: "0",
      no_profit_last_month: "1",
      not_progressing_well: "1",
      market_stress_any: "0",
    },
  },
  {
    label: "Missing answer",
    values: {
      business_not_running: "0",
      no_profit_last_month: "1",
      not_progressing_well: BLANK,
      market_stress_any: "0",
    },
  },
]

export const RULE_NOTICE = {
  title: "Provisional rule · validation pending",
  reasons: [
    "The class comes from SUSTAIN-HH-Risk-Rule v1.0, a rule-based check with no ML model. The rule is provisional and has not yet been validated by experts.",
    "High: the business is not running, or 2 or more of the 3 signals are Yes. Medium: exactly one signal. Low: business running and all signals No.",
    "A blank answer is not treated as No. If blanks could change the class, the result is Unassigned and a follow-up visit is recommended.",
  ],
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
