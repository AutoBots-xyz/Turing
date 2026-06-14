"""
routers/layer3.py — Layer 3 Cross-Domain Search Endpoints

Fixes Error 4 (Batch 4): This file was completely empty.
Exposes the /search, /extract, /match, and /rank endpoints
that wire up the Layer 3 service pipeline.
"""
from fastapi import APIRouter, HTTPException

from schemas.layer3 import (
    Step11Response, Step12Response, Step13Request, Step13Response,
    Step14Request, Step14Response, StructuralQuery
)
from services.layer3.step11_search_engine import run_step_11_search
from services.layer3.relation_extractor import run_relation_extraction
from services.layer3.isomorphism import match_graphs
from services.layer3.bridge_ranker import rank_bridges

router = APIRouter()


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
