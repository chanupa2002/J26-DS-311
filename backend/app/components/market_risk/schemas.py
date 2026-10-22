"""Request and response data shapes for Explainable Market-Risk Prediction, Recommendation and Decision Dashboard."""
import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Horizon = Literal["3M", "6M"]
HorizonOption = Literal["3M", "6M", "both"]
RiskClass = Literal["Low", "Medium", "High"]
CurrentRiskClass = Literal["Low", "Medium", "High", "Unassigned"]
SignalValue = Literal[0, 1] | None

# Values from sample_data/predict_request_example.json (synthetic example row).
EXAMPLE_FEATURES: dict[str, float | str | None] = {
    "F_Business_Not_Running_t": 0,
    "F_No_Profit_Last_Month_t": 1,
    "F_Not_Progressing_Well_t": 0,
    "F_Revenue_Lowest_Band_t": None,
    "F_Sales_Below_Expected_t": None,
    "F_High_Input_Cost_t": 0,
    "F_Inputs_Unavailable_t": 0,
    "F_Market_Stress_Any_t": None,
    "F_Risk_Ord_t": None,
    "F_Risk_Signal_Count_t": 1,
    "F_Risk_Unknown_t": 1,
    "F_Hours_Ord_t": 1,
    "F_Records_Ord_t": 0,
    "F_Grant_Status_Ord_t": 1,
    "F_Borrowed_t": 0,
    "F_Saved_t": 0,
    "F_Cyclone_Affected_t": 0,
    "F_Female_Head": 1,
    "F_Asset_Lost_t": 0,
    "F_Storage_Transport_Issue_t": 0,
    "F_Machinery_Issue_t": 0,
    "F_Natural_Disaster_t": 0,
    "F_Age": 37,
    "F_Female_Participant": 1,
    "F_Months_Since_Prev_Visit": 2,
    "F_Prev_Risk_Ord": 0,
    "F_Prev_No_Profit_Last_Month": 0,
    "F_Prev_Market_Stress_Any": 0,
    "F_Prev_Not_Progressing_Well": 0,
    "F_Prev_Business_Not_Running": 0,
    "F_Risk_Change_vs_Prev": None,
    "F_Tenure_Months": 5,
    "F_N_Prior_Visits": 4,
    "F_Risk_Mean_3M_Window": 0,
    "F_NoProfit_Rate_3M_Window": 0.5,
    "F_MarketStress_Rate_3M_Window": 0,
    "F_High_Count_6M_Window": 0,
    "F_Months_Since_Grant": 6.8003,
    "F_Mkt_Pressure_t": None,
    "F_Mkt_Volatility_t": None,
    "F_Mkt_Pressure_Change_1M": None,
    "F_Mkt_Volatility_Change_1M": None,
    "F_Mkt_Pressure_Tier_Ord_t": None,
    "F_Mkt_Volatility_Tier_Ord_t": None,
    "F_Mkt_Pressure_Tier_Ord_t_minus_1": None,
    "F_Mkt_Evidence_Missing": 1,
    "F_Macro_CCPI_YoY_t": 6.8,
    "F_Macro_CCPI_YoY_Change_1M": 1.3,
    "F_Macro_Food_Index_Change_1M_pct": 4.4921,
    "F_Macro_Diesel_t": 406.17,
    "F_Macro_Diesel_Change_1M_pct": 3.6571,
    "F_Category": "Other",
    "F_District": "Badulla",
}


class HealthResponse(BaseModel):
    component: str
    status: str


