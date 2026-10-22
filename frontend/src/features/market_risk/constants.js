export const BASE_PATH = "/api/risk"

// Fixed starts of the backend 503 messages (api() does not expose the status; FRONTEND_PLAN.md §5).
export const UNAVAILABLE_MESSAGE_PREFIXES = [
  "Market-risk model is unavailable",
  "Market-context data is unavailable",
]

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

// ------------------------------------------------------------ Future Risk ----

export const TOP_K = 5

export const HORIZON_OPTIONS = [
  { value: "both", label: "Both (3M and 6M)" },
  { value: "3M", label: "3 months (3M)" },
  { value: "6M", label: "6 months (6M)" },
]

export const CATEGORICAL_FEATURES = ["F_Category", "F_District"]

// Form sections for the 53 features. Any feature from /model-info that is not
// listed here is shown in an extra "Other" section, so nothing can be lost.
export const FEATURE_GROUPS = [
  {
    key: "signals",
    title: "Current signals",
    description: "Answers at this visit and the current risk class from the rule.",
    features: [
      "F_Business_Not_Running_t",
      "F_No_Profit_Last_Month_t",
      "F_Not_Progressing_Well_t",
      "F_Revenue_Lowest_Band_t",
      "F_Sales_Below_Expected_t",
      "F_High_Input_Cost_t",
      "F_Inputs_Unavailable_t",
      "F_Market_Stress_Any_t",
      "F_Risk_Ord_t",
      "F_Risk_Signal_Count_t",
      "F_Risk_Unknown_t",
    ],
  },
  {
    key: "business",
    title: "Business",
    description: "Operating conditions at this visit.",
    features: [
      "F_Hours_Ord_t",
      "F_Records_Ord_t",
      "F_Grant_Status_Ord_t",
      "F_Borrowed_t",
      "F_Saved_t",
      "F_Cyclone_Affected_t",
      "F_Asset_Lost_t",
      "F_Storage_Transport_Issue_t",
      "F_Machinery_Issue_t",
      "F_Natural_Disaster_t",
    ],
  },
  {
    key: "participant",
    title: "Participant",
    description: "Age and gender of the participant and household head.",
    features: ["F_Age", "F_Female_Participant", "F_Female_Head"],
  },
  {
    key: "history",
    title: "History",
    description: "The same household's earlier visits only.",
    features: [
      "F_Months_Since_Prev_Visit",
      "F_Prev_Risk_Ord",
      "F_Prev_No_Profit_Last_Month",
      "F_Prev_Market_Stress_Any",
      "F_Prev_Not_Progressing_Well",
      "F_Prev_Business_Not_Running",
      "F_Risk_Change_vs_Prev",
      "F_Tenure_Months",
      "F_N_Prior_Visits",
      "F_Risk_Mean_3M_Window",
      "F_NoProfit_Rate_3M_Window",
      "F_MarketStress_Rate_3M_Window",
      "F_High_Count_6M_Window",
      "F_Months_Since_Grant",
    ],
  },
  {
    key: "location",
    title: "Category, visit month & District",
    description: "Category and visit month also fill the market and macro values automatically.",
    features: ["F_Category", "F_District"],
  },
]

// Market (category x month) and macro (month) features: never typed in. They come from
// GET /api/risk/market-context (step F5) and are shown read-only in the Advanced section.
export const CONTEXT_GROUPS = [
  {
    key: "market",
    title: "Market",
    description: "Category market-price pressure and volatility (from category and month).",
    features: [
      "F_Mkt_Pressure_t",
      "F_Mkt_Volatility_t",
      "F_Mkt_Pressure_Change_1M",
      "F_Mkt_Volatility_Change_1M",
      "F_Mkt_Pressure_Tier_Ord_t",
      "F_Mkt_Volatility_Tier_Ord_t",
      "F_Mkt_Pressure_Tier_Ord_t_minus_1",
      "F_Mkt_Evidence_Missing",
    ],
  },
  {
    key: "macro",
    title: "Macro",
    description: "National inflation, food prices and diesel price (from month).",
    features: [
      "F_Macro_CCPI_YoY_t",
      "F_Macro_CCPI_YoY_Change_1M",
      "F_Macro_Food_Index_Change_1M_pct",
      "F_Macro_Diesel_t",
      "F_Macro_Diesel_Change_1M_pct",
    ],
  },
]

export const CONTEXT_FEATURES = CONTEXT_GROUPS.flatMap((group) => group.features)

export const VISIT_MONTH_HELP =
  "The month of this visit; the model predicts 3 and 6 months after it."

