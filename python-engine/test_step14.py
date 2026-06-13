"""
Test Suite — Layer 3 Step 14: Bridge Validity Ranker
Converted from a print-only demo script to a real pytest test suite.
"""
import pytest
from schemas.graph import CausalGraph, Node, Edge
from schemas.layer3 import StructuralQuery, Step14Request
from services.layer3.step11_search_engine import run_step_11_search
from services.layer3.relation_extractor import run_relation_extraction
from services.layer3.isomorphism_matcher import match_graphs, Step13Request
from services.layer3.bridge_ranker import rank_bridges


TARGET_GRAPH = CausalGraph(
    nodes=[
        Node(id="A", label="Node A", confidence=100.0),
        Node(id="B", label="Node B", confidence=100.0),
        Node(id="C", label="Node C", confidence=100.0),
        Node(id="D", label="Node D", confidence=100.0),
    ],
    edges=[
        Edge(source="A", target="C", relation="FLOWS_TO", confidence=100.0),
        Edge(source="B", target="C", relation="FLOWS_TO", confidence=100.0),
        Edge(source="C", target="D", relation="CAUSES",   confidence=100.0),
    ]
)

QUERY_1 = StructuralQuery(
    original_node_id="C",
    original_confidence=45.0,
    structural_description="generic structural query 1"
)

QUERY_2 = StructuralQuery(
    original_node_id="node_isolated",
    original_confidence=20.0,
    structural_description="generic structural query 2"
)

QUERY_3 = StructuralQuery(
    original_node_id="node_high",
    original_confidence=95.0,
    structural_description="generic structural query 3"
)


async def _run_full_pipeline(query: StructuralQuery):
    step11 = await run_step_11_search(query)
    mechanisms = await run_relation_extraction(step11.results)
    s13_req = Step13Request(target_graph=TARGET_GRAPH, candidates=mechanisms)
    s13_resp = await match_graphs(s13_req)
    s14_req = Step14Request(
        matches=s13_resp.matches,
        user_domain_context=query.structural_description
    )
    s14_resp = await rank_bridges(s14_req)
    return s14_resp


@pytest.mark.asyncio
async def test_step14_top_bridges():
    """Step 14 must return at most 3 ranked bridges with valid scores."""
    response = await _run_full_pipeline(QUERY_1)

    assert response is not None, "Response must not be None"
    assert isinstance(response.top_bridges, list), "top_bridges must be a list"
    assert len(response.top_bridges) <= 3, "Step 14 must return at most 3 bridges"

    for bridge in response.top_bridges:
        scores = bridge.scores
        assert 0.0 <= scores.structural_match <= 1.0
        assert 0.0 <= scores.constraint_compatibility <= 1.0
        assert 0.0 <= scores.solution_transferability <= 1.0
        assert 0.0 <= scores.evidence_strength <= 1.0
        assert 0.0 <= scores.final_score <= 1.0


@pytest.mark.asyncio
async def test_step14_isolated_node_no_crash():
    """Step 14 must handle an empty matches list gracefully."""
    response = await _run_full_pipeline(QUERY_2)

    assert response is not None, "Response must not be None"
    assert isinstance(response.top_bridges, list), "top_bridges must be a list"


@pytest.mark.asyncio
async def test_step14_bridges_sorted_descending():
    """Bridges in the response must be sorted descending by final_score."""
    response = await _run_full_pipeline(QUERY_3)

    scores = [b.scores.final_score for b in response.top_bridges]
    assert scores == sorted(scores, reverse=True), \
        f"Bridges must be sorted descending by final_score, got: {scores}"
