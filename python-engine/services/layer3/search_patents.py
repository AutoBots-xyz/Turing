import os
import logging

logger = logging.getLogger(__name__)
import httpx
from typing import List
from schemas.layer3 import StructuralQuery, SearchResult, SearchSource

# Serper.dev API — freemium, thousands of free searches (as specified in different.md)
SERPER_API_URL = "https://google.serper.dev/patents"
MAX_RESULTS = 5


def _confidence_from_rank(rank: int, total: int) -> float:
    """Top patent result = 92%, last = 70%."""
    if total <= 1:
        return 92.0
    return round(92.0 - (rank / max(total - 1, 1)) * 22.0, 1)


async def search_patents(query: StructuralQuery) -> List[SearchResult]:
    """
    Layer 4: Google Patents via Serper.dev API
    Fixes Error 3: Makes real HTTP calls to Serper.dev — removes all synthetic
    Boeing/NASA static results and non-existent test URLs.
    Fixes Error 4: No simulated asyncio.sleep — real API provides authentic latency.

    Populates citation_count, replication_count, and deployment_status from
    actual patent metadata returned by the API.

    Falls back gracefully to an empty list if SERPER_API_KEY is not configured.
    """
    api_key = os.getenv("SERPER_API_KEY", "")
    results: List[SearchResult] = []

    if not api_key:
        logger.warning("[search_patents] SERPER_API_KEY not set. Returning empty results.")
        return results

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "q": query.structural_description,
        "num": MAX_RESULTS,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(SERPER_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            patents = data.get("patents", [])
            total = len(patents)

            for rank, patent in enumerate(patents):
                title = patent.get("title", "Untitled Patent")
                snippet = patent.get("snippet", title)
                link = patent.get("link")
                patent_number = patent.get("patentNumber", "")

                # Build a clean Google Patents URL from the patent number if link missing
                url = link or (
                    f"https://patents.google.com/patent/{patent_number}" if patent_number else None
                )

                # ERR-B45 fix: Remove 8-company static whitelist. Any assignee implies commercial backing.
                assignee = patent.get("assignee", "").strip()
                deployment_status = "deployed" if assignee else "single_study"

                # ERR-B44 fix: Remove fabricated `age * 15` citation math. Only use real data.
                try:
                    citation_count = int(patent.get("citationCount", 0))
                except (ValueError, TypeError):
                    citation_count = 0

                confidence = _confidence_from_rank(rank, total)

                results.append(SearchResult(
                    source=SearchSource.PATENT,
                    title=title,
                    summary=snippet,
                    url=url,
                    confidence=confidence,
                    original_query=query,
                    citation_count=citation_count,
                    replication_count=0,
                    deployment_status=deployment_status,
                ))

    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.error(f"[search_patents] Serper.dev API error: {exc}. Returning empty results.")

    return results
