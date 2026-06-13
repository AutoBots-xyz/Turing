"""
Test Suite — Layer 3 Step 12: Relation Extraction
Converted from a print-only demo script to a real pytest test suite.
"""
import pytest
from schemas.layer3 import StructuralQuery, MatchType
from services.layer3.step11_search_engine import run_step_11_search
from services.layer3.relation_extractor import run_relation_extraction

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
async def test_step12_produces_graphs():
    """Step 12 should produce at least one extracted mechanism."""
    step11_response = await run_step_11_search(QUERY_1)
    mechanisms = await run_relation_extraction(step11_response.results)

    assert len(mechanisms) > 0, "At least one mechanism must be extracted"

    for em in mechanisms:
        assert em.source_result is not None, "source_result must be populated"
        assert em.causal_graph is not None, "causal_graph must not be None"
        assert isinstance(em.causal_graph.nodes, list), "nodes must be a list"
        assert isinstance(em.causal_graph.edges, list), "edges must be a list"

        for node in em.causal_graph.nodes:
            assert node.id, "Node id must not be empty"
            assert node.label, "Node label must not be empty"
            assert 0.0 <= node.confidence <= 100.0, "Node confidence must be in [0, 100]"

        node_ids = {n.id for n in em.causal_graph.nodes}
        for edge in em.causal_graph.edges:
            assert edge.source in node_ids, f"Edge source '{edge.source}' not in node ids"
            assert edge.target in node_ids, f"Edge target '{edge.target}' not in node ids"
            assert edge.relation, "Edge relation must not be empty"


@pytest.mark.asyncio
async def test_step12_isolated_node_no_crash():
    """Step 12 must not crash even when Step 11 returns sparse results."""
    step11_response = await run_step_11_search(QUERY_2)
    mechanisms = await run_relation_extraction(step11_response.results)

    assert isinstance(mechanisms, list), "mechanisms must be a list (even if empty)"


@pytest.mark.asyncio
async def test_step12_high_confidence_no_invalid_graphs():
    """Every graph extracted must pass basic structural validation."""
    step11_response = await run_step_11_search(QUERY_3)
    mechanisms = await run_relation_extraction(step11_response.results)

    for em in mechanisms:
        node_ids = {n.id for n in em.causal_graph.nodes}
        for edge in em.causal_graph.edges:
            assert edge.source in node_ids or len(node_ids) == 0, \
                f"Dangling edge source '{edge.source}'"
