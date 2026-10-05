"""Request and response data shapes for Explainable Evidence Trust Scoring and Recommendation Framework."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    component: str
    status: str
