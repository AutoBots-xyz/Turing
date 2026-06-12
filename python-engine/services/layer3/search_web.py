import os
import httpx
from typing import List
from schemas.layer3 import StructuralQuery, SearchResult, SearchSource

# Serper.dev API — freemium, as specified in different.md
SERPER_API_URL = "https://google.serper.dev/search"
MAX_RESULTS = 5

# Search query suffix to target industry whitepapers and case studies
SEARCH_SUFFIX = "site:aws.amazon.com OR site:cloud.google.com OR site:martinfowler.com OR whitepaper OR case study OR engineering blog"


def _confidence_from_rank(rank: int, total: int) -> float:
    """Top web result = 78%, last = 55%."""
    if total <= 1:
        return 78.0
    return round(78.0 - (rank / max(total - 1, 1)) * 23.0, 1)


async def search_web(query: StructuralQuery) -> List[SearchResult]:
    """
    Layer 3: Web Search via Serper.dev — Industry whitepapers, Case studies, Tech blogs.
    Fixes Error 4: No fake asyncio.sleep — real API provides authentic latency.

    Uses the structural_description as the query with a domain filter targeting
    engineering and architecture content rather than general web noise.

    Falls back gracefully to an empty list if SERPER_API_KEY is not configured.
    """
    api_key = os.getenv("SERPER_API_KEY", "")
    results: List[SearchResult] = []

    if not api_key:
        print("[search_web] SERPER_API_KEY not set. Returning empty results.")
        return results

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "q": f"{query.structural_description} {SEARCH_SUFFIX}",
        "num": MAX_RESULTS,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(SERPER_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            organic = data.get("organic", [])
            total = len(organic)

            for rank, item in enumerate(organic):
                title = item.get("title", "Untitled Article")
                snippet = item.get("snippet", title)
                url = item.get("link")

                confidence = _confidence_from_rank(rank, total)

                results.append(SearchResult(
                    source=SearchSource.WEB,
                    title=title,
                    summary=snippet,
                    url=url,
                    confidence=confidence,
                    original_query=query,
                    citation_count=0,
                    replication_count=0,
                    deployment_status="blog",
                ))

    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        print(f"[search_web] Serper.dev API error: {exc}. Returning empty results.")

    return results
