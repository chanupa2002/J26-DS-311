"""Main FastAPI application for SWSS."""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.components.beneficiary_selection.router import router as beneficiary_router
from app.components.beneficiary_selection.model_api import (
    LABEL as COMPONENT1_RESEARCH_LABEL,
    MODEL_VERSION as COMPONENT1_MODEL_VERSION,
    SPEC_VERSION as COMPONENT1_SPEC_VERSION,
    api_router as component1_model_router,
    app as component1_model_app,
)
from app.components.evidence_trust.router import router as trust_router
from app.components.livelihood_planning.router import router as livelihood_router
from app.components.market_risk.router import router as risk_router
from app.core.config import settings
from app.core.database import get_supabase

app = FastAPI(title="SWSS Backend", version="0.1.0")
component1_api_paths = {
    "/", "/health", "/households", "/summary", "/whatif", "/sensitivity",
    "/spec", "/model-info", "/openapi.yaml", "/whatif/template.csv",
    "/geography", "/glossary", "/distribution", "/coverage",
    "/assess/derive", "/assess/score",
}


def component1_metadata():
    data = component1_model_app.state.data
    return {
        "research_label": COMPONENT1_RESEARCH_LABEL,
        "model_version": COMPONENT1_MODEL_VERSION,
        "spec_version": COMPONENT1_SPEC_VERSION,
        "data_manifest_sha256": data.manifest_hash,
        "data_mode": data.mode,
    }


@app.middleware("http")
async def component1_response_metadata(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path in component1_api_paths or path.startswith("/households/") or path.startswith("/whatif/batches/") or path.startswith("/assets/"):
        for key, value in component1_metadata().items():
            header = "X-" + "-".join(part.title() for part in key.split("_"))
            response.headers[header] = str(value)
    return response


@app.exception_handler(StarletteHTTPException)
async def component1_http_error(request: Request, exc: StarletteHTTPException):
    if request.url.path in component1_api_paths or request.url.path.startswith("/households/") or request.url.path.startswith("/whatif/batches/"):
        return JSONResponse(status_code=exc.status_code, content={**component1_metadata(), "error": exc.detail})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def component1_validation_error(request: Request, exc: RequestValidationError):
    if request.url.path in component1_api_paths or request.url.path.startswith("/households/") or request.url.path.startswith("/whatif/batches/"):
        return JSONResponse(status_code=422, content=jsonable_encoder({**component1_metadata(), "error": "Invalid request", "details": exc.errors()}))
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": exc.errors()}))

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health():
    data = component1_model_app.state.data
    return {
        "status": "ok",
        "research_label": COMPONENT1_RESEARCH_LABEL,
        "model_version": COMPONENT1_MODEL_VERSION,
        "spec_version": COMPONENT1_SPEC_VERSION,
        "data_manifest_sha256": data.manifest_hash,
        "data_mode": data.mode,
    }


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
app.include_router(component1_model_router)
app.include_router(livelihood_router)
app.include_router(trust_router)
app.include_router(risk_router)
