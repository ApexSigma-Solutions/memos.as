from dagster import repository
from .assets import sample_llm_cache_asset


@repository
def memos_as_repository():
    """Repository for memos.as Dagster assets."""
    return [
        sample_llm_cache_asset,
    ]
