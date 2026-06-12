import os
from typing import Optional
import asyncio
from schemas.graph import CausalGraph, Node, Edge

def generate_domain_blind_query(node: Node, graph: CausalGraph) -> str:
    """
    Calls Anthropic API to convert a domain-specific node into a domain-blind structural query.
    """
    # Get local context for the node
    incoming = [e for e in graph.edges if e.target == node.id]
    outgoing = [e for e in graph.edges if e.source == node.id]
    
    # In a fully functional implementation, this would use the anthropic python SDK
    # to prompt Claude with the node context and graph structure.
    # Example:
    # prompt = f"Given node {node.label} with incoming edges {incoming} and outgoing edges {outgoing}, extract a domain-blind structural mechanism."
    
    # Placeholder mock response for now
    return f"domain blind structural mechanism involving {len(incoming)} inputs and {len(outgoing)} outputs"

async def extract_causal_graph_from_text(text: str) -> CausalGraph:
    """
    Step 12 LLM call: Extracts a mini causal graph from a text summary.
    As per 'different.md' rules:
    - Nodes must be nouns.
    - Edges must be verbs (e.g., INHIBITS, ACTIVATES).
    - Confidence is scored based on the strength of the language.
    """
    await asyncio.sleep(0.5)  # Simulate API latency
    
    # Mocking semantic extraction based on common phrases
    nodes = []
    edges = []
    
    if "bypass" in text.lower():
        # Extracted from the Boeing patent mock
        nodes = [
            Node(id="n1", label="Input Pressure", confidence=95.0),
            Node(id="n2", label="Bottleneck", confidence=95.0),
            Node(id="n3", label="Bypass Valve", confidence=95.0),
            Node(id="n4", label="System Failure", confidence=95.0)
        ]
        edges = [
            Edge(source="n1", target="n2", relation="OVERLOADS", confidence=95.0),
            Edge(source="n3", target="n2", relation="RELIEVES", confidence=95.0),
            Edge(source="n3", target="n4", relation="PREVENTS", confidence=90.0) # "prevents" = high confidence
        ]
    elif "conflicting" in text.lower():
        # Extracted from the contradicting patent mock
        nodes = [
            Node(id="n1", label="Input Pressure", confidence=80.0),
            Node(id="n2", label="Bottleneck", confidence=80.0),
            Node(id="n4", label="System Failure", confidence=80.0)
        ]
        edges = [
            Edge(source="n1", target="n2", relation="WIDENS", confidence=80.0),
            Edge(source="n1", target="n4", relation="MIGHT_PREVENT", confidence=40.0) # "might" = weak confidence
        ]
    else:
        # Generic mechanism
        nodes = [
            Node(id="n_a", label="Factor A", confidence=85.0),
            Node(id="n_b", label="Factor B", confidence=85.0)
        ]
        edges = [
            Edge(source="n_a", target="n_b", relation="INFLUENCES", confidence=60.0)
        ]
        
    return CausalGraph(nodes=nodes, edges=edges)

from typing import Tuple

async def evaluate_compatibility_and_transferability(domain_context: str, candidate_mechanism: str) -> Tuple[float, float]:
    """
    Step 14 LLM call: Evaluates constraint compatibility and solution transferability.
    Returns two floats between 0.0 and 1.0.
    """
    await asyncio.sleep(0.5)  # Simulate API latency
    
    # Mocking semantic grading based on common phrases
    # If the candidate mechanism explicitly mentions resolving "bottleneck crash", we give high scores.
    if "bypass" in candidate_mechanism.lower() or "bottleneck" in candidate_mechanism.lower():
        compatibility = 0.95
        transferability = 0.90
    else:
        compatibility = 0.60
        transferability = 0.50
        
    return compatibility, transferability

