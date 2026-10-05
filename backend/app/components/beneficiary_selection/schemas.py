"""Request and response data shapes for Beneficiary Selection Support."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    component: str
    status: str
