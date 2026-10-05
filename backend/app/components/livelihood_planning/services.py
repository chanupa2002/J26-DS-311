"""Logic for Livelihood Recommendation and Family Development Planning.

Public functions (the ones other components may call) must be listed in docs/CONTRACTS.md.
To use the database:  from app.core.database import get_supabase
To use a model:       from app.components.livelihood_planning.ml.loader import load_model
"""


def get_status() -> dict:
    return {"component": "livelihood_planning", "status": "ok"}


def recommend_livelihood(*args, **kwargs):
    """PLACEHOLDER public function. The component owner will implement and document it."""
    raise NotImplementedError(
        "Not implemented yet. Owner: implement and document in docs/CONTRACTS.md"
    )
