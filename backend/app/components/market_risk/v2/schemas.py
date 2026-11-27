"""Request and response shapes for the market_risk v2 endpoints. Examples are synthetic."""

from datetime import date
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
    """3M or 6M: machine-learning prediction."""

    model_config = ConfigDict(extra="forbid")

    p_high: float
    predicted_class: RiskClass
    alert: bool | None = Field(description="P(High) >= alert_threshold; null when no threshold is set.")
    alert_threshold: float | None
    reliability_note: str | None = None


class NextMonthOutlook(BaseModel):
    """1M: summary of past monthly transitions between risk classes, not machine learning.
    The chances are null when the current risk class is Unassigned."""

    model_config = ConfigDict(extra="forbid")

    p_low: float | None
    p_medium: float | None
    p_high: float | None
    predicted_class: RiskClass | None = Field(description="Most likely class next month.")
    method: Literal["past monthly transitions"]
    n_transitions: int = Field(description="Number of one-month steps the summary is based on.")
    alert: None = Field(default=None, description="Always null: no alert is issued for 1 month.")
    note: str


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
    grant_status: int | None = Field(description="0-3 as sent or stored; null when not answered.")
    grant_status_label: str | None = Field(description="Codebook label of grant_status.")
    current_risk: CurrentRisk
    predictions: dict[str, NextMonthOutlook | HorizonOutlook] = Field(
        description='"1M" = past monthly transitions; "3M" and "6M" = machine-learning models.'
    )
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
    grant_status: int | None
    grant_status_label: str | None
    current_risk: CurrentRiskClass
    reasons: list[str]
    next_month_class: RiskClass | None = Field(description="Most likely class next month (past monthly transitions).")
    next_month_p_high: float | None = Field(description="Past monthly transitions; null if Unassigned.")
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
    next_month_class: RiskClass | None = Field(description="Most likely class next month (past monthly transitions).")
    next_month_p_high: float | None = Field(description="Past monthly transitions; null if Unassigned.")
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


class ChanceOfHighAfter(BaseModel):
    months: int
    Low: float
    Medium: float
    High: float


class TransitionSummary(BaseModel):
    is_synthetic: bool
    method: str
    classes: list[RiskClass]
    smoothing: int
    n_transitions: int
    counts: list[list[int]] = Field(description="Rows = this month, columns = next month.")
    matrix: list[list[float]] = Field(description="Smoothed chances; each row sums to 1.")
    p_high_after: list[ChanceOfHighAfter] = Field(description="Chance of High after 1-6 months by starting class.")
    text: str


class RetrievalCheck(BaseModel):
    queries: int
    hit_at_1: int
    hit_at_3: int


class CitedPage(BaseModel):
    doc_id: str | None = Field(description="null when only a page number was found in the citation text.")
    page: int


class SourcePageRule(BaseModel):
    rule_id: str
    basis: Literal["cited_pages", "citation text (page only)"]
    cited_pages: list[CitedPage]
    top_source: str
    top_doc_id: str
    top_page: int | None
    matched: bool


class SourcePageCheck(BaseModel):
    matched: int
    total: int = Field(description="Rules whose citation names pages and that have a source.")
    rules: list[SourcePageRule]


class TranslationSummary(BaseModel):
    translated: int = Field(description="Sinhala chunks with an English machine translation.")
    sinhala_chunks: int
    model: str | None = Field(description="Model that wrote most translations; null when there are none.")


class RecommendationEvidence(BaseModel):
    n_rules: int
    n_rules_validated: int
    n_documents: int
    n_chunks: int
    knowledge_version: str
    retrieval_check: RetrievalCheck = Field(description="Fixed test set of queries -> expected documents; computed at load.")
    source_page_check: SourcePageCheck = Field(
        description="Top source of each rule on a page named in its citation? Computed at load."
    )
    translations: TranslationSummary = Field(
        description="Counted from the optional guidance_chunks_en.jsonl; not part of knowledge_version.")


class EvidenceResponse(V2Envelope):
    models: dict[str, Any]
    alert_thresholds: dict[str, float | None]
    comparisons: list[PersistenceComparison]
    results: dict[str, list[dict[str, Any]]]
    shap_group_share: list[dict[str, Any]]
    threshold_register: list[dict[str, Any]]
    transitions: TransitionSummary
    recommendations: RecommendationEvidence | None = Field(
        description="Rule table and circular retrieval; null when the knowledge base is not installed."
    )
    limitations: list[str]


DecisionValue = Literal["accept", "modify", "reject"]


class DecisionRequest(BaseModel):
    """FR7: the officer's decision on one recommended rule. No personal data."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={
        "examples": [{"decision": "accept", "note": "Visit planned with the coach.", "planned_visit_date": "2026-12-03"}]
    })

    decision: DecisionValue
    note: str | None = Field(default=None, max_length=500)
    planned_visit_date: date | None = None


class Decision(BaseModel):
    decision: DecisionValue
    note: str | None
    planned_visit_date: str | None
    knowledge_version: str
    created_at: str


class Source(BaseModel):
    chunk_id: str
    doc_id: str
    issuer: str | None
    circular_no: str | None
    title_en: str | None
    date: str | None
    page: int | None
    source_url: str | None
    status_note: str | None
    excerpt: str = Field(description=(
        "Passage of the OCR text, at most ~600 characters: whole words only, starting at a sentence or "
        "numbered-point start, ending at a sentence end; ends with '…' when text was left out."))
    excerpt_en: str | None = Field(default=None, description=(
        "Machine translation (English) of a Sinhala chunk, trimmed the same way; null when there is none."))


class SummaryStep(BaseModel):
    text: str
    chunk_ids: list[str]


class RelatedFactor(BaseModel):
    label: str = Field(description="SHAP factor label, as in shap_top_factors.")
    value: str = Field(description="The household's value label for it, as in shap_top_factors (may be empty).")


class Recommendation(BaseModel):
    rule_id: str
    level: Literal["A", "B"]
    action_category: str
    reason_label: str
    action_en: str
    timing_days: int | None
    circular_says: str = Field(description=(
        "What the cited circular says, in plain English (rule table, validated by the supervisor). "
        "May be empty."))
    guardrail: str
    research_basis: str = Field(description="Background for the rule; not a source.")
    draft: bool = Field(description="True until the supervisor validates the rule table.")
    related_factors: list[RelatedFactor] = Field(
        description="SHAP factors that raise risk and are linked to this rule, with the household's value.")
    sources: list[Source] = Field(description="Top 2 chunks from the rule's documents only.")
    summary_steps: list[SummaryStep] | None = Field(description="Optional LLM summary; null without a key or on any error.")
    decision: Decision | None = Field(description="Latest officer decision for this rule.")


class RecommendationsResponse(V2Envelope):
    household_key: str
    monitoring_period: str
    knowledge_version: str
    generated_by: Literal["rules+retrieval", "rules+retrieval+llm"]
    follow_up: Recommendation | None
    actions: list[Recommendation]
    disclaimer: str


class DecisionResponse(V2Envelope):
    household_key: str
    rule_id: str
    decision: Decision
