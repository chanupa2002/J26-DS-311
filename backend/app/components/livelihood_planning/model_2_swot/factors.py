"""Retrieve livelihood facts from Supabase when the fact bank is implemented."""


def get_livelihood_factors(livelihood: str) -> list[dict]:
    """Return a small placeholder fact bank for one livelihood."""
    source = "placeholder: future Supabase fact bank"
    return [
        {
            "category": "strengths",
            "text": f"Placeholder strength for {livelihood}.",
            "source": source,
        },
        {
            "category": "weaknesses",
            "text": f"Placeholder weakness for {livelihood}.",
            "source": source,
        },
        {
            "category": "opportunities",
            "text": f"Placeholder opportunity for {livelihood}.",
            "source": source,
        },
        {
            "category": "threats",
            "text": f"Placeholder threat for {livelihood}.",
            "source": source,
        },
    ]
