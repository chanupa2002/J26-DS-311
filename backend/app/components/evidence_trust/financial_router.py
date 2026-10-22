"""Financial-risk API routes."""

import asyncio
import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from .ml.financial_risk.pipeline import FinancialRiskPipeline
from .ml.financial_risk.repository import InMemoryFinancialRepository, SupabaseFinancialRepository
from .ml.financial_risk.contracts import Visit
from .ml.financial_risk.bill_verifier import BillExtractor
from .ml.financial_risk.schemas import BatchScoreRequest, FinancialReportResponse, ScoreRequest
from .ml.image_verification.authenticity import SerpApiGoogleLensMatcher
from .ml.image_verification.config_loader import load_config as load_image_config
from .ml.image_verification.contracts import ImageInput
from .ml.image_verification.image_loader import load_context
from .services import verify_image_upload
from app.core.config import settings

router = APIRouter(prefix="/evidence-trust/financial", tags=["Evidence Trust Financial Risk"])
_local_repository = InMemoryFinancialRepository()
_local_submissions: list[dict] = []


def repository():
    try: return SupabaseFinancialRepository()
    except RuntimeError: return _local_repository


@router.post("/score", response_model=FinancialReportResponse)
def score(request: ScoreRequest):
    try:
        report = FinancialRiskPipeline(repository()).score_and_save(request.visit_id)
        return {"report": report.as_dict()}
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/score-batch")
async def score_batch(request: BatchScoreRequest):
    repo = repository()
    pipeline = FinancialRiskPipeline(repo)
    async def one(visit_id: str):
        return await asyncio.to_thread(pipeline.score_and_save, visit_id)
    results = await asyncio.gather(*(one(visit_id) for visit_id in request.visit_ids), return_exceptions=True)
    return {"reports": [{"report": result.as_dict()} if not isinstance(result, Exception) else {"visit_id": visit_id, "error": str(result)} for visit_id, result in zip(request.visit_ids, results)]}


@router.post("/score-with-bills", response_model=FinancialReportResponse)
async def score_with_bills(visit_id: str = Form(...), bills: list[UploadFile] = File(...)):
    """Score one visit and reconcile all uploaded bill images advisory-only."""
    if not bills: raise HTTPException(status_code=422, detail="At least one bill image is required")
    try:
        images = [await bill.read() for bill in bills]
        report = await asyncio.to_thread(FinancialRiskPipeline(repository()).score_and_save, visit_id, images)
        return {"report": report.as_dict()}
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}", response_model=FinancialReportResponse)
def get_run(run_id: str):
    repo = repository()
    result = repo.get_run(run_id) if hasattr(repo, "get_run") else None
    if result is None: raise HTTPException(status_code=404, detail="Financial run not found")
    return {"report": result if isinstance(result, dict) else result.as_dict()}


@router.post("/inspect-bill")
async def inspect_bill(bill: UploadFile = File(...)):
    """Diagnostic endpoint for bill OCR/model extraction; does not save the bill."""
    content = await bill.read()
    try:
        extractor = BillExtractor()
        extracted = await asyncio.to_thread(extractor.extract, content)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "filename": bill.filename,
        "extracted": {
            "total_lkr": extracted.total,
            "bill_date": extracted.bill_date.isoformat() if extracted.bill_date else None,
            "currency": extracted.currency,
            "extraction_error": extracted.extraction_error,
        },
        "note": "The bill model selects totals; the date is read by Tesseract OCR and the date parser.",
    }


@router.post("/debug-bill-ocr")
async def debug_bill_ocr(bill: UploadFile = File(...)):
    """Temporary diagnostic endpoint returning date-focused OCR text."""
    content = await bill.read()
    try:
        extractor = BillExtractor()
        debug = await asyncio.to_thread(extractor.debug_ocr, content)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"filename": bill.filename, **debug}


@router.post("/debug-bill-ocr-full")
async def debug_bill_ocr_full(bill: UploadFile = File(...)):
    """Return full bill OCR, date candidates, amount candidates, and currency."""
    content = await bill.read()
    try:
        extractor = BillExtractor()
        debug = await asyncio.to_thread(extractor.debug_full_ocr, content)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Bill OCR failed: {exc}") from exc
    return {"filename": bill.filename, **debug}


