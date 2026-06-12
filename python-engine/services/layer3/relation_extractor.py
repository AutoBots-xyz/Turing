import asyncio
from typing import List

from schemas.layer3 import MergedResult, ExtractedMechanism
from services.anthropic_client import extract_causal_graph_from_text

async def run_relation_extraction(results: List[MergedResult]) -> List[ExtractedMechanism]:
    """
    Step 12: Relation Extraction
    Reads every result from Step 11/11.5 and uses Claude to extract causal relationships
    as mini graphs, extracting Nouns as Nodes and Verbs as Edges, with confidence scores.
    """
    
    extracted_mechanisms = []
    
    # We can process these concurrently
    tasks = []
    for merged in results:
        # If there's a contradiction, we want to extract graphs from BOTH the main
        # mechanism and the contradictory one so the engine can evaluate both.
        # For this prototype, we'll just pass the full merged summary (and any debate context)
        # to the LLM and let it figure out the nodes and edges.
        
        context_text = merged.merged_summary
        
        if merged.contradiction_analysis and merged.contradiction_analysis.conflict_detected:
            # Append the contradictory source's summary to the context text
            # so the LLM extracts the conflicting edges as well
            context_text += f"\nContradicting View: {merged.contradiction_analysis.debate_log.skeptic_rebuttal}"
            
        tasks.append(extract_causal_graph_from_text(context_text))
        
    extracted_graphs = await asyncio.gather(*tasks)
    
    for merged, graph in zip(results, extracted_graphs):
        extracted_mechanisms.append(ExtractedMechanism(
            source_result=merged,
            causal_graph=graph
        ))
        
    return extracted_mechanisms
