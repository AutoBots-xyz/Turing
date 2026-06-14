"""
routers/layer3.py — Layer 3 Cross-Domain Search Endpoints

Fixes Error 4 (Batch 4): This file was completely empty.
Exposes the /search, /extract, /match, and /rank endpoints
that wire up the Layer 3 service pipeline.
"""
from fastapi import APIRouter, HTTPException

from schemas.layer3 import (
    Step11Response, Step12Response, Step13Request, Step13Response,
    Step14Request, Step14Response, StructuralQuery, MergedResult
)
import asyncio
import logging

logger = logging.getLogger(__name__)
from typing import List
from services.layer3.search_papers import search_papers
from services.layer3.search_wikipedia import search_wikipedia
from services.layer3.search_web import search_web
from services.layer3.search_patents import search_patents
from services.layer3.deduplicator import deduplicate_and_merge
from services.layer3.contradiction_detector import detect_contradictions
from services.layer3.relation_extractor import run_relation_extraction
from services.layer3.isomorphism import match_graphs
from services.layer3.bridge_ranker import rank_bridges

router = APIRouter()


_SOURCE_TIMEOUT_SECONDS = 12.0

async def _timed_search(coro, source_name: str) -> List:
    """
    Wraps each individual search coroutine in asyncio.wait_for()
    with a hard deadline.
    """
    try:
        return await asyncio.wait_for(coro, timeout=_SOURCE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.warning(f"[layer3_search] {source_name} timed out after {_SOURCE_TIMEOUT_SECONDS}s.")
        return []
    except Exception as exc:
        logger.error(f"[layer3_search] {source_name} error: {exc}")
        return []

async def run_step_11_search(query: StructuralQuery) -> Step11Response:
    """
    Step 11 — 4 LAYER SEARCH ENGINE
    """
    results_nested = await asyncio.gather(
        _timed_search(search_papers(query),    "search_papers"),
        _timed_search(search_wikipedia(query), "search_wikipedia"),
        _timed_search(search_web(query),       "search_web"),
        _timed_search(search_patents(query),   "search_patents"),
        return_exceptions=True,
    )

    all_results = []
    for res in results_nested:
        if isinstance(res, Exception):
            logger.error(f"[layer3_search] Unexpected gather error: {res}")
        elif isinstance(res, list):
            all_results.extend(res)

    merged_results = await deduplicate_and_merge(all_results)
    final_results = await detect_contradictions(merged_results)

    return Step11Response(
        query=query,
        results=final_results,
    )

@router.post(
    "/search",
    response_model=Step11Response,
    summary="Step 11 — Run 4-layer cross-domain search"
)
async def search(query: StructuralQuery):
    """
    Accepts a domain-blind structural query and runs parallel searches
    across Papers (Semantic Scholar), Wikipedia, Web (Serper), and Patents.
    Returns deduplicated MergedResult objects with optional contradiction analysis.
    """
    try:
        return await run_step_11_search(query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/extract",
    response_model=Step12Response,
    summary="Step 12 — Extract causal graphs from search results"
)
async def extract(response: Step11Response):
    """
    Accepts the Step 11 response and runs LLM-based causal graph extraction
    on each MergedResult. Returns a list of ExtractedMechanism objects.
    """
    try:
        mechanisms = await run_relation_extraction(response.results)
        return Step12Response(extracted_mechanisms=mechanisms)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/match",
    response_model=Step13Response,
    summary="Step 13 — Graph isomorphism matching"
)
async def match(request: Step13Request):
    """
    Compares each candidate ExtractedMechanism against the user's target graph
    using structural isomorphism scoring. Returns IsomorphismMatch objects
    classified as PERFECT / STRONG_PARTIAL / WEAK_PARTIAL / DISCARDED.
    """
    try:
        return await match_graphs(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/rank",
    response_model=Step14Response,
    summary="Step 14 — Bridge validity ranking"
)
async def rank(request: Step14Request):
    """
    Scores surviving matches on 4 validity factors (structural match,
    constraint compatibility, solution transferability, evidence strength)
    and returns the Top 3 cross-domain bridges.
    """
    try:
        return await rank_bridges(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
