"""
services/layer1/validator.py — Graph Validator

Fixes Error 5 (Batch 4): This file was completely empty.
Validates a CausalGraph before it is passed downstream to Layer 2.
Checks for structural integrity, data quality, and minimum requirements.
"""
from typing import List, Tuple

from schemas.graph import CausalGraph


class ValidationError(Exception):
    """Raised when a CausalGraph fails a critical validation check."""
    pass


def validate_graph(graph: CausalGraph) -> Tuple[bool, List[str]]:
    """
    Validates a CausalGraph for correctness and minimum data quality.

    Checks performed (in order):
    1. Graph is not empty (has nodes)
    2. All edge references (source/target) point to existing node ids
    3. No self-loops (a node causing itself)
    4. All node ids are unique
    5. All edge confidences are in [0, 100]
    6. At least one edge exists (a graph with only isolated nodes is useless)

    Parameters
    ----------
    graph : CausalGraph
        The graph to validate (output of pc_algorithm or ontology_builder).

    Returns
    -------
    Tuple[bool, List[str]]
        (is_valid, list_of_warnings_or_errors)
        is_valid is False only if a CRITICAL check fails.
        Warnings are non-critical issues that are logged but don't block.
    """
    issues: List[str] = []
    node_ids = {node.id for node in graph.nodes}

    # Critical: must have at least 2 nodes
    if len(graph.nodes) < 2:
        issues.append("CRITICAL: Graph has fewer than 2 nodes — no causal relationships possible.")
        return False, issues

    # Critical: duplicate node ids
    if len(node_ids) != len(graph.nodes):
        issues.append("CRITICAL: Duplicate node ids detected.")
        return False, issues

    # Critical: dangling edge references
    for edge in graph.edges:
        if edge.source not in node_ids:
            issues.append(f"CRITICAL: Edge source '{edge.source}' does not exist in nodes.")
            return False, issues
        if edge.target not in node_ids:
            issues.append(f"CRITICAL: Edge target '{edge.target}' does not exist in nodes.")
            return False, issues

    # Warning: self-loops
    for edge in graph.edges:
        if edge.source == edge.target:
            issues.append(f"WARNING: Self-loop detected on node '{edge.source}' — will be ignored downstream.")

    # Warning: no edges
    if not graph.edges:
        issues.append("WARNING: Graph has no edges — downstream Layer 2 simulation will be trivial.")

    # Warning: confidence out of range
    for node in graph.nodes:
        if not (0.0 <= node.confidence <= 100.0):
            issues.append(f"WARNING: Node '{node.id}' has confidence {node.confidence} outside [0, 100].")

    for edge in graph.edges:
        if not (0.0 <= edge.confidence <= 100.0):
            issues.append(f"WARNING: Edge {edge.source}→{edge.target} has confidence {edge.confidence} outside [0, 100].")

    return True, issues


def assert_valid_graph(graph: CausalGraph) -> None:
    """
    Convenience wrapper that raises ValidationError on failure.
    Use this in service code that must not continue with an invalid graph.
    """
    is_valid, issues = validate_graph(graph)
    if not is_valid:
        critical_issues = [i for i in issues if i.startswith("CRITICAL")]
        raise ValidationError(
            f"CausalGraph failed validation: {'; '.join(critical_issues)}"
        )
