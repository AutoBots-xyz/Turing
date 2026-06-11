import asyncio
import random
from typing import List
from schemas.layer3 import StructuralQuery, SearchResult, SearchSource

async def search_web(query: StructuralQuery) -> List[SearchResult]:
    """
    Layer 3: WEB SEARCH (Industry whitepapers, Tech blogs, Case studies)
    Focuses on "What real solutions exist?"
    """
    # Simulate API call latency
    await asyncio.sleep(random.uniform(0.8, 2.0))
    
    # Mock response
    return [
        SearchResult(
            source=SearchSource.WEB,
            title="AWS Architecture Blog: Handling Traffic Surges",
            summary=f"A case study discussing {query.structural_description} and how to mitigate it using queueing mechanisms.",
            url="https://aws.amazon.com/blogs/architecture/mock",
            confidence=75.0,
            original_query=query
        )
    ]
