import asyncio
import random
from typing import List
from schemas.layer3 import StructuralQuery, SearchResult, SearchSource

async def search_papers(query: StructuralQuery) -> List[SearchResult]:
    """
    Layer 1: SPECTER2 (Academic papers via Semantic Scholar, arXiv, PubMed)
    Focuses on "What did researchers prove?"
    """
    # Simulate API call latency
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    # Mock response
    return [
        SearchResult(
            source=SearchSource.PAPER,
            title="Structural Analysis of Resource Constraints in Bottlenecked Networks",
            summary=f"Researchers found that {query.structural_description} often leads to cascading failures in isolated networks.",
            url="https://arxiv.org/abs/mock-paper",
            confidence=85.0,
            original_query=query
        )
    ]
