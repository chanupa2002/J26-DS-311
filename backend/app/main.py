"""Main FastAPI application for SWSS."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.components.beneficiary_selection.router import router as beneficiary_router
from app.components.evidence_trust.router import router as trust_router
from app.components.livelihood_planning.router import router as livelihood_router
from app.components.market_risk.router import router as risk_router
from app.core.config import settings
from app.core.database import get_supabase

app = FastAPI(title="SWSS Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}


@app.get("/health/db", tags=["System"])
def database_health():
    try:
        client = get_supabase()
    except RuntimeError:
        return JSONResponse(
            status_code=503,
            content={"database": "not_configured"},
        )

    try:
        client.storage.list_buckets()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "database": "error",
                "message": "Database connection check failed.",
            },
        )

    return {"database": "ok"}


# Each member only adds their own include_router line here.
app.include_router(beneficiary_router)
app.include_router(livelihood_router)
app.include_router(trust_router)
app.include_router(risk_router)
