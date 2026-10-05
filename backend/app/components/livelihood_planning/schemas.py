"""Request and response data shapes for Livelihood Recommendation and Family Development Planning."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    component: str
    status: str
