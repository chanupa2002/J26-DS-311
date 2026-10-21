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