def _serpapi_account() -> dict:
    api_key = settings.serpapi_key or os.getenv("SERPAPI_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_KEY is not configured")
    query = urllib.parse.urlencode({"api_key": api_key})
    request = urllib.request.Request(f"https://serpapi.com/account.json?{query}")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"SerpApi account request returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"SerpApi account request failed: {exc.reason}") from exc
    return {
        key: payload.get(key)
        for key in (
            "account_status",
            "plan_name",
            "searches_per_month",
            "plan_searches_left",
            "extra_credits",
            "total_searches_left",
            "this_month_usage",
            "this_hour_searches",
            "account_rate_limit_per_hour",
        )
    }


@router.get("/serpapi/account")
async def serpapi_account():
    """Return safe SerpApi quota fields without exposing the API key."""
    try:
        account = await asyncio.to_thread(_serpapi_account)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"provider": "serpapi", "account": account}


@router.post("/serpapi/test-image")
async def test_serpapi_image(image: UploadFile = File(...)):
    """Run one real SerpApi Google Lens request without saving the image."""
    raw = await image.read()
    config, _ = load_image_config()
    matcher = SerpApiGoogleLensMatcher(
        api_key=settings.serpapi_key or os.getenv("SERPAPI_KEY"),
        timeout_seconds=float(config.get("authenticity", {}).get("serpapi_timeout_seconds", 30.0)),
    )
    if not matcher.available:
        raise HTTPException(status_code=503, detail="SERPAPI_KEY is not configured")
    context = await asyncio.to_thread(
        load_context,
        ImageInput(raw, "diagnostic", "diagnostic"),
        int(config.get("image", {}).get("fixed_longest_side", 512)),
    )
    if context.load_error:
        raise HTTPException(status_code=422, detail=context.load_error)
    try:
        result = await asyncio.to_thread(matcher.match, context, config.get("authenticity", {}))
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "ok": False,
            "available": True,
            "error_code": matcher.last_error_code or "request_failed",
            "error": str(exc),
            "detail": matcher.last_error_detail,
        }
    return {"ok": True, "available": True, "match": result}


def _optional_bool(value: str | None) -> bool | None:
    if value in (None, "", "null"):
        return None
    return value.lower() in {"true", "1", "yes", "on"}


def _optional_float(value: str | None) -> float | None:
    if value in (None, "", "null"):
        return None
    return float(value)


def _non_negative_float(value: str | None, label: str) -> float | None:
    parsed = _optional_float(value)
    if parsed is not None and parsed < 0:
        raise HTTPException(status_code=422, detail=f"{label} cannot be negative")
    return parsed


def _problem_count(value: str | None) -> int | None:
    parsed = _optional_float(value)
    if parsed is not None and (not parsed.is_integer() or not 0 <= parsed <= 7):
        raise HTTPException(status_code=422, detail="Problem count must be an integer from 0 to 7")
    return int(parsed) if parsed is not None else None


def _record_keeping_level(value: str | None) -> int | None:
    parsed = _optional_float(value)
    if parsed is not None and (not parsed.is_integer() or not 0 <= parsed <= 3):
        raise HTTPException(
            status_code=422,
            detail="Record keeping level must be 0, 1, 2, or 3",
        )
    return int(parsed) if parsed is not None else None


def _safe_filename(value: str | None) -> str:
    name = Path(value or "bill-image").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return cleaned or "bill-image"


