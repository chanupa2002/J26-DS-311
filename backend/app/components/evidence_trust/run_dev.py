"""Run ONLY this component (so a problem in another folder cannot block you).

From the backend/ folder:
    uvicorn app.components.evidence_trust.run_dev:app --reload --port 8003
Then open http://localhost:8003/docs
"""
from fastapi import FastAPI

from app.components.evidence_trust.router import router

app = FastAPI(title="Explainable Evidence Trust Scoring and Recommendation Framework (dev)")
app.include_router(router)
