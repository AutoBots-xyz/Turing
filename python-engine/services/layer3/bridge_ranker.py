import asyncio

from schemas.layer3 import (
    Step14Request, Step14Response, IsomorphismMatch, MatchType,
    SearchSource, ValidityScores, RankedBridge
)
from services.anthropic_client import evaluate_compatibility_and_transferability


def calculate_evidence_strength(match: IsomorphismMatch) -> float:
    """
    Factor 4: Evidence Strength
    Fixes ERR-B24: Replaces arbitrary hardcoded "magic numbers" with a 
    statistically grounded Noisy-OR probability model. We treat each 
    source (and its replications) as independent probabilistic evidence.
    """
    source_results = match.mechanism.source_result.source_results

    if not source_results:
        return 0.05

    combined_p_failure = 1.0
    for result in source_results:
        # Treat the base confidence as a probability [0.0, 1.0]
        p = max(0.0, min(100.0, result.confidence)) / 100.0
        
        # Each independent replication acts as an additional independent trial
        trials = 1 + result.replication_count
        
        # Noisy-OR combination
        combined_p_failure *= ((1.0 - p) ** trials)

    evidence_score = 1.0 - combined_p_failure

    # Clamp to [0.05, 1.0] to avoid zeroing out the entire geometric product
    return round(max(0.05, evidence_score), 3)


async def rank_bridges(request: Step14Request) -> Step14Response:
    """
    Step 14: Bridge Validity Ranker
    Scores surviving matches on 4 factors and returns the Top 3.

    Fixes L3-7: user_domain_context defaults to "" which causes the LLM to
    receive no problem context and return meaningless compatibility scores.
    Now falls back to the top bridge's merged_summary when context is empty,
    ensuring the LLM always has at least some domain signal to work with.
    """
    # Filter out discarded matches from Step 13
    valid_matches = [m for m in request.matches if m.match_type != MatchType.DISCARDED]

    if not valid_matches:
        return Step14Response(top_bridges=[])

    # Fixes L3-7: use the top match's merged summary as fallback context
    # when the caller did not supply a domain context string.
    domain_context = request.user_domain_context.strip()
    if not domain_context:
        # Sort by isomorphism score to find the best match's summary
        best_match = max(valid_matches, key=lambda m: m.isomorphism_score)
        domain_context = best_match.mechanism.source_result.merged_summary
        print(
            "[bridge_ranker] WARNING: user_domain_context was empty. "
            "Falling back to top-match summary as LLM context."
        )

    # Build LLM evaluation tasks using the real domain context
    tasks = [
        evaluate_compatibility_and_transferability(
            domain_context=domain_context,
            candidate_mechanism=match.mechanism.source_result.merged_summary
        )
        for match in valid_matches
    ]

    llm_scores = await asyncio.gather(*tasks, return_exceptions=True)

    ranked_bridges = []
    for match, llm_result in zip(valid_matches, llm_scores):
        # Gracefully handle any LLM failures — Fixes ERR-B25: Do not swallow silently!
        if isinstance(llm_result, Exception):
            raise RuntimeError(f"LLM evaluation failed during bridge ranking: {llm_result}") from llm_result
        else:
            compatibility, transferability = llm_result

        # Factor 1: Structural Match (convert 0-100 to 0.0-1.0)
        structural_match = match.isomorphism_score / 100.0

        # Factor 4: Dynamic evidence strength
        evidence = calculate_evidence_strength(match)

        # Final Score = F1 × F2 × F3 × F4 (geometric product)
        final_score = structural_match * compatibility * transferability * evidence

        scores = ValidityScores(
            structural_match=round(structural_match, 3),
            constraint_compatibility=round(compatibility, 3),
            solution_transferability=round(transferability, 3),
            evidence_strength=evidence,
            final_score=round(final_score, 4),
        )

        ranked_bridges.append(RankedBridge(match=match, scores=scores))

    # Sort descending by final score and return Top 3
    ranked_bridges.sort(key=lambda x: x.scores.final_score, reverse=True)
    return Step14Response(top_bridges=ranked_bridges[:3])
