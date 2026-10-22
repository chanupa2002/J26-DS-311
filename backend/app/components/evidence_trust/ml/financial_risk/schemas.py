"""API schemas for financial risk."""

from typing import Any
from pydantic import BaseModel, Field


class ScoreRequest(BaseModel):
    visit_id: str


class BatchScoreRequest(BaseModel):
    visit_ids: list[str] = Field(min_length=1, max_length=1000)


class FinancialReportResponse(BaseModel):
    report: dict[str, Any]
