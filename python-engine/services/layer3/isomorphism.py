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
    Calculates structural similarity using NetworkX's true Graph Edit Distance (GED).
    Replaces arbitrary magic number weights with a mathematically rigorous
    structural comparison.
    """
    target_nx = _to_digraph(target)
    candidate_nx = _to_digraph(candidate)

    t_nodes = target_nx.number_of_nodes()
    c_nodes = candidate_nx.number_of_nodes()

    if t_nodes == 0 and c_nodes == 0:
        return 100.0
    if t_nodes == 0 or c_nodes == 0:
        return 0.0

    # ERR-B43 fix: Use mathematical Graph Edit Distance instead of magic weights
    try:
        # Timeout applied to prevent NP-Hard hang on massive graphs
        ged = nx.graph_edit_distance(target_nx, candidate_nx, timeout=3.0)
        if ged is None:
            # Fallback heuristic if GED times out
            ged = abs(t_nodes - c_nodes) + abs(target_nx.number_of_edges() - candidate_nx.number_of_edges())
    except Exception:
        ged = abs(t_nodes - c_nodes) + abs(target_nx.number_of_edges() - candidate_nx.number_of_edges())

    # Maximum possible GED is the total sum of all nodes and edges in both graphs
    # (i.e. deleting everything in target, and inserting everything in candidate)
    max_ged = (t_nodes + target_nx.number_of_edges()) + (c_nodes + candidate_nx.number_of_edges())
    
    if max_ged == 0:
        return 100.0

    similarity = max(0.0, 1.0 - (ged / max_ged))
    return round(similarity * 100.0, 2)


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