class MarketRiskFeatures(BaseModel):
    """The 53 engineered features, in metadata.json feature_names_in_order.

    Every key is required; any value may be null (numeric nulls are
    median-imputed by the model pipeline). Unknown keys are rejected.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    # Current-visit household signals (1/0)
    F_Business_Not_Running_t: float | None = Field(description="1 if the business was not running at visit t, else 0.")
    F_No_Profit_Last_Month_t: float | None = Field(description="1 if no profit last month at visit t, else 0.")
    F_Not_Progressing_Well_t: float | None = Field(description="1 if the business is not progressing well at visit t, else 0.")
    F_Revenue_Lowest_Band_t: float | None = Field(description="1 if revenue is in the lowest band at visit t, else 0.")
    F_Sales_Below_Expected_t: float | None = Field(description="1 if sales were below expected at visit t, else 0.")
    F_High_Input_Cost_t: float | None = Field(description="1 if input costs were high at visit t, else 0.")
    F_Inputs_Unavailable_t: float | None = Field(description="1 if inputs were unavailable at visit t, else 0.")
    F_Market_Stress_Any_t: float | None = Field(description="1 if any market-stress signal at visit t, else 0.")
    F_Risk_Ord_t: float | None = Field(description="Household risk class at t (rule v1.0): 0=Low, 1=Medium, 2=High.")
    F_Risk_Signal_Count_t: float | None = Field(description="Count of the three risk signals (no profit, not progressing, market stress) equal to 1 at t.")
    F_Risk_Unknown_t: float | None = Field(description="Count of those three risk signals left blank at t.")
    # Operating conditions at t
    F_Hours_Ord_t: float | None = Field(description="Hours worked per day last month: 1=1-4, 2=5-8, 3=9+.")
    F_Records_Ord_t: float | None = Field(description="Business record keeping: 0=none, 1=a few times a month, 2=once or twice a week, 3=daily.")
    F_Grant_Status_Ord_t: float | None = Field(description="Grant status: 0=not received, 1=not fully utilized, 2=utilized but bills not settled, 3=fully utilized.")
    F_Borrowed_t: float | None = Field(description="Borrowed money for the business last month: Yes=1, No=0.")
    F_Saved_t: float | None = Field(description="Able to save money last month: Yes=1, No=0.")
    F_Cyclone_Affected_t: float | None = Field(description="Affected by the cyclone: Yes=1, No=0.")
    F_Female_Head: float | None = Field(description="Household headed by a female: Yes=1, No=0.")
    F_Asset_Lost_t: float | None = Field(description="Lost a livelihood asset: Yes=1, No=0.")
    F_Storage_Transport_Issue_t: float | None = Field(description="Storage or transportation issues: Yes=1, No=0.")
    F_Machinery_Issue_t: float | None = Field(description="Machinery or equipment not functioning: Yes=1, No=0.")
    F_Natural_Disaster_t: float | None = Field(description="Affected by a natural disaster: Yes=1, No=0.")
    # Participant
    F_Age: float | None = Field(description="Participant age in years.")
    F_Female_Participant: float | None = Field(description="Participant gender: Female=1, Male=0.")
    # Household history (same household, earlier visits only)
    F_Months_Since_Prev_Visit: float | None = Field(description="Months since the household's previous visit.")
    F_Prev_Risk_Ord: float | None = Field(description="Risk class (0/1/2) at the previous visit.")
    F_Prev_No_Profit_Last_Month: float | None = Field(description="No-profit signal (1/0) at the previous visit.")
    F_Prev_Market_Stress_Any: float | None = Field(description="Market-stress signal (1/0) at the previous visit.")
    F_Prev_Not_Progressing_Well: float | None = Field(description="Not-progressing signal (1/0) at the previous visit.")
    F_Prev_Business_Not_Running: float | None = Field(description="Business-not-running signal (1/0) at the previous visit.")
    F_Risk_Change_vs_Prev: float | None = Field(description="F_Risk_Ord_t minus F_Prev_Risk_Ord.")
    F_Tenure_Months: float | None = Field(description="Months since the household's first visit.")
    F_N_Prior_Visits: float | None = Field(description="Number of earlier visits by the household.")
    F_Risk_Mean_3M_Window: float | None = Field(description="Mean risk class over visits in months [t-2, t].")
    F_NoProfit_Rate_3M_Window: float | None = Field(description="Share of visits in months [t-2, t] with no profit.")
    F_MarketStress_Rate_3M_Window: float | None = Field(description="Share of visits in months [t-2, t] with market stress.")
    F_High_Count_6M_Window: float | None = Field(description="Number of High-risk visits in months [t-5, t].")
    F_Months_Since_Grant: float | None = Field(description="Months since the grant date reported at or before t.")
    # Category market evidence (month t and t-1)
    F_Mkt_Pressure_t: float | None = Field(description="Category market-price pressure at month t (adverse direction).")
    F_Mkt_Volatility_t: float | None = Field(description="Category market-price volatility at month t.")
    F_Mkt_Pressure_Change_1M: float | None = Field(description="Market pressure at t minus t-1.")
    F_Mkt_Volatility_Change_1M: float | None = Field(description="Market volatility at t minus t-1.")
    F_Mkt_Pressure_Tier_Ord_t: float | None = Field(description="Category pressure tier at t (ordinal).")
    F_Mkt_Volatility_Tier_Ord_t: float | None = Field(description="Category volatility tier at t (ordinal).")
    F_Mkt_Pressure_Tier_Ord_t_minus_1: float | None = Field(description="Category pressure tier at t-1 (ordinal).")
    F_Mkt_Evidence_Missing: float | None = Field(description="1 if market pressure at t is missing, else 0.")
    # National macro indicators
    F_Macro_CCPI_YoY_t: float | None = Field(description="CCPI year-on-year inflation at month t (%).")
    F_Macro_CCPI_YoY_Change_1M: float | None = Field(description="CCPI YoY inflation at t minus t-1 (percentage points).")
    F_Macro_Food_Index_Change_1M_pct: float | None = Field(description="CCPI food index change from t-1 to t (%).")
    F_Macro_Diesel_t: float | None = Field(description="Auto diesel price at month t.")
    F_Macro_Diesel_Change_1M_pct: float | None = Field(description="Auto diesel price change from t-1 to t (%).")
    # Categorical
    F_Category: str | None = Field(description="Livelihood category: a trained level (see /api/risk/model-info) or an upper-case survey name, which is converted.")
    F_District: str | None = Field(description="District: a trained level (see /api/risk/model-info).")


class PredictRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"horizon": "both", "features": EXAMPLE_FEATURES}]
        },
    )

    horizon: HorizonOption = "both"
    features: MarketRiskFeatures


class ExplainRequest(PredictRequest):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"horizon": "both", "top_k": 5, "features": EXAMPLE_FEATURES}]
        },
    )

    top_k: int = Field(default=5, ge=1, le=20, description="Number of top factors to return per horizon.")


class RiskProbabilities(BaseModel):
    Low: float
    Medium: float
    High: float


class HorizonPrediction(BaseModel):
    horizon: Horizon
    model_name: str
    predicted_risk: RiskClass
    probabilities: RiskProbabilities
    model_status: str
    deployment_reason: str


class PredictResponse(BaseModel):
    horizon: HorizonOption
    predictions: list[HorizonPrediction]
    warnings: list[str] = Field(default_factory=list)
    placeholder: bool


class ExplanationFactor(BaseModel):
    feature: str
    label: str = Field(description="Plain-English meaning of the feature.")
    value: float | str | None = Field(description="Input value the model used (after category conversion); null if blank.")
    contribution: float = Field(description="SHAP contribution to the probability of the explained class.")
    direction: Literal["increases risk", "decreases risk"] = Field(
        description="Effect on the expected risk score 0*P(Low) + 1*P(Medium) + 2*P(High)."
    )


class HorizonExplanation(BaseModel):
    horizon: Horizon
    model_name: str
    predicted_risk: RiskClass
    explained_class: RiskClass
    base_value: float = Field(description="Average model probability of the explained class (SHAP expected value).")
    probability: float = Field(description="Model probability of the explained class for this household.")
    top_factors: list[ExplanationFactor]
    other_features_contribution: float = Field(description="Sum of contributions of all features not in top_factors.")
    high_risk_probability: float
    high_risk_factors: list[ExplanationFactor] = Field(description="Top factors for the High class, always included.")
    model_status: str
    deployment_reason: str


class ExplainResponse(BaseModel):
    horizon: HorizonOption
    explanations: list[HorizonExplanation]
    warnings: list[str] = Field(default_factory=list)
    note: str


class ModelSummary(BaseModel):
    horizon: Horizon
    model_name: str
    horizon_months: int
    algorithm: str
    classes: list[RiskClass]
    model_status: str
    deployment_reason: str
    data_basis: str | None = None
    target_generation_method: str | None = None
    validation_methodology: str | None = None
    test_metrics: dict[str, float] = Field(default_factory=dict)
    persistence_baseline_test_macro_f1: float | None = None
    training_period: dict[str, str] = Field(default_factory=dict)
    created: str | None = None


class FeatureInfo(BaseModel):
    name: str
    type: Literal["numeric", "categorical"]
    description: str


class ModelInfoResponse(BaseModel):
    models: list[ModelSummary]
    features: list[FeatureInfo]
    categorical_levels: dict[str, list[str]]


class IdentifyRequest(BaseModel):
    """Current-visit signals for SUSTAIN-HH-Risk-Rule v1.0. Each is 0, 1 or null (blank)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "business_not_running": 0,
                    "no_profit_last_month": 1,
                    "not_progressing_well": 0,
                    "market_stress_any": None,
                }
            ]
        },
    )

    business_not_running: SignalValue = Field(description="1 if the business is not running at this visit, 0 if running, null if not answered.")
    no_profit_last_month: SignalValue = Field(description="1 if no profit last month, 0 if profit, null if not answered.")
    not_progressing_well: SignalValue = Field(description="1 if the business is not progressing well, 0 otherwise, null if not answered.")
    market_stress_any: SignalValue = Field(description="1 if any market stress (sales below expected, high input cost or inputs unavailable), 0 if none, null if not answered.")


