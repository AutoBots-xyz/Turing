"""
services/layer4/context_packager.py — Context Packager for Layer 4

Fixes Error 7 (Batch 4): This file was completely empty.
Converts the Top 3 RankedBridge objects into a rich, structured text prompt
that Claude can use to generate the FinalReport.
"""
from typing import List

from schemas.layer3 import RankedBridge


def pack_bridges_into_context(bridges: List[RankedBridge], user_query: str = "") -> str:
    """
    Converts the Top 3 ranked bridges into a structured, numbered context block
    for the report-generation LLM prompt.

    Each bridge section includes:
    - Title and match classification
    - Quantitative validity scores (all 4 factors)
    - The merged summary from Step 11
    - Any contradiction warnings from the Step 11.5 debate

    Parameters
    ----------
    bridges : List[RankedBridge]
        The ranked bridges from Step 14 (at most 3).
    user_query : str
        The original domain-blind structural description for context.

    Returns
    -------
    str
        A human-readable, structured context string ready to be injected
        into the report generation prompt.
    """
    sections = []

    if user_query:
        sections.append(f"USER PROBLEM (domain-blind structural description):\n{user_query}\n")

    sections.append(f"TOP {len(bridges)} CROSS-DOMAIN BRIDGES FOUND:\n{'='*60}")

    for rank, bridge in enumerate(bridges, 1):
        match = bridge.match
        scores = bridge.scores
        source = match.mechanism.source_result

        contradiction_block = ""
        if source.contradiction_analysis and source.contradiction_analysis.conflict_detected:
            debate = source.contradiction_analysis.debate_log
            contradiction_block = (
                f"\n  ⚠ CONTRADICTION DETECTED:\n"
                f"    Nature: {source.contradiction_analysis.nature_of_conflict}\n"
                f"    Proposer: {debate.proposer_argument}\n"
                f"    Skeptic: {debate.skeptic_rebuttal}\n"
                f"    Synthesizer consensus: {debate.synthesizer_consensus}\n"
                f"    Recommended experiment: {source.contradiction_analysis.recommended_experiment}"
            )

        source_list = ", ".join(s.value for s in source.sources)
        nodes_summary = ", ".join(
            n.label for n in match.mechanism.causal_graph.nodes[:5]
        )
        edges_summary = "; ".join(
            f"{e.source}→{e.target} [{e.relation}]"
            for e in match.mechanism.causal_graph.edges[:5]
        )

        section = (
            f"\nBRIDGE #{rank}: {source.title}\n"
            f"  Match type:     {match.match_type.value}\n"
            f"  Evidence from:  {source_list}\n"
            f"  Summary:        {source.merged_summary}\n"
            f"  Causal nodes:   {nodes_summary or 'N/A'}\n"
            f"  Causal edges:   {edges_summary or 'N/A'}\n"
            f"  Scores:\n"
            f"    Structural match:         {scores.structural_match:.2f}\n"
            f"    Constraint compatibility: {scores.constraint_compatibility:.2f}\n"
            f"    Solution transferability: {scores.solution_transferability:.2f}\n"
            f"    Evidence strength:        {scores.evidence_strength:.2f}\n"
            f"    FINAL SCORE:              {scores.final_score:.4f}"
            f"{contradiction_block}"
        )
        sections.append(section)

    return "\n".join(sections)