def _save_bill_evidence(
    financial_repository,
    visit: Visit,
    uploaded_bills: list[tuple[str, str | None, bytes]],
    financial_report: dict,
) -> list[dict]:
    """Upload bills and save searchable metadata beside the financial run."""
    if not uploaded_bills:
        return []
    if not isinstance(financial_repository, SupabaseFinancialRepository):
        return [
            {
                "original_filename": filename,
                "content_type": content_type,
                "content_hash": hashlib.sha256(content).hexdigest(),
                "storage_path": None,
            }
            for filename, content_type, content in uploaded_bills
        ]

    bucket = "evidence-trust-bills"
    bill_checks = next(
        (block.get("checks", []) for block in financial_report.get("blocks", []) if block.get("name") == "bill_to_expenditure"),
        [],
    )
    saved: list[dict] = []
    for filename, content_type, content in uploaded_bills:
        content_hash = hashlib.sha256(content).hexdigest()
        safe_name = _safe_filename(filename)
        storage_path = f"{visit.household_id}/{visit.visit_date.strftime('%Y-%m')}/{visit.visit_id}/{content_hash}-{safe_name}"
        financial_repository.client.storage.from_(bucket).upload(
            storage_path,
            content,
            {"content-type": content_type or "application/octet-stream", "upsert": "true"},
        )
        row = {
            "visit_id": visit.visit_id,
            "household_id": visit.household_id,
            "monitoring_year": visit.visit_date.year,
            "monitoring_month": visit.visit_date.month,
            "monitoring_month_key": visit.visit_date.strftime("%Y%m"),
            "storage_path": storage_path,
            "original_filename": filename or safe_name,
            "content_type": content_type,
            "content_hash": content_hash,
            "extraction_result": {"status": "processed", "bill_count": len(uploaded_bills)},
            "verification_result": {"checks": bill_checks},
        }
        financial_repository.client.table("evidence_trust_bill_evidence").insert(row).execute()
        saved.append({
            "original_filename": row["original_filename"],
            "content_type": content_type,
            "content_hash": content_hash,
            "storage_path": storage_path,
        })
    return saved


