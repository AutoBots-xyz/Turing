import asyncio

from schemas.graph import CausalGraph, Node, Edge
from schemas.layer3 import StructuralQuery, Step14Request
from services.layer3.step11_search_engine import run_step_11_search
from services.layer3.relation_extractor import run_relation_extraction
from services.layer3.isomorphism_matcher import match_graphs, Step13Request
from services.layer3.bridge_ranker import rank_bridges

async def main():
    print("Testing Layer 3 Step 14: Bridge Validity Ranker...")
    print("--------------------------------------------------")
    
    # 1. Define Target Graph
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
    
    # 2. Run Pipeline Steps 11 -> 12 -> 13
    query = StructuralQuery(
        original_node_id="C",
        original_confidence=45.0,
        structural_description="two inputs shared bottleneck crash under combined load"
    )
    
    print("Running Steps 11, 12, 13 to generate Isomorphism Matches...")
    step11_response = await run_step_11_search(query)
    extracted_mechanisms = await run_relation_extraction(step11_response.results)
    
    step13_request = Step13Request(target_graph=target_graph, candidates=extracted_mechanisms)
    step13_response = await match_graphs(step13_request)
    
    print(f"Generated {len(step13_response.matches)} candidate matches.")
    
    # 3. Run Step 14
    print("\nRunning Step 14 Bridge Validity Ranker...")
    step14_request = Step14Request(matches=step13_response.matches)
    step14_response = await rank_bridges(step14_request)
    
    print("\n--- FINAL LAYER 3 OUTPUT (TOP BRIDGES) ---")
    for idx, ranked_bridge in enumerate(step14_response.top_bridges, 1):
        print(f"\nRank #{idx}: {ranked_bridge.match.mechanism.source_result.title}")
        print(f"Match Type: {ranked_bridge.match.match_type.value}")
        print(f"Sources: {[s.value for s in ranked_bridge.match.mechanism.source_result.sources]}")
        
        scores = ranked_bridge.scores
        print(f"\nValidity Scores:")
        print(f"  - Structural Match:         {scores.structural_match:.2f}")
        print(f"  - Constraint Compatibility: {scores.constraint_compatibility:.2f}")
        print(f"  - Solution Transferability: {scores.solution_transferability:.2f}")
        print(f"  - Evidence Strength:        {scores.evidence_strength:.2f}")
        print(f"  =====================================")
        print(f"  FINAL SCORE (Product):      {scores.final_score:.4f}")
        
        # Check for contradiction analysis
        analysis = ranked_bridge.match.mechanism.source_result.contradiction_analysis
        if analysis and analysis.conflict_detected:
            print(f"\n[!] WARNING: This bridge contains conflicting evidence.")
            print(f"    Debate Synthesizer: {analysis.debate_log.synthesizer_consensus}")

if __name__ == "__main__":
    asyncio.run(main())
