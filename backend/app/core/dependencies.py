"""Shared FastAPI dependencies. This file is leader-owned."""

from app.core.database import get_supabase


def get_db():
    """Return the shared database client."""
    return get_supabase()
