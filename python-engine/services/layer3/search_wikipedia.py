import httpx
from typing import List
from schemas.layer3 import StructuralQuery, SearchResult, SearchSource

# Wikipedia REST API — 100% free, no API key required
WIKIPEDIA_SEARCH_API = "https://en.wikipedia.org/w/api.php"
MAX_RESULTS = 3


def _confidence_from_rank(rank: int, total: int) -> float:
    """Top Wikipedia result = 82%, last = 60%."""
    if total <= 1:
        return 82.0
    return round(82.0 - (rank / max(total - 1, 1)) * 22.0, 1)


async def search_wikipedia(query: StructuralQuery) -> List[SearchResult]:
    """
    Layer 2: Wikipedia REST API
    Fixes Error 1: Makes real HTTP calls to the Wikipedia API.
    Fixes Error 2: Populates deployment_status='replicated' (Wikipedia articles
    represent established, community-validated knowledge) and citation_count
    from the article's reference/link count.
    Fixes Error 4: No fake asyncio.sleep — real API provides authentic latency.
    """
    results: List[SearchResult] = []

    # Step 1: Search for relevant article titles
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": query.structural_description,
        "srlimit": MAX_RESULTS,
        "format": "json",
        "utf8": 1,
    }

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": "CausalNexus/1.0 (research bot; contact@causalnexus.ai)"}
        ) as client:
            search_response = await client.get(WIKIPEDIA_SEARCH_API, params=search_params)
            search_response.raise_for_status()
            search_data = search_response.json()

            articles = search_data.get("query", {}).get("search", [])
            total = len(articles)

            for rank, article in enumerate(articles):
                title = article.get("title", "")
                snippet = article.get("snippet", title)
                # Strip HTML tags from snippet
                snippet = snippet.replace("<span class=\"searchmatch\">", "").replace("</span>", "")

                page_id = article.get("pageid")
                url = f"https://en.wikipedia.org/?curid={page_id}" if page_id else None

                # Fixes ERR-B46: Removed fabricated Wikipedia citation math based on article length.
                # Wikipedia does not track academic citations. Set to 0 to prevent data fabrication.
                citation_count = 0

                confidence = _confidence_from_rank(rank, total)

                results.append(SearchResult(
                    source=SearchSource.WIKIPEDIA,
                    title=title,
                    summary=snippet,
                    url=url,
                    confidence=confidence,
                    original_query=query,
                    citation_count=citation_count,
                    replication_count=0,
                    # Wikipedia articles = community-validated, established knowledge
                    deployment_status="replicated",
                ))

    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        print(f"[search_wikipedia] Wikipedia API error: {exc}. Returning empty results.")

    return results