export const MARKET_CONTEXT_TEXT = {
  choose: "Choose a category and visit month to fill these 13 values automatically.",
  noEvidence:
    "No market price data for this category in this month. Only national indicators were filled; the model handles the blanks.",
  outOfRange: "No market or national data for this month, so these values stay empty. Nothing is estimated.",
}

// Risk Check router state -> feature names (decision Q6).
export const RISK_CHECK_SIGNAL_FEATURES = {
  business_not_running: "F_Business_Not_Running_t",
  no_profit_last_month: "F_No_Profit_Last_Month_t",
  not_progressing_well: "F_Not_Progressing_Well_t",
  market_stress_any: "F_Market_Stress_Any_t",
}
export const RISK_CHECK_COUNT_FEATURES = {
  risk_ord: "F_Risk_Ord_t",
  signal_count: "F_Risk_Signal_Count_t",
  unknown_count: "F_Risk_Unknown_t",
}

export const PROBABILITY_BAR_CLASS = {
  Low: "bg-emerald-600 dark:bg-emerald-500",
  Medium: "bg-amber-500 dark:bg-amber-400",
  High: "bg-red-600 dark:bg-red-500",
}

export const SHAP_COLORS = { towardsHigh: "#dc2626", awayFromHigh: "#16a34a" }

export const FUTURE_RISK_NOTICE_REASON =
  "Predictions come from prototype models trained on a synthetic panel. They show what the model would say, not what will happen to a real household."

// Coded features shown as selects. Values are the exact numbers the model was
// trained with (sent as numbers); the blank option is sent as null.
const YES_NO = [
  { value: "1", label: "Yes" },
  { value: "0", label: "No" },
]
const RISK_LEVELS = [
  { value: "0", label: "Low" },
  { value: "1", label: "Medium" },
  { value: "2", label: "High" },
]
// Category_Month_Table coding: Low=0, Medium=1, High=2; "Insufficient Evidence" is blank.
const MARKET_TIERS = RISK_LEVELS

export const FEATURE_OPTIONS = {
  ...Object.fromEntries(
    [
      "F_Business_Not_Running_t",
      "F_No_Profit_Last_Month_t",
      "F_Not_Progressing_Well_t",
      "F_Revenue_Lowest_Band_t",
      "F_Sales_Below_Expected_t",
      "F_High_Input_Cost_t",
      "F_Inputs_Unavailable_t",
      "F_Market_Stress_Any_t",
      "F_Borrowed_t",
      "F_Saved_t",
      "F_Cyclone_Affected_t",
      "F_Female_Head",
      "F_Asset_Lost_t",
      "F_Storage_Transport_Issue_t",
      "F_Machinery_Issue_t",
      "F_Natural_Disaster_t",
      "F_Prev_No_Profit_Last_Month",
      "F_Prev_Market_Stress_Any",
      "F_Prev_Not_Progressing_Well",
      "F_Prev_Business_Not_Running",
      "F_Mkt_Evidence_Missing",
    ].map((name) => [name, { options: YES_NO, blank: "Not answered" }]),
  ),
  F_Female_Participant: {
    options: [
      { value: "1", label: "Female" },
      { value: "0", label: "Male" },
    ],
    blank: "Not answered",
  },
  F_Risk_Ord_t: { options: RISK_LEVELS, blank: "Not answered (Unassigned)" },
  F_Prev_Risk_Ord: { options: RISK_LEVELS, blank: "Not answered (no previous visit)" },
  F_Hours_Ord_t: {
    options: [
      { value: "1", label: "1–4 hours a day" },
      { value: "2", label: "5–8 hours a day" },
      { value: "3", label: "9+ hours a day" },
    ],
    blank: "Not answered",
  },
  F_Records_Ord_t: {
    options: [
      { value: "0", label: "No records" },
      { value: "1", label: "A few times a month" },
      { value: "2", label: "Once or twice a week" },
      { value: "3", label: "Daily" },
    ],
    blank: "Not answered",
  },
  F_Grant_Status_Ord_t: {
    options: [
      { value: "0", label: "Not received" },
      { value: "1", label: "Received, not fully used" },
      { value: "2", label: "Fully used, bills not settled" },
      { value: "3", label: "Received, fully used" },
    ],
    blank: "Not answered",
  },
  F_Mkt_Pressure_Tier_Ord_t: { options: MARKET_TIERS, blank: "Insufficient evidence" },
  F_Mkt_Volatility_Tier_Ord_t: { options: MARKET_TIERS, blank: "Insufficient evidence" },
  F_Mkt_Pressure_Tier_Ord_t_minus_1: { options: MARKET_TIERS, blank: "Insufficient evidence" },
}

export const SHAP_NOTE = "SHAP shows what drives the model, not real-world causes."
