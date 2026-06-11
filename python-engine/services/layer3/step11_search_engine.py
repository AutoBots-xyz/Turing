import asyncio
from typing import List

from schemas.layer3 import StructuralQuery, MergedResult, Step11Response
from services.layer3.search_papers import search_papers
from services.layer3.search_wikipedia import search_wikipedia
from services.layer3.search_web import search_web
from services.layer3.search_patents import search_patents
from services.layer3.deduplicator import deduplicate_and_merge
from services.layer3.contradiction_detector import detect_contradictions

async def run_step_11_search(query: StructuralQuery) -> Step11Response:
    """
    Step 11 — 4 LAYER SEARCH ENGINE
    Runs 4 concurrent searches across different domains for the same structural query.
    Then merges and deduplicates them.
    """
    
    # Run all 4 searches simultaneously
    results_nested = await asyncio.gather(
        search_papers(query),
        search_wikipedia(query),
        search_web(query),
        search_patents(query),
        return_exceptions=True
    )
    
    # Flatten the results, handling potential exceptions from individual searches
    all_results = []
    for res in results_nested:
        if isinstance(res, Exception):
            # In a real app, log the error and continue with other sources
            print(f"Error in search layer: {res}")
        else:
            all_results.extend(res)
            
    # Step 11 Deduplication
    merged_results = await deduplicate_and_merge(all_results)
    
    # Step 11.5 Contradiction Detection via Agent Swarm
    final_results = await detect_contradictions(merged_results)
    
    return Step11Response(
        query=query,
        results=final_results
    )
