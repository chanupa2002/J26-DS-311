"""Request and response shapes for the market_risk v2 endpoints. Examples are synthetic."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
HOUSEHOLD_KEY_PATTERN = r"^SIM-HH-[A-Za-z0-9-]+$"
MAX_PREVIOUS_VISITS = 24

Binary = Literal[0, 1] | None
Flag = Literal[0, 1]
RiskClass = Literal["Low", "Medium", "High"]
CurrentRiskClass = Literal["Low", "Medium", "High", "Unassigned"]

EXAMPLE_VISIT = {
    "monitoring_period": "2026-06",
    "district": "Ampara",
    "category": "AGRICULTURE & PLANTATION CROPS",
    "is_synthetic": True,
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
    "problem_input_unavailable": 0,
}


class PreviousVisit(BaseModel):
    """An earlier visit of the same household: only the answers history needs."""

    model_config = ConfigDict(extra="forbid")

    monitoring_period: str = Field(pattern=MONTH_PATTERN)
    business_running: Binary = None
    profit: Binary = None
    coach_progressing: Binary = None
    revenue_band: Literal[0, 1, 2, 3] | None = None
    problem_sales_low: Binary = None
    problem_input_cost: Binary = None
    problem_input_unavailable: Binary = None


class VisitRequest(BaseModel):
    """One monitoring visit. Blank answers are null. Nothing is stored."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [EXAMPLE_VISIT]})

    monitoring_period: str = Field(pattern=MONTH_PATTERN, description="Visit month, YYYY-MM.")
    district: str = Field(min_length=1, description="One of the 25 districts in the market table.")
    category: str = Field(min_length=1, description="Livelihood category, upper case, or UNASSIGNED.")
    is_synthetic: bool = Field(description="True for simulated households, false for real visits.")
    household_key: str | None = Field(
        default=None, pattern=HOUSEHOLD_KEY_PATTERN,
        description="Required for synthetic visits. Not allowed for real visits.",
    )
    previous_visits: list[PreviousVisit] | None = Field(
        default=None, max_length=MAX_PREVIOUS_VISITS,
        description="Earlier visits. If omitted, a synthetic household's stored visits are used. "
                    "Not allowed for real visits.",
    )

    business_running: Binary = None
    profit: Binary = None
    coach_progressing: Binary = None
    revenue_band: Literal[0, 1, 2, 3] | None = None
    hours_band: Literal[1, 2, 3] | None = None
    record_keeping: Literal[0, 1, 2, 3] | None = None
    borrowed_money: Binary = None
    saved_money: Binary = None
    grant_status: Literal[0, 1, 2, 3] | None = None

    problem_sales_low: Binary = None
    problem_asset_lost: Binary = None
    problem_input_cost: Binary = None
    problem_input_unavailable: Binary = None
    problem_storage_transport: Binary = None
    problem_equipment: Binary = None
    problem_disaster: Binary = None

    revenue_band_dk: Flag = 0
    profit_dk: Flag = 0
    coach_progressing_dk: Flag = 0
    record_keeping_dk: Flag = 0
    children_in_school_not_applicable: Flag = 0
    ill_member_got_care_not_applicable: Flag = 0
    referral_reached_not_applicable: Flag = 0

    @model_validator(mode="after")
    def _check_identity_and_history(self):
        if self.is_synthetic and self.household_key is None:
            raise ValueError("household_key is required when is_synthetic is true")
        if not self.is_synthetic and (self.household_key is not None or self.previous_visits is not None):
            raise ValueError("real visits are scored without household_key or previous_visits")
        months = [visit.monitoring_period for visit in self.previous_visits or []]
        if len(months) != len(set(months)):
            raise ValueError("previous_visits has duplicate months")
        if any(month >= self.monitoring_period for month in months):
            raise ValueError("previous_visits must be before monitoring_period")
        return self


class V2Envelope(BaseModel):
    is_synthetic: bool
    model_version: Literal["v2"] = "v2"
    note: str | None = None

    model_config = ConfigDict(protected_namespaces=())


class CurrentRisk(BaseModel):
    risk_class: CurrentRiskClass
    risk_ord: int | None
    signal_count: int
    reasons: list[str]
    rule_version: str


class HorizonOutlook(BaseModel):
    p_high: float
    predicted_class: RiskClass
    alert: bool | None = Field(description="P(High) >= alert_threshold; null when no threshold is set.")
    alert_threshold: float | None
    reliability_note: str | None = None


class ShapFactor(BaseModel):
    feature: str
    label: str
    value: str
    raw_value: float | None
    group: str
    contribution: float = Field(description="Signed effect on P(High) at 3 months.")


class MarketInfo(BaseModel):
    pressure: float | None
    level: str | None
    price_month_used: str | None
    series: str | None
    basis: str | None


class VisitResponse(V2Envelope):
    household_key: str | None
    monitoring_period: str
    district: str
    category: str
    current_risk: CurrentRisk
    predictions: dict[str, HorizonOutlook]
    shap_base_value: float
    shap_top_factors: list[ShapFactor]
    market: MarketInfo
    warnings: list[str] = Field(default_factory=list)


class HouseholdSummary(BaseModel):
    household_key: str
    monitoring_period: str
    district: str
    category: str
    is_synthetic: bool
    current_risk: CurrentRiskClass
    predicted_3m: RiskClass
    p_high_3m: float
    alert_3m: bool | None
    market_level: str | None


class HouseholdListResponse(V2Envelope):
    month: str
    count: int
    households: list[HouseholdSummary]


class TimelinePoint(BaseModel):
    monitoring_period: str
    current_risk: CurrentRiskClass
    reasons: list[str]
    predicted_3m: RiskClass
    p_high_3m: float
    alert_3m: bool | None
    market_level: str | None


class HouseholdDetailResponse(V2Envelope):
    household_key: str
    latest_visit: VisitResponse
    timeline: list[TimelinePoint]


class MarketRow(BaseModel):
    district: str
    category: str
    market_pressure: float | None
    market_pressure_level: str | None
    price_month_used: str | None
    series: str | None
    ipa_basis: str | None
    dmc_affected_families: float | None


class MarketTableResponse(V2Envelope):
    month: str
    available_months: list[str]
    count: int
    rows: list[MarketRow]


class PersistenceComparison(BaseModel):
    name: str
    metric: str
    model: float
    persistence: float
    model_better: bool


class EvidenceResponse(V2Envelope):
    models: dict[str, Any]
    alert_thresholds: dict[str, float | None]
    comparisons: list[PersistenceComparison]
    results: dict[str, list[dict[str, Any]]]
    shap_group_share: list[dict[str, Any]]
    threshold_register: list[dict[str, Any]]
    limitations: list[str]
