import asyncio

from schemas.layer3 import StructuralQuery, Step12Request
from services.layer3.step11_search_engine import run_step_11_search
from services.layer3.relation_extractor import run_relation_extraction

async def main():
    print("Testing Layer 3 Step 12: Relation Extraction (Text Path)...")
    print("----------------------------------------------------------")
    
    # 1. Run Step 11 to get the mock deduplicated results
    query = StructuralQuery(
        original_node_id="node_123",
        original_confidence=45.0,
        structural_description="two inputs shared bottleneck crash under combined load"
    )
    print("Running Step 11 Search Engine to get text summaries...")
    step11_response = await run_step_11_search(query)
    
    # 2. Feed those text summaries into Step 12
    print("\nRunning Step 12 Relation Extraction...")
    extracted_mechanisms = await run_relation_extraction(step11_response.results)
    
    # 3. Print the resulting Causal Graphs
    print("\n--- EXTRACTED GRAPHS ---")
    for idx, em in enumerate(extracted_mechanisms, 1):
        print(f"\nMechanism {idx} (from '{em.source_result.title}')")
        
        print("  Nodes (Nouns):")
        for node in em.causal_graph.nodes:
            print(f"    - {node.label} (Confidence: {node.confidence:.2f}%)")
            
        print("  Edges (Verbs):")
        for edge in em.causal_graph.edges:
            # Look up node labels for clearer printing
            src_label = next(n.label for n in em.causal_graph.nodes if n.id == edge.source)
            tgt_label = next(n.label for n in em.causal_graph.nodes if n.id == edge.target)
            print(f"    - {src_label} --[{edge.relation}]--> {tgt_label} (Confidence: {edge.confidence:.2f}%)")

if __name__ == "__main__":
    asyncio.run(main())
