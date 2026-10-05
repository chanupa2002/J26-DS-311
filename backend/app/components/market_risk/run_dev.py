"""Run ONLY this component (so a problem in another folder cannot block you).

From the backend/ folder:
    uvicorn app.components.market_risk.run_dev:app --reload --port 8004
Then open http://localhost:8004/docs
"""
from fastapi import FastAPI

from app.components.market_risk.router import router

app = FastAPI(title="Explainable Market-Risk Prediction, Recommendation and Decision Dashboard (dev)")
app.include_router(router)
