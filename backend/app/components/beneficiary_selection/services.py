"""Logic for Beneficiary Selection Support.

Public functions (the ones other components may call) must be listed in docs/CONTRACTS.md.
To use the database:  from app.core.database import get_supabase
To use a model:       from app.components.beneficiary_selection.ml.loader import load_model
"""


def get_status() -> dict:
    return {"component": "beneficiary_selection", "status": "ok"}


def assess_household(*args, **kwargs):
    """PLACEHOLDER public function. The component owner will implement and document it."""
    raise NotImplementedError(
        "Not implemented yet. Owner: implement and document in docs/CONTRACTS.md"
    )
