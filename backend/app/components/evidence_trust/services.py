"""Logic for Explainable Evidence Trust Scoring and Recommendation Framework.

Public functions (the ones other components may call) must be listed in docs/CONTRACTS.md.
To use the database:  from app.core.database import get_supabase
To use a model:       from app.components.evidence_trust.ml.loader import load_model
"""

from typing import Any

from app.components.evidence_trust.ml.image_verification.contracts import ImageInput
from app.components.evidence_trust.ml.image_verification.pipeline import ImageVerificationPipeline
from app.components.evidence_trust.ml.image_verification.report import report_dict
from app.components.evidence_trust.ml.image_verification.monitoring_repository import InMemoryMonitoringRepository, SupabaseMonitoringRepository, MonitoringRepository

_local_monitoring_repository = InMemoryMonitoringRepository()


def get_monitoring_repository() -> MonitoringRepository:
    """Use Supabase when configured, otherwise use an offline repository."""
    try:
        return SupabaseMonitoringRepository()
    except RuntimeError:
        return _local_monitoring_repository


def get_status() -> dict:
    return {"component": "evidence_trust", "status": "ok"}


def score_evidence(*args, **kwargs):
    """PLACEHOLDER public function. The component owner will implement and document it."""
    raise NotImplementedError(
        "Not implemented yet. Owner: implement and document in docs/CONTRACTS.md"
    )


async def verify_image_upload(image_bytes: bytes, household_id: str, month: str, registered_category: str | None = None, previous_image_reference: str | None = None) -> dict[str, Any]:
    """Run the image-verification pipeline for one uploaded image."""
    repository = get_monitoring_repository()
    previous = repository.latest_previous(household_id, month)
    previous_bytes = repository.read_image(previous) if previous else None
    image = ImageInput(image_bytes, household_id, month, registered_category, previous_bytes or previous_image_reference or None)
    report = await ImageVerificationPipeline(monitoring_repository=repository).process(image)
    return report_dict(report)


async def verify_category_match(image_bytes: bytes, registered_category: str) -> dict[str, Any]:
    """Run only the livelihood category-match block for diagnostic testing."""
    image = ImageInput(image_bytes, "category-test", "category-test", registered_category)
    pipeline = ImageVerificationPipeline()
    pipeline.config["pipeline"] = {"blocks": [{"name": "category_match", "enabled": True}]}
    report = await pipeline.process(image)
    block = next((item for item in report.blocks if item.block_name == "category_match"), None)
    check = block.checks[0] if block and block.checks else None
    return {
        "registered_category": registered_category,
        "check": {
            "code": check.check_code,
            "value": check.value,
            "reason": check.reason,
            "raw_measure": check.raw_measure,
            "threshold": check.threshold,
            "evidence": check.evidence,
        } if check else None,
    }


async def verify_progress_only(
    previous_image_bytes: bytes,
    current_image_bytes: bytes,
    household_id: str,
    previous_month: str,
    current_month: str,
    registered_category: str,
) -> dict[str, Any]:
    """Compare two monthly images using only the progress block."""
    pipeline = ImageVerificationPipeline()
    pipeline.config["pipeline"] = {"blocks": [{"name": "similarity_change", "enabled": True}]}
    current = ImageInput(
        current_image_bytes,
        household_id,
        current_month,
        registered_category,
        previous_image=previous_image_bytes,
    )
    report = await pipeline.process(current)
    block = next((item for item in report.blocks if item.block_name == "similarity_change"), None)
    return {
        "household_id": household_id,
        "previous_month": previous_month,
        "current_month": current_month,
        "registered_category": registered_category,
        "checks": [
            {
                "code": check.check_code,
                "value": check.value,
                "reason": check.reason,
                "raw_measure": check.raw_measure,
                "threshold": check.threshold,
                "evidence": check.evidence,
                "severity": check.severity,
            }
            for check in (block.checks if block else [])
        ],
    }
