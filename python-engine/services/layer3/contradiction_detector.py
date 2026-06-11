import asyncio
from typing import List
from schemas.layer3 import MergedResult
from services.agent_factory import AgentFactory

async def detect_contradictions(merged_results: List[MergedResult]) -> List[MergedResult]:
    """
    Step 11.5 Contradiction Detector:
    Passes merged findings to the 3-Agent Swarm to debate and identify structural contradictions.
    """
    processed_results = []
    
    # We run the debate concurrently for all grouped results
    tasks = []
    for merged in merged_results:
        if len(merged.source_results) > 1:
            tasks.append(AgentFactory.conduct_adversarial_debate(merged.source_results))
        else:
            # If only one source, there's no contradiction to debate
            tasks.append(asyncio.sleep(0, result=None))
            
    debates = await asyncio.gather(*tasks)
    
    for merged, debate_details in zip(merged_results, debates):
        if debate_details:
            merged.contradiction_analysis = debate_details
        processed_results.append(merged)
        
    return processed_results
