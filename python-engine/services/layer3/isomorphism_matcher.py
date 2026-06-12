import networkx as nx
from typing import List

from schemas.graph import CausalGraph
from schemas.layer3 import Step13Request, Step13Response, IsomorphismMatch, MatchType, ExtractedMechanism

def calculate_structural_similarity(target: CausalGraph, candidate: CausalGraph) -> float:
    """
    Calculates the mathematical structural similarity between two CausalGraphs
    using networkx, ignoring semantic labels.
    """
    # Convert target to nx.DiGraph
    target_nx = nx.DiGraph()
    for node in target.nodes:
        target_nx.add_node(node.id)
    for edge in target.edges:
        target_nx.add_edge(edge.source, edge.target)
        
    # Convert candidate to nx.DiGraph
    candidate_nx = nx.DiGraph()
    for node in candidate.nodes:
        candidate_nx.add_node(node.id)
    for edge in candidate.edges:
        candidate_nx.add_edge(edge.source, edge.target)
        
    # Heuristic scoring based on basic structural topology
    target_nodes = target_nx.number_of_nodes()
    target_edges = target_nx.number_of_edges()
    
    cand_nodes = candidate_nx.number_of_nodes()
    cand_edges = candidate_nx.number_of_edges()
    
    if target_nodes == 0 or cand_nodes == 0:
        return 0.0
        
    # Basic node/edge ratio similarity
    node_ratio = min(target_nodes, cand_nodes) / max(target_nodes, cand_nodes)
    
    if max(target_edges, cand_edges) == 0:
        edge_ratio = 1.0 if target_edges == cand_edges else 0.0
    else:
        edge_ratio = min(target_edges, cand_edges) / max(target_edges, cand_edges)
        
    # We can also compare degree distributions
    target_in_degrees = sorted([d for n, d in target_nx.in_degree()])
    cand_in_degrees = sorted([d for n, d in candidate_nx.in_degree()])
    
    # Simple overlap of max bottleneck (max in-degree)
    target_max_in = max(target_in_degrees) if target_in_degrees else 0
    cand_max_in = max(cand_in_degrees) if cand_in_degrees else 0
    
    bottleneck_match = 1.0 if target_max_in == cand_max_in and target_max_in > 0 else 0.5
    
    # Weighted final score (out of 100)
    score = (node_ratio * 0.3 + edge_ratio * 0.3 + bottleneck_match * 0.4) * 100
    return min(100.0, score)

async def match_graphs(request: Step13Request) -> Step13Response:
    """
    Step 13: Graph Isomorphism Matcher
    Compares extracted mechanisms against the target bottleneck graph.
    Classifies matches as PERFECT, STRONG_PARTIAL, WEAK_PARTIAL, or DISCARDED.
    """
    matches = []
    
    for candidate in request.candidates:
        score = calculate_structural_similarity(request.target_graph, candidate.causal_graph)
        
        if score >= 100.0:
            match_type = MatchType.PERFECT
        elif score >= 70.0:
            match_type = MatchType.STRONG_PARTIAL
        elif score >= 30.0:
            match_type = MatchType.WEAK_PARTIAL
        else:
            match_type = MatchType.DISCARDED
            
        matches.append(IsomorphismMatch(
            mechanism=candidate,
            isomorphism_score=score,
            match_type=match_type
        ))
        
    return Step13Response(matches=matches)
