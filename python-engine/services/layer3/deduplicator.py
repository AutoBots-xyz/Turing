import asyncio
from typing import List
from schemas.layer3 import SearchResult, MergedResult, SearchSource

async def deduplicate_and_merge(results: List[SearchResult]) -> List[MergedResult]:
    """
    Step 11 Deduplication + Merge:
    Merges evidence describing the same mechanism from different sources to increase confidence.
    """
    if not results:
        return []
        
    merged_results = []
    
    # For this mock, we will simply group everything together into one main group
    # so the contradiction detector can analyze them.
    merged_results = []
    
    sources = [r.source for r in results]
    
    # Boost confidence based on number of unique sources
    base_confidence = max([r.confidence for r in results])
    boost = len(set(sources)) * 2.0  # 2% boost per unique source
    final_confidence = min(100.0, base_confidence + boost)
    
    merged = MergedResult(
        title="Shared Bottleneck Resolution Mechanism",
        merged_summary="Combined evidence from multiple sources indicates this mechanism resolves cascading failures.",
        underlying_mechanism=results[0].original_query.structural_description,
        sources=list(set(sources)),
        source_results=results,
        confidence=final_confidence
    )
    merged_results.append(merged)

    return merged_results