@router.post("/monitoring")
async def submit_monitoring(
    household_id: str = Form(...),
    year: int = Form(...),
    month_number: int = Form(...),
    livelihood_category: str = Form(...),
    grant_amount_lkr: str | None = Form(default=None),
    monthly_expenditure_lkr: str = Form(...),
    grant_use_status: str | None = Form(default=None),
    grant_used_per_plan: str | None = Form(default=None),
    disaster_impact_reported: str | None = Form(default=None),
    livelihood_difficulty_reported: str | None = Form(default=None),
    business_running: str | None = Form(default=None),
    profit: str | None = Form(default=None),
    borrowed_money: str | None = Form(default=None),
    revenue_mid_lkr: str | None = Form(default=None),
    problem_count: str | None = Form(default=None),
    record_keeping_level: str | None = Form(default=None),
    saved_amount_lkr: str | None = Form(default=None),
    image: UploadFile = File(...),
    bills: list[UploadFile] | None = File(default=None),
):
    """Create one monitoring visit, verify its image, and score its finances."""
    if not household_id.strip():
        raise HTTPException(status_code=422, detail="Household number is required")
    if not 1 <= month_number <= 12:
        raise HTTPException(status_code=422, detail="Month must be between 1 and 12")
    if not 2000 <= year <= 2100:
        raise HTTPException(status_code=422, detail="Enter a valid monitoring year")

    monthly_expenditure = _non_negative_float(monthly_expenditure_lkr, "Monthly expenditure")
    if monthly_expenditure is None:
        raise HTTPException(status_code=422, detail="Monthly expenditure is required")

    visit_id = str(uuid4())
    monitoring_month = f"{year:04d}-{month_number:02d}"
    financial_repository = repository()
    history_probe = Visit(
        visit_id=visit_id,
        source_uuid=visit_id,
        household_id=household_id.strip(),
        month_index=year * 12 + month_number,
        visit_date=date(year, month_number, 1),
    )
    previous_visits = financial_repository.get_history(history_probe)
    previous = previous_visits[-1] if previous_visits else None
    submitted_grant_amount = _non_negative_float(grant_amount_lkr, "Grant amount")
    grant_amount = submitted_grant_amount
    if grant_amount is None and previous is not None:
        grant_amount = previous.grant_amount_lkr
        if grant_amount is None and previous.grant_spent_lkr is not None and previous.grant_remaining_lkr is not None:
            grant_amount = previous.grant_spent_lkr + previous.grant_remaining_lkr
    if grant_amount is None:
        raise HTTPException(status_code=422, detail="Grant amount is required for the first household record")
    previous_cumulative = previous.grant_spent_lkr if previous and previous.grant_spent_lkr is not None else 0.0
    cumulative_grant_spent = previous_cumulative + monthly_expenditure
    calculated_grant_remaining = max(0.0, grant_amount - cumulative_grant_spent)
    visit = Visit(
        visit_id=visit_id,
        source_uuid=visit_id,
        household_id=household_id.strip(),
        month_index=year * 12 + month_number,
        visit_date=date(year, month_number, 1),
        grant_amount_lkr=grant_amount,
        grant_spent_lkr=cumulative_grant_spent,
        monthly_expenditure_lkr=monthly_expenditure,
        grant_remaining_lkr=calculated_grant_remaining,
        grant_use_status=grant_use_status or None,
        grant_used_per_plan=_optional_bool(grant_used_per_plan),
        disaster_impact_reported=_optional_bool(disaster_impact_reported),
        livelihood_difficulty_reported=_optional_bool(livelihood_difficulty_reported),
        business_running=_optional_bool(business_running),
        profit=_optional_bool(profit),
        borrowed_money=_optional_bool(borrowed_money),
        revenue_mid_lkr=_non_negative_float(revenue_mid_lkr, "Revenue"),
        problem_count=_problem_count(problem_count),
        record_keeping_level=_record_keeping_level(record_keeping_level),
        saved_amount_lkr=_non_negative_float(saved_amount_lkr, "Saved amount"),
    )

    financial_repository.upsert_visit(visit)
    image_report = await verify_image_upload(
        await image.read(), household_id.strip(), monitoring_month, livelihood_category
    )
    uploaded_bills = [
        (bill.filename or "bill-image", bill.content_type, await bill.read())
        for bill in (bills or [])
    ]
    bill_images = [content for _, _, content in uploaded_bills]
    financial_report = await asyncio.to_thread(
        FinancialRiskPipeline(financial_repository).score_and_save,
        visit_id,
        bill_images,
    )
    financial_report_payload = financial_report.as_dict()
    financial_report_payload["bill_evidence"] = _save_bill_evidence(
        financial_repository,
        visit,
        uploaded_bills,
        financial_report_payload,
    )
    financial_report_payload["monthly_expenditure_lkr"] = monthly_expenditure
    financial_report_payload["cumulative_grant_spent_lkr"] = cumulative_grant_spent
    financial_report_payload["grant_amount_lkr"] = grant_amount
    financial_report_payload["grant_remaining_lkr"] = calculated_grant_remaining
    financial_report_payload["has_previous_record"] = previous is not None
    financial_report_payload["image_report"] = image_report
    financial_report_payload["household_id"] = household_id.strip()
    financial_report_payload["month"] = monitoring_month
    financial_report_payload["livelihood_category"] = livelihood_category
    if isinstance(financial_repository, SupabaseFinancialRepository):
        financial_repository.client.table("evidence_trust_financial_runs").update(
            {"report_json": financial_report_payload}
        ).eq("run_id", financial_report.run_id).execute()
    submission = {
        "visit_id": visit_id,
        "household_id": household_id.strip(),
        "month": monitoring_month,
        "livelihood_category": livelihood_category,
        "image_report": image_report,
        "financial_report": financial_report_payload,
    }
    _local_submissions.insert(0, submission)
    del _local_submissions[100:]
    return submission


@router.get("/monitoring")
def list_monitoring():
    """Return recent monitoring submissions for the officer dashboard."""
    if _local_submissions:
        return {"records": _local_submissions}
    repo = repository()
    if isinstance(repo, SupabaseFinancialRepository):
        response = repo.client.table("evidence_trust_financial_runs").select("report_json").order("created_at", desc=True).limit(100).execute()
        records = []
        for row in response.data or []:
            report = row.get("report_json") or {}
            visit = repo.get_visit(report.get("visit_id", ""))
            records.append({
                "visit_id": report.get("visit_id"),
                "household_id": visit.household_id if visit else None,
                "month": visit.visit_date.isoformat()[:7] if visit and visit.visit_date else None,
                "livelihood_category": report.get("livelihood_category"),
                "image_report": report.get("image_report"),
                "financial_report": report,
            })
        return {"records": records}
    return {"records": []}
