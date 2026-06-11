import asyncio
import json

from schemas.layer3 import StructuralQuery
from services.layer3.step11_search_engine import run_step_11_search

async def main():
    print("Testing Layer 3 Step 11: 4 Layer Search Engine...")
    print("--------------------------------------------------")
    
    # 1. Create a mock StructuralQuery that would come from Step 10
    query = StructuralQuery(
        original_node_id="node_123",
        original_confidence=45.0,
        structural_description="two inputs shared bottleneck crash under combined load"
    )
    
    print(f"Domain Blind Query: '{query.structural_description}'")
    print("Running parallel search across 4 layers (Papers, Wiki, Web, Patents)...")
    
    # 2. Run the search engine
    response = await run_step_11_search(query)
    
    # 3. Print the deduplicated and merged results
    print("\n--- RESULTS ---")
    for idx, merged in enumerate(response.results, 1):
        print(f"\nResult {idx}: {merged.title}")
        print(f"Confidence: {merged.confidence:.2f}% (Boosted from {len(merged.sources)} sources)")
        print(f"Sources combined: {[s.value for s in merged.sources]}")
        print(f"Summary: {merged.merged_summary}")
        
        if merged.contradiction_analysis:
            print("\n  [CONTRADICTION DETECTED]")
            print(f"  Nature: {merged.contradiction_analysis.nature_of_conflict}")
            print(f"  Proposer: {merged.contradiction_analysis.debate_log.proposer_argument}")
            print(f"  Skeptic: {merged.contradiction_analysis.debate_log.skeptic_rebuttal}")
            print(f"  Synthesizer: {merged.contradiction_analysis.debate_log.synthesizer_consensus}")
            print(f"  Recommended Experiment: {merged.contradiction_analysis.recommended_experiment}")


if __name__ == "__main__":
    asyncio.run(main())
