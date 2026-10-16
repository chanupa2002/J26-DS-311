"""Request and response data shapes for Livelihood Recommendation and Family Development Planning."""
from pydantic import BaseModel

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
    age: int | None = None
    gender: str | None = None
    female_headed: bool | None = None
    disability: bool | None = None
    aswesuma_category: str | None = None
    track: str | None = None


class RecommendationItem(BaseModel):
    livelihood: str
    score: float


class SwotItem(BaseModel):
    text: str
    source: str


class SwotResult(BaseModel):
    strengths: list[SwotItem]
    weaknesses: list[SwotItem]
    opportunities: list[SwotItem]
    threats: list[SwotItem]


class RecommendResponse(BaseModel):
    recommendations: list[RecommendationItem]
    placeholder: bool


class SwotResponse(RecommendResponse):
    swot: SwotResult


class PlanResponse(SwotResponse):
    plan: dict[str, object]
