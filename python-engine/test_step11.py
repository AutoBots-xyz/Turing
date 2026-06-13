"""
Test Suite — Layer 3 Step 11: 4-Layer Search Engine
Converted from a print-only demo script to a real pytest test suite.
"""
import pytest
from schemas.layer3 import StructuralQuery
from services.layer3.step11_search_engine import run_step_11_search

# ---------------------------------------------------------------------------
# Query Variants
# ---------------------------------------------------------------------------

QUERY_1 = StructuralQuery(
    original_node_id="node_123",
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


@pytest.mark.asyncio
async def test_step11_low_confidence_bottleneck():
    """A low-confidence generic node should return at least one merged result."""
    response = await run_step_11_search(QUERY_1)

    assert response is not None, "Response should not be None"
    assert len(response.results) > 0, "At least one MergedResult should be returned"

    for result in response.results:
        assert result.title, "Result title must not be empty"
        assert result.merged_summary, "Result merged_summary must not be empty"
        assert len(result.sources) > 0, "Result must list at least one SearchSource"
        assert 0.0 <= result.confidence <= 100.0, "Confidence must be in [0, 100]"


@pytest.mark.asyncio
async def test_step11_isolated_node():
    """An isolated node with no edges should still produce a valid response."""
    response = await run_step_11_search(QUERY_2)

    assert response is not None, "Response should not be None"
    assert isinstance(response.results, list), "results must be a list (even if empty)"


@pytest.mark.asyncio
async def test_step11_high_confidence_node():
    """A high-confidence node should return a valid response without crashing."""
    response = await run_step_11_search(QUERY_3)

    assert response is not None, "Response should not be None"
    assert isinstance(response.results, list), "results must be a list"

    for result in response.results:
        assert result.title, "Result title must not be empty"
        assert 0.0 <= result.confidence <= 100.0, "Confidence must be in [0, 100]"