class IdentifyResponse(BaseModel):
    risk_class: CurrentRiskClass
    risk_ord: int | None = Field(description="0/1/2 for Low/Medium/High, null if Unassigned; usable as F_Risk_Ord_t.")
    signal_count: int = Field(description="Number of the three stress signals equal to 1; usable as F_Risk_Signal_Count_t.")
    unknown_count: int = Field(description="Number of the three stress signals left blank; usable as F_Risk_Unknown_t.")
    reasons: list[str]
    rule_version: str
    best_case_class: RiskClass = Field(description="Class if every blank signal is 0 and a blank business status means running.")
    worst_case_class: RiskClass = Field(description="Class if every blank signal is 1 and a blank business status means not running (High).")
    possible_range: str = Field(description="'<best>-<worst>' (e.g. 'Medium-High'), or the single class when both are equal.")
    follow_up_needed: bool = Field(description="True when risk_class is Unassigned: a follow-up visit should fill the blank answers.")


class MarketContextFeatures(BaseModel):
    """The 13 F_* features that depend only on (category, month) or on month. null = no evidence."""

    F_Mkt_Pressure_t: float | None
    F_Mkt_Volatility_t: float | None
    F_Mkt_Pressure_Change_1M: float | None
    F_Mkt_Volatility_Change_1M: float | None
    F_Mkt_Pressure_Tier_Ord_t: float | None
    F_Mkt_Volatility_Tier_Ord_t: float | None
    F_Mkt_Pressure_Tier_Ord_t_minus_1: float | None
    F_Mkt_Evidence_Missing: int | None
    F_Macro_CCPI_YoY_t: float | None
    F_Macro_CCPI_YoY_Change_1M: float | None
    F_Macro_Food_Index_Change_1M_pct: float | None
    F_Macro_Diesel_t: float | None
    F_Macro_Diesel_Change_1M_pct: float | None


