"""Request and response data shapes for Explainable Market-Risk Prediction, Recommendation and Decision Dashboard."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Horizon = Literal["3M", "6M"]
HorizonOption = Literal["3M", "6M", "both"]
RiskClass = Literal["Low", "Medium", "High"]

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
