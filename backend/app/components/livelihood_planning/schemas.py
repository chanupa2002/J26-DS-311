"""Request and response data shapes for Livelihood Recommendation and Family Development Planning."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

OFFICIAL_LIVELIHOOD_CATEGORIES = (
    "AGRICULTURE & PLANTATION CROPS",
    "LIVESTOCK & ANIMAL HUSBANDRY",
    "FOOD PROCESSING & PRODUCTION",
    "TRADE",
    "GARMENT TEXTILE, HANDICRAFTS",
    "CONSTRUCTION, BUILDING AND REPAIR",
    "TRANSPORT & LOGISTICS",
    "BEAUTY AND WELLNESS",
    "OTHER",
)


class HealthResponse(BaseModel):
    component: str
    status: str


class LivelihoodRequest(BaseModel):
    # FINAL FIELD LIST TO BE FROZEN
    district: str | None = None
    ds_division: str | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    gender: str | None = None
    female_headed: bool | None = None
    disability: bool | None = None
    aswesuma_category: str | None = None
    track: str | None = None


class SwotRequest(LivelihoodRequest):
    livelihood: str | None = None


class AssessmentRequest(BaseModel):
    livelihood: str | None = None


class RecommendationItem(BaseModel):
    livelihood: str
    score: float
    reasons: list[str] = Field(default_factory=list)


class SwotItem(BaseModel):
    text: str
    source: str
    evidence: str | None = None
    strength: Literal["clear", "weak"] | None = None


class SwotResult(BaseModel):
    strengths: list[SwotItem]
    weaknesses: list[SwotItem]
    opportunities: list[SwotItem]
    threats: list[SwotItem]


class ViabilityResult(BaseModel):
    score: float
    low: float
    high: float
    profitability: float
    market: float
    area: float
    resilience: float
    estimated: bool


class ViabilityPreview(BaseModel):
    livelihood: str
    score: float
    low: float
    high: float
    estimated: bool


class DecisionTrailStep(BaseModel):
    id: str
    title: str
    summary: str
    flag: Literal["ok", "note", "warning"]
    details: dict[str, Any] = Field(default_factory=dict)


class DecisionTrailSection(BaseModel):
    steps: list[DecisionTrailStep] = Field(default_factory=list)


class RecommendationDecisionTrail(BaseModel):
    version: Literal[1] = 1
    recommendation: DecisionTrailSection


class DecisionTrail(RecommendationDecisionTrail):
    swot: DecisionTrailSection


class BaseRecommendationResponse(BaseModel):
    recommendations: list[RecommendationItem]
    placeholder: bool
    confidence: Literal["low", "normal"] = "normal"
    notes: list[str] = Field(default_factory=list)


class RecommendResponse(BaseRecommendationResponse):
    decision_trail: RecommendationDecisionTrail | None = None
    viability_preview: list[ViabilityPreview | None] = Field(
        default_factory=list
    )


class SwotResponse(RecommendResponse):
    swot: SwotResult
    viability: ViabilityResult | None = None
    selected_livelihood: str
    decision_trail: DecisionTrail | None = None


class PlanResponse(BaseRecommendationResponse):
    swot: SwotResult
    viability: ViabilityResult | None = None
    plan: dict[str, object]


class BeneficiarySummary(BaseModel):
    id: str | int
    full_name: str
    district: str | None = None
    age: int | None = None
    gender: str | None = None
    female_headed: bool | None = None
    disability: bool | None = None
    aswesuma_category: str | None = None
    is_demo: bool | None = None


class AssessmentResponse(BaseModel):
    id: str | int
    beneficiary_id: str | int
    input_snapshot: dict[str, object] = Field(default_factory=dict)
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    chosen_livelihood: str | None = None
    swot: SwotResult | None = None
    viability: ViabilityResult | None = None
    notes: list[str] = Field(default_factory=list)
    confidence: Literal["low", "normal"]
    status: str
    created_at: datetime | None = None
    decision_trail: DecisionTrail | None = None
    selected_livelihood: str | None = None
    viability_preview: list[ViabilityPreview | None] = Field(
        default_factory=list
    )
