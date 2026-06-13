import os
import httpx
import asyncio
from typing import List
from schemas.layer3 import StructuralQuery, SearchResult, SearchSource
from services.anthropic_client import classify_deployment_status

# Serper.dev API — freemium, as specified in different.md
SERPER_API_URL = "https://google.serper.dev/search"
MAX_RESULTS = 5

# Search query suffix to target engineering whitepapers and case studies
SEARCH_SUFFIX = (
    "site:aws.amazon.com OR site:cloud.google.com OR site:azure.microsoft.com "
    "OR site:martinfowler.com OR site:infoq.com OR site:acm.org OR site:ieee.org "
    "OR whitepaper OR case study OR engineering blog"
)

# ---------------------------------------------------------------------------
# Authority domains for deployment_status inference 
# Fixes ERR-B23: Hardcoded lists have been replaced by an LLM-based 
# `classify_deployment_status` mechanism imported from anthropic_client.
# ---------------------------------------------------------------------------


def _confidence_from_rank(rank: int, total: int) -> float:
    """Top web result = 78%, last = 55%."""
    if total <= 1:
        return 78.0
    return round(78.0 - (rank / max(total - 1, 1)) * 23.0, 1)


async def search_web(query: StructuralQuery) -> List[SearchResult]:
    """
    Layer 3: Web Search via Serper.dev — Industry whitepapers, Case studies, Tech blogs.

    Fixes L3-8: deployment_status is now inferred from the result URL domain
    rather than hardcoded to "blog" for all results. High-authority engineering
    sources (AWS, Google Cloud, IEEE, etc.) receive proportionally higher
    evidence scores in bridge_ranker.py.

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

            # Fixes ERR-B23: Gather deployment statuses concurrently using LLM
            tasks = []
            for item in organic:
                snippet = item.get("snippet", item.get("title", ""))
                url = item.get("link", "")
                tasks.append(classify_deployment_status(url, snippet))
                
            statuses = await asyncio.gather(*tasks, return_exceptions=True)

            for rank, item in enumerate(organic):
                title = item.get("title", "Untitled Article")
                snippet = item.get("snippet", title)
                url = item.get("link")

                confidence = _confidence_from_rank(rank, total)
                
                status_result = statuses[rank]
                deployment_status = "blog" if isinstance(status_result, Exception) else status_result

                results.append(SearchResult(
                    source=SearchSource.WEB,
                    title=title,
                    summary=snippet,
                    url=url,
                    confidence=confidence,
                    original_query=query,
                    citation_count=0,
                    replication_count=0,
                    deployment_status=deployment_status,
                ))

    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        print(f"[search_web] Serper.dev API error: {exc}. Returning empty results.")

    return results
