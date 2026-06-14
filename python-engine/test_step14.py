"""
Test Suite — Layer 3 Step 14: Bridge Validity Ranker
Converted from a print-only demo script to a real pytest test suite.
Fixes Error 3 (3 diverse query variants) and Error 4 (proper assert statements).
"""
import asyncio
import pytest

from schemas.graph import CausalGraph, Node, Edge
from schemas.layer3 import StructuralQuery, Step14Request
from services.layer3.step11_search_engine import run_step_11_search
from services.layer3.relation_extractor import run_relation_extraction
from services.layer3.isomorphism_matcher import match_graphs, Step13Request
from services.layer3.bridge_ranker import rank_bridges


# ---------------------------------------------------------------------------
# Shared target graph
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
# Query Variants (fixes Error 3)
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


def _run_full_pipeline(query: StructuralQuery):
    """Helper: runs steps 11 → 12 → 13 → 14."""
    step11 = run(run_step_11_search(query))
    mechanisms = run(run_relation_extraction(step11.results))
    s13_req = Step13Request(target_graph=TARGET_GRAPH, candidates=mechanisms)
    s13_resp = run(match_graphs(s13_req))
    s14_req = Step14Request(
        matches=s13_resp.matches,
        user_domain_context=query.structural_description
    )
    s14_resp = run(rank_bridges(s14_req))
    return s14_resp


# ---------------------------------------------------------------------------
# Test 1 — Bottleneck node: top bridges must have valid scores
# ---------------------------------------------------------------------------

def test_step14_bottleneck_top_bridges():
    """Step 14 must return at most 3 ranked bridges with all validity scores in [0, 1]."""
    response = _run_full_pipeline(QUERY_BOTTLENECK)

    assert response is not None, "Response must not be None"
    assert isinstance(response.top_bridges, list), "top_bridges must be a list"
    assert len(response.top_bridges) <= 3, "Step 14 must return at most 3 bridges"

    for bridge in response.top_bridges:
        scores = bridge.scores
        assert 0.0 <= scores.structural_match <= 1.0, \
            f"structural_match must be in [0, 1], got {scores.structural_match}"
        assert 0.0 <= scores.constraint_compatibility <= 1.0, \
            f"constraint_compatibility must be in [0, 1], got {scores.constraint_compatibility}"
        assert 0.0 <= scores.solution_transferability <= 1.0, \
            f"solution_transferability must be in [0, 1], got {scores.solution_transferability}"
        assert 0.0 <= scores.evidence_strength <= 1.0, \
            f"evidence_strength must be in [0, 1], got {scores.evidence_strength}"
        assert 0.0 <= scores.final_score <= 1.0, \
            f"final_score must be in [0, 1], got {scores.final_score}"

    print(f"\n[PASS] Bottleneck: {len(response.top_bridges)} bridge(s) ranked")
    for idx, b in enumerate(response.top_bridges, 1):
        print(f"  Rank #{idx}: {b.match.mechanism.source_result.title} — final: {b.scores.final_score:.4f}")


# ---------------------------------------------------------------------------
# Test 2 — Isolated node: no crash even with empty pipeline
# ---------------------------------------------------------------------------

def test_step14_isolated_node_no_crash():
    """Step 14 must handle an empty matches list gracefully."""
    response = _run_full_pipeline(QUERY_ISOLATED)

    assert response is not None, "Response must not be None"
    assert isinstance(response.top_bridges, list), "top_bridges must be a list"

    print(f"\n[PASS] Isolated node: {len(response.top_bridges)} bridge(s) returned (may be 0)")


# ---------------------------------------------------------------------------
# Test 3 — High-confidence node: bridges must be sorted descending by final_score
# ---------------------------------------------------------------------------

def test_step14_bridges_sorted_descending():
    """Bridges in the response must be sorted in descending order of final_score."""
    response = _run_full_pipeline(QUERY_HIGH_CONF)

    scores = [b.scores.final_score for b in response.top_bridges]
    assert scores == sorted(scores, reverse=True), \
        f"Bridges must be sorted descending by final_score, got: {scores}"

    print(f"\n[PASS] High-confidence: bridges sorted correctly — {scores}")



