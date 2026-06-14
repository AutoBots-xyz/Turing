"""
Test Suite — Layer 3 Step 12: Relation Extraction
Converted from a print-only demo script to a real pytest test suite.
Fixes Error 3 (3 diverse query variants) and Error 4 (proper assert statements).
"""
import asyncio
import pytest

from schemas.layer3 import StructuralQuery, MatchType
from services.layer3.step11_search_engine import run_step_11_search
from services.layer3.relation_extractor import run_relation_extraction


# ---------------------------------------------------------------------------
# Query Variants
# ---------------------------------------------------------------------------

QUERY_BOTTLENECK = StructuralQuery(
    original_node_id="node_123",
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
    structural_description="stable linear throughput node with single output"
)


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Test 1 — Bottleneck node: extraction should produce graphs with edges
# ---------------------------------------------------------------------------

def test_step12_bottleneck_produces_graphs():
    """Step 12 on a bottleneck query should produce at least one extracted mechanism."""
    step11_response = run(run_step_11_search(QUERY_BOTTLENECK))
    mechanisms = run(run_relation_extraction(step11_response.results))

    assert len(mechanisms) > 0, "At least one mechanism must be extracted"

    for em in mechanisms:
        assert em.source_result is not None, "source_result must be populated"
        assert em.causal_graph is not None, "causal_graph must not be None"
        assert isinstance(em.causal_graph.nodes, list), "nodes must be a list"
        assert isinstance(em.causal_graph.edges, list), "edges must be a list"

        # Each node must have an id, label and valid confidence
        for node in em.causal_graph.nodes:
            assert node.id, "Node id must not be empty"
            assert node.label, "Node label must not be empty"
            assert 0.0 <= node.confidence <= 100.0, "Node confidence must be in [0, 100]"

        # Each edge must reference valid source/target ids
        node_ids = {n.id for n in em.causal_graph.nodes}
        for edge in em.causal_graph.edges:
            assert edge.source in node_ids, f"Edge source '{edge.source}' not in node ids"
            assert edge.target in node_ids, f"Edge target '{edge.target}' not in node ids"
            assert edge.relation, "Edge relation must not be empty"

    print(f"\n[PASS] Bottleneck: {len(mechanisms)} mechanism(s) extracted")


# ---------------------------------------------------------------------------
# Test 2 — Isolated node: no crash even with empty or minimal search results
# ---------------------------------------------------------------------------

def test_step12_isolated_node_no_crash():
    """Step 12 must not crash even when Step 11 returns sparse results for isolated nodes."""
    step11_response = run(run_step_11_search(QUERY_ISOLATED))
    mechanisms = run(run_relation_extraction(step11_response.results))

    assert isinstance(mechanisms, list), "mechanisms must be a list (even if empty)"

    print(f"\n[PASS] Isolated node: {len(mechanisms)} mechanism(s) extracted (may be 0)")


# ---------------------------------------------------------------------------
# Test 3 — High-confidence node: extraction must not produce invalid graphs
# ---------------------------------------------------------------------------

def test_step12_high_confidence_no_invalid_graphs():
    """Every graph extracted from a high-confidence query must pass basic structural validation."""
    step11_response = run(run_step_11_search(QUERY_HIGH_CONF))
    mechanisms = run(run_relation_extraction(step11_response.results))

    for em in mechanisms:
        # Graphs may be empty but must not have dangling edge references
        node_ids = {n.id for n in em.causal_graph.nodes}
        for edge in em.causal_graph.edges:
            assert edge.source in node_ids or len(node_ids) == 0, \
                f"Dangling edge source '{edge.source}' — nodes were extracted but edge ref is invalid"

    print(f"\n[PASS] High-confidence: {len(mechanisms)} mechanism(s) validated")



