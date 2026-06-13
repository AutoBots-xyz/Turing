"""
Test Suite — Layer 3 Step 13: Graph Isomorphism Matcher
Converted from a print-only demo script to a real pytest test suite.
"""
import pytest
from schemas.graph import CausalGraph, Node, Edge
from schemas.layer3 import StructuralQuery, Step13Request, MatchType
from services.layer3.step11_search_engine import run_step_11_search
from services.layer3.relation_extractor import run_relation_extraction
from services.layer3.isomorphism_matcher import match_graphs


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


async def _run_pipeline(query: StructuralQuery):
    step11_response = await run_step_11_search(query)
    mechanisms = await run_relation_extraction(step11_response.results)
    request = Step13Request(target_graph=TARGET_GRAPH, candidates=mechanisms)
    response = await match_graphs(request)
    return response, mechanisms


@pytest.mark.asyncio
async def test_step13_returns_valid_matches():
    response, mechanisms = await _run_pipeline(QUERY_1)

    assert response is not None, "Response must not be None"
    assert isinstance(response.matches, list), "matches must be a list"

    if len(mechanisms) > 0:
        assert len(response.matches) > 0, "Matcher should return at least one result"

    for match in response.matches:
        assert 0.0 <= match.isomorphism_score <= 100.0, "isomorphism_score must be in [0, 100]"
        assert match.match_type in MatchType.__members__.values(), "match_type must be a valid MatchType"
        assert match.mechanism is not None, "match.mechanism must not be None"


@pytest.mark.asyncio
async def test_step13_isolated_node_no_crash():
    response, _ = await _run_pipeline(QUERY_2)
    assert response is not None, "Response must not be None"
    assert isinstance(response.matches, list), "matches must be a list"


@pytest.mark.asyncio
async def test_step13_discarded_matches_below_threshold():
    response, _ = await _run_pipeline(QUERY_3)

    for match in response.matches:
        if match.match_type == MatchType.DISCARDED:
            assert match.isomorphism_score < 30.0
        elif match.match_type == MatchType.WEAK_PARTIAL:
            assert 30.0 <= match.isomorphism_score < 70.0
        elif match.match_type == MatchType.STRONG_PARTIAL:
            assert match.isomorphism_score >= 70.0
