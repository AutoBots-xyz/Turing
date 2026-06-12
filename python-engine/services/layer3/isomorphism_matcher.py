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
    Calculates structural similarity using NetworkX graph algorithms.

    Strategy (layered scoring):
    1. In-degree sequence similarity  — captures bottleneck topology (weight 0.35)
    2. Out-degree sequence similarity — captures fanout structure   (weight 0.25)
    3. Bottleneck alignment          — max in-degree node match     (weight 0.25)
    4. Graph density similarity      — overall connectivity ratio   (weight 0.15)

    Fixes L3-5: Each sub-score is now clamped to [0.0, 1.0] with max(0.0, ...)
    before the weighted sum. Previously, numerical edge cases could produce
    negative composite scores that were silently misclassified as DISCARDED.

    Fixes L3-6: The out-degree fallback when max_possible_diff == 0 was
    incorrectly returning 0 (worst match) instead of 1.0 (perfect match).
    Two graphs that both have zero out-degrees are a perfect structural match
    on that dimension — they should score 1.0, not 0.
    """
    target_nx = _to_digraph(target)
    candidate_nx = _to_digraph(candidate)

    t_nodes = target_nx.number_of_nodes()
    c_nodes = candidate_nx.number_of_nodes()

    if t_nodes == 0 or c_nodes == 0:
        return 0.0

    # --- Score 1: In-degree sequence similarity ---
    t_in_degs = sorted([d for _, d in target_nx.in_degree()], reverse=True)
    c_in_degs = sorted([d for _, d in candidate_nx.in_degree()], reverse=True)

    max_len = max(len(t_in_degs), len(c_in_degs))
    t_in_degs += [0] * (max_len - len(t_in_degs))
    c_in_degs += [0] * (max_len - len(c_in_degs))

    in_max_possible = max_len * max(max(t_in_degs), max(c_in_degs), 1)
    in_actual_diff = sum(abs(a - b) for a, b in zip(t_in_degs, c_in_degs))
    degree_seq_score = 1.0 - (in_actual_diff / in_max_possible)

    # --- Score 2: Out-degree sequence similarity ---
    t_out_degs = sorted([d for _, d in target_nx.out_degree()], reverse=True)
    c_out_degs = sorted([d for _, d in candidate_nx.out_degree()], reverse=True)

    max_len = max(len(t_out_degs), len(c_out_degs))
    t_out_degs += [0] * (max_len - len(t_out_degs))
    c_out_degs += [0] * (max_len - len(c_out_degs))

    out_max_possible = max_len * max(max(t_out_degs), max(c_out_degs), 1)
    out_actual_diff = sum(abs(a - b) for a, b in zip(t_out_degs, c_out_degs))

    # Fixes L3-6: when out_max_possible == 0 both graphs have all-zero out-degrees
    # → perfect structural match on this dimension → score = 1.0 (was incorrectly 0).
    if out_max_possible == 0:
        out_degree_score = 1.0
    else:
        out_degree_score = 1.0 - (out_actual_diff / out_max_possible)

    # --- Score 3: Structural bottleneck alignment ---
    t_max_in = max((d for _, d in target_nx.in_degree()), default=0)
    c_max_in = max((d for _, d in candidate_nx.in_degree()), default=0)
    if t_max_in == 0 and c_max_in == 0:
        bottleneck_score = 1.0   # Both graphs have no bottleneck — perfect match
    else:
        bottleneck_score = max(0.0, 1.0 - abs(t_max_in - c_max_in) / max(t_max_in, c_max_in, 1))

    # --- Score 4: Graph density similarity ---
    t_density = nx.density(target_nx)
    c_density = nx.density(candidate_nx)
    density_score = 1.0 - abs(t_density - c_density)

    # --- Weighted composite score ---
    # Fixes L3-5: each sub-score clamped to [0.0, 1.0] to prevent negative totals
    # from numerical edge cases propagating into the final score.
    score = (
        max(0.0, min(1.0, degree_seq_score))  * 0.35 +
        max(0.0, min(1.0, out_degree_score))  * 0.25 +
        max(0.0, min(1.0, bottleneck_score))  * 0.25 +
        max(0.0, min(1.0, density_score))     * 0.15
    ) * 100.0

    return round(min(100.0, max(0.0, score)), 2)


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
