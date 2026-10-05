"""Request and response data shapes for Explainable Market-Risk Prediction, Recommendation and Decision Dashboard."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    component: str
    status: str
