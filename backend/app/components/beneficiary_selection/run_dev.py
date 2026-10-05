"""Run ONLY this component (so a problem in another folder cannot block you).

From the backend/ folder:
    uvicorn app.components.beneficiary_selection.run_dev:app --reload --port 8001
Then open http://localhost:8001/docs
"""
from fastapi import FastAPI

from app.components.beneficiary_selection.router import router

app = FastAPI(title="Beneficiary Selection Support (dev)")
app.include_router(router)
