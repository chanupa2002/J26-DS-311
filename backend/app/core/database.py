"""Shared Supabase client."""

from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase():
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY are not set. "
            "Copy .env.example to .env and fill them in."
        )
    from supabase import create_client

    return create_client(settings.supabase_url, settings.supabase_key)
