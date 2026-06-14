"""
Test Suite — Layer 3 Step 11: 4-Layer Search Engine
Converted from a print-only demo script to a real pytest test suite.
Fixes Error 3 (3 diverse query variants) and Error 4 (proper assert statements).
"""
import asyncio
import pytest

from schemas.layer3 import StructuralQuery
from services.layer3.step11_search_engine import run_step_11_search


# ---------------------------------------------------------------------------
# Query Variants (fixes Error 3 — was a single hardcoded query in all tests)
# ---------------------------------------------------------------------------

QUERY_LOW_CONF_BOTTLENECK = StructuralQuery(
    original_node_id="node_123",
    original_confidence=45.0,
    structural_description="two inputs shared bottleneck crash under combined load"
)

QUERY_ISOLATED_NODE = StructuralQuery(
    original_node_id="node_isolated",
    original_confidence=20.0,
    structural_description="single isolated node with no causal inputs or outputs"
)

QUERY_HIGH_CONF_NODE = StructuralQuery(
    original_node_id="node_high",
    original_confidence=95.0,
    structural_description="well-understood linear throughput node with stable output"
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Test 1 — Low-confidence bottleneck node (canonical happy path)
# ---------------------------------------------------------------------------

def test_step11_low_confidence_bottleneck():
    """A low-confidence bottleneck node should return at least one merged result."""
    response = run(run_step_11_search(QUERY_LOW_CONF_BOTTLENECK))

    # The pipeline must return something
    assert response is not None, "Response should not be None"
    assert len(response.results) > 0, "At least one MergedResult should be returned"

    # Each result must have the required fields populated
    for result in response.results:
        assert result.title, "Result title must not be empty"
        assert result.merged_summary, "Result merged_summary must not be empty"
        assert len(result.sources) > 0, "Result must list at least one SearchSource"
        assert 0.0 <= result.confidence <= 100.0, "Confidence must be in [0, 100]"

    print(f"\n[PASS] Low-confidence bottleneck: {len(response.results)} result(s) returned")


# ---------------------------------------------------------------------------
# Test 2 — Isolated node (edge case: 0 edges)
# ---------------------------------------------------------------------------

def test_step11_isolated_node():
    """An isolated node with no edges should still produce a valid (possibly sparse) response."""
    response = run(run_step_11_search(QUERY_ISOLATED_NODE))

    assert response is not None, "Response should not be None"
    # The pipeline should not crash — it may return 0 results but must not raise
    assert isinstance(response.results, list), "results must be a list (even if empty)"

    print(f"\n[PASS] Isolated node: {len(response.results)} result(s) returned (may be 0)")


# ---------------------------------------------------------------------------
# Test 3 — High-confidence node (should be filtered or return fewer results)
# ---------------------------------------------------------------------------

def test_step11_high_confidence_node():
    """A high-confidence node should return a valid response without crashing."""
    response = run(run_step_11_search(QUERY_HIGH_CONF_NODE))

    assert response is not None, "Response should not be None"
    assert isinstance(response.results, list), "results must be a list"

    # If results are returned, they must be structurally valid
    for result in response.results:
        assert result.title, "Result title must not be empty"
        assert 0.0 <= result.confidence <= 100.0, "Confidence must be in [0, 100]"

    print(f"\n[PASS] High-confidence node: {len(response.results)} result(s) returned")