class MarketContextResponse(BaseModel):
    category: str = Field(description="Trained F_Category level the input resolved to.")
    category_key: str = Field(description="Source category key used for the market lookup.")
    month: str = Field(description="Requested month, YYYY-MM.")
    in_data_range: bool = Field(description="False when the month is outside the lookup data; then every feature is null.")
    features: MarketContextFeatures
    evidence_missing: bool = Field(description="True when there is no category market evidence for this (category, month), or the month is outside the data.")
    source_note: str
    note: str | None = Field(default=None, description="Plain-English note when values are missing.")
    available_months: list[str]


MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
MAX_PREVIOUS_VISITS = 12


class PreviousVisit(BaseModel):
    """One earlier monitoring visit of the same household (month only). No IDs or names."""

    model_config = ConfigDict(extra="forbid")

    month: str = Field(pattern=MONTH_PATTERN, description="Visit month, YYYY-MM.")
    business_running: SignalValue = Field(description="1 if the business was running, 0 if not, null if not answered.")
    profit_last_month: SignalValue = Field(description="1 if there was a profit last month, 0 if not, null if not answered.")
    progressing_well: SignalValue = Field(description="1 if the business was progressing well, 0 if not, null if not answered.")
    market_stress: SignalValue = Field(description="1 if any market stress (sales below expected, high input cost or inputs unavailable), 0 if none, null if not answered.")


