"""Request and response data shapes for Explainable Evidence Trust Scoring and Recommendation Framework."""
from pydantic import BaseModel
from typing import Any


class HealthResponse(BaseModel):
    component: str
    status: str


class ImageVerificationResponse(BaseModel):
    """JSON report returned by the image-verification endpoint."""

    input_summary: dict[str, Any]
    blocks: list[dict[str, Any]]
    flagged_checks: list[dict[str, Any]]
    unknown_checks: list[dict[str, Any]]
    summary: str
    config_hash: str
    raised_flag_order: list[str]
    timestamp: str
