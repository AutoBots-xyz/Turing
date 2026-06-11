import asyncio
import random
from typing import List
from schemas.layer3 import StructuralQuery, SearchResult, SearchSource

async def search_patents(query: StructuralQuery) -> List[SearchResult]:
    """
    Layer 4: PATENTS (Google Patents - Boeing, NASA, Engineering solutions)
    Focuses on "What did engineers actually build?"
    """
    # Simulate API call latency
    await asyncio.sleep(random.uniform(1.0, 2.5))
    
    # Mock response
    return [
        SearchResult(
            source=SearchSource.PATENT,
            title="Boeing System for Fluid Flow Control",
            summary=f"A patented engineering mechanism resolving {query.structural_description} through redundant bypass valves.",
            url="https://patents.google.com/patent/mock",
            confidence=95.0,
            original_query=query
        ),
        SearchResult(
            source=SearchSource.PATENT,
            title="Alternative Mechanism for Pressure Release",
            summary=f"A conflicting approach stating that {query.structural_description} should be handled by increasing input rather than bypassing.",
            url="https://patents.google.com/patent/mock2",
            confidence=80.0,
            original_query=query
        )
    ]
