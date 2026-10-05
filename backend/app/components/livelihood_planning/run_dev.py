"""Run ONLY this component (so a problem in another folder cannot block you).

From the backend/ folder:
    uvicorn app.components.livelihood_planning.run_dev:app --reload --port 8002
Then open http://localhost:8002/docs
"""
from fastapi import FastAPI

from app.components.livelihood_planning.router import router

app = FastAPI(title="Livelihood Recommendation and Family Development Planning (dev)")
app.include_router(router)
