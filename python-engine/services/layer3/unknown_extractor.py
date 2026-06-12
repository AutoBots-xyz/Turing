from typing import List
from schemas.graph import CausalGraph, Node
from schemas.layer3 import StructuralQuery
from services.anthropic_client import generate_domain_blind_query

def extract_unknown_nodes(graph: CausalGraph, confidence_threshold: float = 80.0) -> List[Node]:
    """
    Extracts all unknown nodes, based on explicit flag or low confidence.
    """
    unknowns = []
    for node in graph.nodes:
        if node.is_unknown or node.confidence < confidence_threshold:
            unknowns.append(node)
    return unknowns

def rank_nodes(nodes: List[Node]) -> List[Node]:
    """
    Ranks nodes by importance, where lowest confidence is most important.
    """
    return sorted(nodes, key=lambda n: n.confidence)

def run_step_10(graph: CausalGraph, confidence_threshold: float = 80.0) -> List[StructuralQuery]:
    """
    Main orchestrator for Layer 3 Step 10:
    1. Extract unknown nodes
    2. Rank them
    3. Convert each into a domain-blind structural query
    """
    unknown_nodes = extract_unknown_nodes(graph, confidence_threshold)
    ranked_nodes = rank_nodes(unknown_nodes)
    
    queries = []
    for node in ranked_nodes:
        structural_desc = generate_domain_blind_query(node, graph)
        queries.append(StructuralQuery(
            original_node_id=node.id,
            original_confidence=node.confidence,
            structural_description=structural_desc
        ))
        
    return queries
