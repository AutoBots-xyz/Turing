import asyncio

from schemas.graph import CausalGraph, Node, Edge
from schemas.layer3 import StructuralQuery, Step13Request
from services.layer3.step11_search_engine import run_step_11_search
from services.layer3.relation_extractor import run_relation_extraction
from services.layer3.isomorphism_matcher import match_graphs

async def main():
    print("Testing Layer 3 Step 13: Graph Isomorphism Matcher...")
    print("-------------------------------------------------------")
    
    # 1. Define the user's original Target Graph (The Bottleneck)
    # Two inputs (A, B) -> Bottleneck (C) -> Crash (D)
    target_graph = CausalGraph(
        nodes=[
            Node(id="A", label="Input 1", confidence=100.0),
            Node(id="B", label="Input 2", confidence=100.0),
            Node(id="C", label="Bottleneck Node", confidence=100.0),
            Node(id="D", label="System Crash", confidence=100.0)
        ],
        edges=[
            Edge(source="A", target="C", relation="FLOWS_TO", confidence=100.0),
            Edge(source="B", target="C", relation="FLOWS_TO", confidence=100.0),
            Edge(source="C", target="D", relation="CAUSES", confidence=100.0)
        ]
    )
    
    print(f"Target Graph: {len(target_graph.nodes)} nodes, {len(target_graph.edges)} edges")
    
    # 2. Run Step 11 & 12 to get Extracted Mechanisms
    query = StructuralQuery(
        original_node_id="C",
        original_confidence=45.0,
        structural_description="two inputs shared bottleneck crash under combined load"
    )
    print("Running Pipeline (Step 11 -> Step 12) to generate candidates...")
    step11_response = await run_step_11_search(query)
    extracted_mechanisms = await run_relation_extraction(step11_response.results)
    
    print(f"Extracted {len(extracted_mechanisms)} candidate mechanisms.")
    
    # 3. Run Step 13 Isomorphism Matcher
    print("\nRunning Step 13 Graph Isomorphism Matcher...")
    request = Step13Request(
        target_graph=target_graph,
        candidates=extracted_mechanisms
    )
    response = await match_graphs(request)
    
    print("\n--- MATCH RESULTS ---")
    for idx, match in enumerate(response.matches, 1):
        print(f"\nCandidate {idx}: {match.mechanism.source_result.title}")
        print(f"Nodes: {len(match.mechanism.causal_graph.nodes)}, Edges: {len(match.mechanism.causal_graph.edges)}")
        print(f"Isomorphism Score: {match.isomorphism_score:.2f}%")
        print(f"Match Classification: [{match.match_type.value}]")
        
        if match.match_type.value == "DISCARDED":
            print("Action: -> DISCARD (Below 30% threshold)")
        else:
            print("Action: -> KEPT (Passed to Step 14)")

if __name__ == "__main__":
    asyncio.run(main())
