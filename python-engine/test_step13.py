"""
Test Suite — Layer 3 Step 13: Graph Isomorphism Matcher
Converted from a print-only demo script to a real pytest test suite.
Fixes Error 3 (3 diverse query variants) and Error 4 (proper assert statements).
"""
import asyncio
import pytest

from schemas.graph import CausalGraph, Node, Edge
from schemas.layer3 import StructuralQuery, Step13Request, MatchType
from services.layer3.step11_search_engine import run_step_11_search
from services.layer3.relation_extractor import run_relation_extraction
from services.layer3.isomorphism_matcher import match_graphs


# ---------------------------------------------------------------------------
# Shared Target Graph — Two inputs → Bottleneck → Crash
# ---------------------------------------------------------------------------

TARGET_GRAPH = CausalGraph(
    nodes=[
        Node(id="A", label="Input 1",        confidence=100.0),
        Node(id="B", label="Input 2",        confidence=100.0),
        Node(id="C", label="Bottleneck Node", confidence=100.0),
        Node(id="D", label="System Crash",   confidence=100.0),
    ],
    edges=[
        Edge(source="A", target="C", relation="FLOWS_TO", confidence=100.0),
        Edge(source="B", target="C", relation="FLOWS_TO", confidence=100.0),
        Edge(source="C", target="D", relation="CAUSES",   confidence=100.0),
    ]
)

# ---------------------------------------------------------------------------
# Query Variants (fixes Error 3 — was single hardcoded query)
# ---------------------------------------------------------------------------

QUERY_BOTTLENECK = StructuralQuery(
    original_node_id="C",
    original_confidence=45.0,
    structural_description="two inputs shared bottleneck crash under combined load"
)

QUERY_ISOLATED = StructuralQuery(
    original_node_id="node_isolated",
    original_confidence=20.0,
    structural_description="single isolated node with no causal inputs or outputs"
)

QUERY_HIGH_CONF = StructuralQuery(
    original_node_id="node_high",
    original_confidence=95.0,
    structural_description="stable high-confidence linear throughput node"
)


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _run_pipeline(query: StructuralQuery):
    """Helper: runs steps 11 → 12 → 13 and returns (step13_response, mechanisms)."""
    step11_response = run(run_step_11_search(query))
    mechanisms = run(run_relation_extraction(step11_response.results))
    request = Step13Request(target_graph=TARGET_GRAPH, candidates=mechanisms)
    response = run(match_graphs(request))
    return response, mechanisms


# ---------------------------------------------------------------------------
# Test 1 — Bottleneck query: matcher should return matches with valid scores
# ---------------------------------------------------------------------------

def test_step13_bottleneck_returns_valid_matches():
    """Step 13 on a bottleneck query must return matches with valid isomorphism scores."""
    response, mechanisms = _run_pipeline(QUERY_BOTTLENECK)

    assert response is not None, "Response must not be None"
    assert isinstance(response.matches, list), "matches must be a list"

    if len(mechanisms) > 0:
        # If we have candidates, we must have match results
        assert len(response.matches) > 0, "Matcher should return at least one result"

    for match in response.matches:
        assert 0.0 <= match.isomorphism_score <= 100.0, \
            f"isomorphism_score must be in [0, 100], got {match.isomorphism_score}"
        assert match.match_type in MatchType.__members__.values(), \
            f"match_type must be a valid MatchType, got {match.match_type}"
        assert match.mechanism is not None, "match.mechanism must not be None"

    print(f"\n[PASS] Bottleneck: {len(response.matches)} match(es) returned")
    for m in response.matches:
        print(f"  - {m.mechanism.source_result.title}: {m.isomorphism_score:.1f}% [{m.match_type.value}]")


# ---------------------------------------------------------------------------
# Test 2 — Isolated node: matcher must not crash on sparse/empty candidates
# ---------------------------------------------------------------------------

def test_step13_isolated_node_no_crash():
    """Step 13 must handle empty or minimal candidate lists gracefully."""
    response, _ = _run_pipeline(QUERY_ISOLATED)

    assert response is not None, "Response must not be None"
    assert isinstance(response.matches, list), "matches must be a list"

    print(f"\n[PASS] Isolated node: {len(response.matches)} match(es) (may be 0)")


# ---------------------------------------------------------------------------
# Test 3 — High-confidence node: DISCARDED matches must score below threshold
# ---------------------------------------------------------------------------

def test_step13_discarded_matches_below_threshold():
    """Any match classified as DISCARDED must have an isomorphism_score < 30.0."""
    response, _ = _run_pipeline(QUERY_HIGH_CONF)

    for match in response.matches:
        if match.match_type == MatchType.DISCARDED:
            assert match.isomorphism_score < 30.0, (
                f"A DISCARDED match must score below 30.0, got {match.isomorphism_score:.1f}%"
            )
        elif match.match_type == MatchType.WEAK_PARTIAL:
            assert 30.0 <= match.isomorphism_score < 70.0, (
                f"A WEAK_PARTIAL match must score in [30, 70), got {match.isomorphism_score:.1f}%"
            )
        elif match.match_type == MatchType.STRONG_PARTIAL:
            assert match.isomorphism_score >= 70.0, (
                f"A STRONG_PARTIAL match must score >= 70.0, got {match.isomorphism_score:.1f}%"
            )

    print(f"\n[PASS] High-confidence: {len(response.matches)} match(es), thresholds verified")



