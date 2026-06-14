import asyncio
from typing import List

from schemas.graph import CausalGraph
from schemas.layer3 import MergedResult, ExtractedMechanism
from services.anthropic_client import extract_causal_graph_from_text


async def run_relation_extraction(results: List[MergedResult]) -> List[ExtractedMechanism]:
    """
    Step 12: Relation Extraction
    Reads every result from Step 11/11.5 and uses Claude to extract causal relationships
    as mini graphs, extracting Nouns as Nodes and Verbs as Edges, with confidence scores.

    Fixes Error 1: asyncio.gather now uses return_exceptions=True so a single
    LLM failure does not kill the entire pipeline. Failed extractions fall back
    to an empty CausalGraph.

    Fixes Error 2: When a contradiction is detected, TWO separate LLM calls are
    made — one for the primary mechanism and one for the contradicting view.
    Both are returned as independent ExtractedMechanism objects so the
    isomorphism matcher can evaluate them independently.
    """

    # Build tasks: each MergedResult produces 1 or 2 LLM calls.
    # We track which (merged, is_contradiction_side) pair each task maps to.
    task_map: List[tuple] = []   # (merged, is_contradiction_side)
    tasks = []

    for merged in results:
        # Primary mechanism call — always present
        tasks.append(extract_causal_graph_from_text(merged.merged_summary))
        task_map.append((merged, False))

        # Secondary (contradiction) call — only when a real conflict was detected
        if merged.contradiction_analysis and merged.contradiction_analysis.conflict_detected:
            contradiction_text = (
                f"This is an ALTERNATIVE / CONTRADICTING mechanism for the same phenomenon.\n"
                f"Contradicting view: {merged.contradiction_analysis.debate_log.skeptic_rebuttal}\n\n"
                f"Original context: {merged.merged_summary}"
            )
            tasks.append(extract_causal_graph_from_text(contradiction_text))
            task_map.append((merged, True))

    # --- Fixes Error 1: return_exceptions=True prevents one failure from killing all ---
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    extracted_mechanisms: List[ExtractedMechanism] = []

    for (merged, is_contradiction_side), graph_or_exc in zip(task_map, raw_results):
        if isinstance(graph_or_exc, Exception):
            # Graceful fallback — an empty graph is better than a crashed pipeline
            graph = CausalGraph(nodes=[], edges=[])
        else:
            graph = graph_or_exc

        extracted_mechanisms.append(ExtractedMechanism(
            source_result=merged,
            causal_graph=graph
        ))

    return extracted_mechanisms