class CurrentVisit(BaseModel):
    """The visit to predict from. Full dates, because F_Months_Since_Grant is computed in days as in training."""

    model_config = ConfigDict(extra="forbid")

    visit_date: dt.date = Field(description="Date of this visit, YYYY-MM-DD; its month is the visit month.")
    business_running: SignalValue = Field(description="1 if the business is running, 0 if not, null if not answered.")
    profit_last_month: SignalValue = Field(description="1 if there was a profit last month, 0 if not, null if not answered.")
    progressing_well: SignalValue = Field(description="1 if the business is progressing well, 0 if not, null if not answered.")
    market_stress: SignalValue = Field(description="1 if any market stress, 0 if none, null if not answered.")
    grant_date: dt.date | None = Field(description="Date the grant was received, YYYY-MM-DD, or null if not received / not known. Must not be after visit_date.")

    @property
    def month(self) -> str:
        return self.visit_date.strftime("%Y-%m")


class HistoryFeaturesRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "current_visit": {
                        "visit_date": "2026-04-12", "business_running": 1, "profit_last_month": 0,
                        "progressing_well": 1, "market_stress": 0, "grant_date": "2026-01-20",
                    },
                    "previous_visits": [
                        {"month": "2026-02", "business_running": 1, "profit_last_month": 1, "progressing_well": 1, "market_stress": 0},
                        {"month": "2026-03", "business_running": 1, "profit_last_month": 0, "progressing_well": 0, "market_stress": 1},
                    ],
                }
            ]
        },
    )

    current_visit: CurrentVisit
    previous_visits: list[PreviousVisit] = Field(
        default_factory=list, max_length=MAX_PREVIOUS_VISITS,
        description=f"0 to {MAX_PREVIOUS_VISITS} earlier visits of the same household, any order, each in a different month before the current visit month.",
    )

    @model_validator(mode="after")
    def _check_visits(self):
        current = self.current_visit
        if current.grant_date is not None and current.grant_date > current.visit_date:
            raise ValueError("current_visit.grant_date must not be after current_visit.visit_date")
        months = [visit.month for visit in self.previous_visits]
        duplicates = sorted({m for m in months if months.count(m) > 1})
        if duplicates:
            raise ValueError(f"previous_visits has duplicate months: {', '.join(duplicates)}")
        not_before = sorted(m for m in months if m >= current.month)
        if not_before:
            raise ValueError(
                f"previous_visits must be before the current visit month {current.month}; got {', '.join(not_before)}"
            )
        return self


class HistoryFeatures(BaseModel):
    """The 14 history features, as in training. null = not defined (e.g. no previous visit)."""

    F_Months_Since_Prev_Visit: float | None
    F_Prev_Risk_Ord: float | None
    F_Prev_No_Profit_Last_Month: float | None
    F_Prev_Market_Stress_Any: float | None
    F_Prev_Not_Progressing_Well: float | None
    F_Prev_Business_Not_Running: float | None
    F_Risk_Change_vs_Prev: float | None
    F_Tenure_Months: float | None
    F_N_Prior_Visits: float | None
    F_Risk_Mean_3M_Window: float | None
    F_NoProfit_Rate_3M_Window: float | None
    F_MarketStress_Rate_3M_Window: float | None
    F_High_Count_6M_Window: float | None
    F_Months_Since_Grant: float | None


class VisitRisk(BaseModel):
    month: str
    risk_class: CurrentRiskClass
    is_current: bool


class HistoryFeaturesResponse(BaseModel):
    month: str = Field(description="Current visit month, from visit_date.")
    features: HistoryFeatures
    visits: list[VisitRisk] = Field(description="Every visit used, oldest first, with its risk class from SUSTAIN-HH-Risk-Rule v1.0.")
    rule_version: str
