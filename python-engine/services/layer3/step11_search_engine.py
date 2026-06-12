import asyncio
from typing import List

from schemas.layer3 import StructuralQuery, MergedResult, Step11Response
from services.layer3.search_papers import search_papers
from services.layer3.search_wikipedia import search_wikipedia
from services.layer3.search_web import search_web
from services.layer3.search_patents import search_patents
from services.layer3.deduplicator import deduplicate_and_merge
from services.layer3.contradiction_detector import detect_contradictions

# Per-source timeout in seconds.
# Individual HTTP clients already have their own timeouts (10-15s), but wrapping
# the whole coroutine ensures we never wait more than this even if the inner
# timeout silently hangs (e.g., SSL negotiation stall).
_SOURCE_TIMEOUT_SECONDS = 12.0


async def _timed_search(coro, source_name: str) -> List:
    """
    Fixes L3-9: Wraps each individual search coroutine in asyncio.wait_for()
    with a hard deadline. Without this, if all 4 APIs are slow, their internal
    HTTP client timeouts (10 + 10 + 10 + 15 = 45s) accumulate in series even
    though the gather runs them in parallel — because one hung connection can
    hold up the event loop.

    On timeout, logs a warning and returns an empty list so the other 3 sources
    still contribute to the pipeline.
    """
    try:
        return await asyncio.wait_for(coro, timeout=_SOURCE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        print(
            f"[step11_search_engine] {source_name} timed out after "
            f"{_SOURCE_TIMEOUT_SECONDS}s. Returning empty results."
        )
        return []
    except Exception as exc:
        print(f"[step11_search_engine] {source_name} error: {exc}. Returning empty results.")
        return []


async def run_step_11_search(query: StructuralQuery) -> Step11Response:
    """
    Step 11 — 4 LAYER SEARCH ENGINE

    Runs 4 concurrent searches across different domains for the same structural
    query, then merges, deduplicates, and passes results through contradiction
    detection.

    Fixes L3-9: Each search is now wrapped in `_timed_search()` with a per-source
    12-second hard deadline. Previously the pipeline had no overall timeout, so
    if all 4 APIs were slow, internal HTTP timeouts (10-15s each) would stack
    and stall the pipeline for 60+ seconds.

    return_exceptions=True on the outer gather is kept for defence-in-depth,
    but the individual _timed_search wrappers now handle all expected failures
    (timeout, HTTP error, exception) and return [] gracefully.
    """
    results_nested = await asyncio.gather(
        _timed_search(search_papers(query),    "search_papers"),
        _timed_search(search_wikipedia(query), "search_wikipedia"),
        _timed_search(search_web(query),       "search_web"),
        _timed_search(search_patents(query),   "search_patents"),
        return_exceptions=True,
    )

    # Flatten results, handling any residual exceptions from the gather level
    all_results = []
    for res in results_nested:
        if isinstance(res, Exception):
            print(f"[step11_search_engine] Unexpected gather-level error: {res}")
        elif isinstance(res, list):
            all_results.extend(res)

    # Step 11 Deduplication — stopword-filtered Jaccard with threshold 0.50
    merged_results = await deduplicate_and_merge(all_results)

    # Step 11.5 Contradiction Detection via Agent Swarm
    final_results = await detect_contradictions(merged_results)

    return Step11Response(
        query=query,
        results=final_results,
    )
