import asyncio
import networkx as nx

from schemas.graph import CausalGraph
from schemas.layer3 import Step13Request, Step13Response, IsomorphismMatch, MatchType, ExtractedMechanism


def _to_digraph(graph: CausalGraph) -> nx.DiGraph:
    """Converts a CausalGraph schema object into a networkx DiGraph."""
    G = nx.DiGraph()
    for node in graph.nodes:
        G.add_node(node.id)
    for edge in graph.edges:
        G.add_edge(edge.source, edge.target)
    return G


def calculate_structural_similarity(target: CausalGraph, candidate: CausalGraph) -> float:
    """
    Calculates structural similarity using NetworkX's Graph Edit Distance (GED).

    Fixes ERR-B43: Replaces arbitrary 'magic number' heuristic weights with 
    a mathematically rigorous Graph Edit Distance. This calculates the optimal 
    topological mapping cost between two graphs without relying on tuned fallbacks.
    """
    target_nx = _to_digraph(target)
    candidate_nx = _to_digraph(candidate)

    t_nodes = target_nx.number_of_nodes()
    c_nodes = candidate_nx.number_of_nodes()
    t_edges = target_nx.number_of_edges()
    c_edges = candidate_nx.number_of_edges()

    if t_nodes == 0 and c_nodes == 0:
        return 100.0
    if t_nodes == 0 or c_nodes == 0:
        return 0.0

    max_edits = t_nodes + c_nodes + t_edges + c_edges

    # Calculate optimal Graph Edit Distance
    # We use node_match=lambda n1, n2: True to ensure we are calculating PURE 
    # structural isomorphism, independent of node labels across different domains.
    ged = nx.graph_edit_distance(
        target_nx, 
        candidate_nx, 
        node_match=lambda n1, n2: True,
        edge_match=lambda e1, e2: True,
        timeout=2.0
    )

    if ged is None:
        # Fallback to fast heuristic upper bound if the exact GED times out
        try:
            ged = next(nx.optimize_graph_edit_distance(
                target_nx, 
                candidate_nx, 
                node_match=lambda n1, n2: True,
                edge_match=lambda e1, e2: True
            ))
        except StopIteration:
            ged = max_edits

    score = max(0.0, 1.0 - (ged / max_edits)) * 100.0
    return round(score, 2)


async def match_graphs(request: Step13Request) -> Step13Response:
    """
    Step 13: Graph Isomorphism Matcher
    Compares each candidate ExtractedMechanism against the user's target graph
    using structural isomorphism scoring. Thresholds are configurable via
    request.thresholds (no more hardcoded magic numbers).
    """
    thresholds = request.thresholds
    matches = []

    for candidate in request.candidates:
        score = calculate_structural_similarity(request.target_graph, candidate.causal_graph)

        if score >= thresholds.perfect:
            match_type = MatchType.PERFECT
        elif score >= thresholds.strong_partial:
            match_type = MatchType.STRONG_PARTIAL
        elif score >= thresholds.weak_partial:
            match_type = MatchType.WEAK_PARTIAL
        else:
            match_type = MatchType.DISCARDED

        matches.append(IsomorphismMatch(
            mechanism=candidate,
            isomorphism_score=score,
            match_type=match_type,
        ))

    return Step13Response(matches=matches)
