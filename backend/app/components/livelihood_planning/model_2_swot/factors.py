"""Retrieve grounded SWOT facts and optional semantic relevance scores."""

import math
from typing import Any

from app.core.database import get_supabase
from app.components.livelihood_planning.model_2_swot.gemini_client import (
    create_gemini_client,
)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 768
SWOT_CATEGORY_MAP = {
    "Strength": "strengths",
    "Weakness": "weaknesses",
    "Opportunity": "opportunities",
    "Threat": "threats",
}
FACT_COLUMNS = (
    "fact_id,scope,livelihood,district,statement,value,evidence_type,"
    "is_estimated,source,n_obs,small_group,swot"
)


def _l2_normalize(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise ValueError("Gemini returned an empty embedding vector.")
    return [value / norm for value in values]


def _embed_query(query: str) -> list[float]:
    from google.genai import types

    client = create_gemini_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )
    values = [float(value) for value in response.embeddings[0].values]
    return _l2_normalize(values)


def _matches_district(row: dict[str, Any], district: str | None) -> bool:
    row_district = row.get("district")
    if row_district is None:
        return True
    if not district:
        return False
    return str(row_district).strip().casefold() == district.casefold()


def _factor_from_row(row: dict[str, Any]) -> dict[str, Any] | None:
    category = SWOT_CATEGORY_MAP.get(str(row.get("swot", "")))
    statement = str(row.get("statement") or "").strip()
    if category is None or not statement:
        return None
    return {
        "category": category,
        "text": statement,
        "source": str(row.get("source") or ""),
        "fact_id": row.get("fact_id"),
        "value": row.get("value"),
        "is_estimated": bool(row.get("is_estimated", False)),
        "n_obs": row.get("n_obs"),
        "district": row.get("district"),
        "scope": row.get("scope"),
    }


def _direct_factors(
    client: Any, livelihood: str, district: str | None
) -> list[dict[str, Any]]:
    query = (
        client.table("livelihood_facts")
        .select(FACT_COLUMNS)
        .in_("livelihood", [livelihood, "ALL"])
        .neq("swot", "none")
    )
    if district:
        query = query.or_(f"district.is.null,district.eq.{district}")
    else:
        query = query.is_("district", "null")

    rows = query.execute().data or []
    factors: list[dict[str, Any]] = []
    for row in rows:
        row_livelihood = str(row.get("livelihood") or "").strip().casefold()
        if row_livelihood not in {livelihood.casefold(), "all"}:
            continue
        if not _matches_district(row, district):
            continue
        factor = _factor_from_row(row)
        if factor is not None:
            factors.append(factor)
    return factors


def _add_semantic_context(
    client: Any,
    factors: list[dict[str, Any]],
    livelihood: str,
    district: str | None,
) -> None:
    district_text = district or "all districts"
    query = (
        f"{livelihood} {district_text} strengths weaknesses "
        "opportunities threats"
    )
    embedding = _embed_query(query)
    response = client.rpc(
        "match_livelihood_facts",
        {
            "query_embedding": embedding,
            "p_livelihood": livelihood,
            "p_district": district,
            "match_count": 10,
        },
    ).execute()

    by_fact_id = {
        str(factor["fact_id"]): factor
        for factor in factors
        if factor.get("fact_id") is not None
    }
    by_statement = {factor["text"]: factor for factor in factors}
    for row in response.data or []:
        factor = by_fact_id.get(str(row.get("fact_id")))
        if factor is None:
            factor = by_statement.get(str(row.get("statement") or "").strip())
        if factor is not None and row.get("similarity") is not None:
            factor["similarity"] = float(row["similarity"])


def get_livelihood_factors(
    livelihood: str, district: str | None = None
) -> list[dict[str, Any]]:
    """Return direct SWOT facts, enriched with semantic similarity when available."""
    cleaned_livelihood = str(livelihood).strip()
    cleaned_district = str(district).strip() if district else None

    try:
        client = get_supabase()
    except Exception:
        return []

    try:
        factors = _direct_factors(client, cleaned_livelihood, cleaned_district)
    except Exception:
        factors = []

    try:
        _add_semantic_context(
            client, factors, cleaned_livelihood, cleaned_district
        )
    except Exception:
        pass

    return factors
