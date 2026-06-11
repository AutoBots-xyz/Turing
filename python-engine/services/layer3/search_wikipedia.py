import asyncio
import random
from typing import List
from schemas.layer3 import StructuralQuery, SearchResult, SearchSource

async def search_wikipedia(query: StructuralQuery) -> List[SearchResult]:
    """
    Layer 2: WIKIPEDIA API
    Focuses on "What phenomena exist in nature?"
    """
    # Simulate API call latency
    await asyncio.sleep(random.uniform(0.3, 1.0))
    
    # Mock response
    return [
        SearchResult(
            source=SearchSource.WIKIPEDIA,
            title="Braess's Paradox",
            summary=f"An observation in mathematics where {query.structural_description} behaves counterintuitively when capacity is added.",
            url="https://en.wikipedia.org/wiki/Braess%27s_paradox",
            confidence=70.0,
            original_query=query
        )
    ]
