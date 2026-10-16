"""Load approved cleaned records into Supabase through a manual script."""


def load_cleaned_records(records: list[dict], table_name: str) -> int:
    """Describe the future manual loading contract without connecting."""
    _ = (records, table_name)
    raise NotImplementedError(
        "Supabase loading is not implemented. Use an approved manual script later."
    )
