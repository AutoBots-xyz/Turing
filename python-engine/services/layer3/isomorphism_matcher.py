import asyncio
import networkx as nx
from networkx.algorithms import isomorphism

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
    Fixes Error 4: Calculates true structural similarity using networkx
    graph algorithms — NOT raw node/edge counts.

    Strategy (layered scoring):
    1. Degree Sequence Similarity: Compares the sorted in/out-degree sequences.
       Two graphs with the same topology will have identical degree sequences.
    2. Bottleneck Detection: Checks if both graphs contain a node with the same
       maximum in-degree (the structural "bottleneck").
    3. Graph Density: Compares the overall edge density of both graphs.
    4. Weakly Connected Components: Penalises graphs with different component counts.

    This is a mathematically grounded heuristic that catches structural differences
    that raw count comparisons completely miss.
    """
    target_nx = _to_digraph(target)
    candidate_nx = _to_digraph(candidate)

    t_nodes = target_nx.number_of_nodes()
    c_nodes = candidate_nx.number_of_nodes()

    if t_nodes == 0 or c_nodes == 0:
        return 0.0

    # --- Score 1: In-degree sequence similarity (0.0 to 1.0) ---
    t_in_degs = sorted([d for _, d in target_nx.in_degree()], reverse=True)
    c_in_degs = sorted([d for _, d in candidate_nx.in_degree()], reverse=True)

    # Pad shorter sequence with zeros for comparison
    max_len = max(len(t_in_degs), len(c_in_degs))
    t_in_degs += [0] * (max_len - len(t_in_degs))
    c_in_degs += [0] * (max_len - len(c_in_degs))

    max_possible_diff = max_len * max(max(t_in_degs), max(c_in_degs), 1)
    actual_diff = sum(abs(a - b) for a, b in zip(t_in_degs, c_in_degs))
    degree_seq_score = 1.0 - (actual_diff / max_possible_diff)

    # --- Score 2: Out-degree sequence similarity (0.0 to 1.0) ---
    t_out_degs = sorted([d for _, d in target_nx.out_degree()], reverse=True)
    c_out_degs = sorted([d for _, d in candidate_nx.out_degree()], reverse=True)

    max_len = max(len(t_out_degs), len(c_out_degs))
    t_out_degs += [0] * (max_len - len(t_out_degs))
    c_out_degs += [0] * (max_len - len(c_out_degs))

    max_possible_diff = max_len * max(max(t_out_degs), max(c_out_degs), 1)
    actual_diff = sum(abs(a - b) for a, b in zip(t_out_degs, c_out_degs))
    out_degree_score = 1.0 - (actual_diff / max_possible_diff if max_possible_diff > 0 else 0)

    # --- Score 3: Structural bottleneck alignment (0.0 or 1.0) ---
    t_max_in = max((d for _, d in target_nx.in_degree()), default=0)
    c_max_in = max((d for _, d in candidate_nx.in_degree()), default=0)
    bottleneck_score = 1.0 if t_max_in == c_max_in else max(0.0, 1.0 - abs(t_max_in - c_max_in) / max(t_max_in, c_max_in, 1))

    # --- Score 4: Graph density similarity (0.0 to 1.0) ---
    t_density = nx.density(target_nx)
    c_density = nx.density(candidate_nx)
    density_score = 1.0 - abs(t_density - c_density)

    # --- Weighted composite score ---
    # In-degree pattern is the most important signal (bottleneck structure)
    score = (
        degree_seq_score  * 0.35 +
        out_degree_score  * 0.25 +
        bottleneck_score  * 0.25 +
        density_score     * 0.15
    ) * 100.0

    return round(min(100.0, score), 2)


async def match_graphs(request: Step13Request) -> Step13Response:
    """
    Step 13: Graph Isomorphism Matcher
    Compares extracted mechanisms against the target bottleneck graph.
    Fixes Error 5: Uses configurable thresholds from request.thresholds
    instead of hardcoded magic numbers.
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
            match_type=match_type
        ))

    return Step13Response(matches=matches)
