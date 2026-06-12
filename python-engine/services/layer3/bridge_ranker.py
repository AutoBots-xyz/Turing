import asyncio

from schemas.layer3 import (
    Step14Request, Step14Response, IsomorphismMatch, MatchType,
    SearchSource, ValidityScores, RankedBridge
)
from services.anthropic_client import evaluate_compatibility_and_transferability


def calculate_evidence_strength(match: IsomorphismMatch) -> float:
    """
    Factor 4: Evidence Strength
    Fixes Error 6: Dynamically scores evidence quality based on real
    signals from SearchResult — citation count, replication count, and
    deployment status — rather than static hardcoded floats per source type.

    Scoring table (from layer 3.md):
    - Boeing patent deployed in 10,000 flights → highest
    - Paper replicated 5+ times → very high
    - Paper cited 100+ times → high
    - Single unreplicated paper → low
    - Blog post → very low
    """
    # Gather all underlying SearchResult objects from this merged mechanism
    source_results = match.mechanism.source_result.source_results

    best_score = 0.0
    for result in source_results:
        score = 0.0

        # Base score from source type
        if result.source == SearchSource.PATENT:
            score = 0.70
        elif result.source == SearchSource.PAPER:
            score = 0.55
        elif result.source == SearchSource.WIKIPEDIA:
            score = 0.45
        elif result.source == SearchSource.WEB:
            score = 0.30

        # Boost from deployment status
        if result.deployment_status == "deployed":
            score += 0.25
        elif result.deployment_status == "replicated":
            score += 0.15
        elif result.deployment_status == "single_study":
            score += 0.00
        elif result.deployment_status == "blog":
            score -= 0.10

        # Boost from citation count (capped at 0.10)
        if result.citation_count >= 500:
            score += 0.10
        elif result.citation_count >= 100:
            score += 0.07
        elif result.citation_count >= 10:
            score += 0.03

        # Boost from independent replication (capped at 0.05)
        if result.replication_count >= 5:
            score += 0.05
        elif result.replication_count >= 2:
            score += 0.02

        best_score = max(best_score, score)

    # Clamp to [0.05, 1.0]
    return round(min(1.0, max(0.05, best_score)), 3)


async def rank_bridges(request: Step14Request) -> Step14Response:
    """
    Step 14: Bridge Validity Ranker
    Scores surviving matches on 4 factors and returns the Top 3.
    Fixes Error 7: Passes the real user_domain_context from the request
    to the LLM evaluator instead of the placeholder "Domain context" string.
    """
    ranked_bridges = []

    # Filter out discarded matches from Step 13
    valid_matches = [m for m in request.matches if m.match_type != MatchType.DISCARDED]

    if not valid_matches:
        return Step14Response(top_bridges=[])

    # Build LLM evaluation tasks using the real domain context (Error 7 fix)
    tasks = [
        evaluate_compatibility_and_transferability(
            domain_context=request.user_domain_context,
            candidate_mechanism=match.mechanism.source_result.merged_summary
        )
        for match in valid_matches
    ]

    llm_scores = await asyncio.gather(*tasks, return_exceptions=True)

    for match, llm_result in zip(valid_matches, llm_scores):
        # Gracefully handle any LLM failures — don't let one bad result kill the whole pipeline
        if isinstance(llm_result, Exception):
            compatibility, transferability = 0.5, 0.5
        else:
            compatibility, transferability = llm_result

        # Factor 1: Structural Match (from Step 13 — convert 0-100 to 0.0-1.0)
        structural_match = match.isomorphism_score / 100.0

        # Factor 4: Dynamic evidence strength
        evidence = calculate_evidence_strength(match)

        # Final Score = F1 × F2 × F3 × F4 (geometric product as defined in layer 3.md)
        final_score = structural_match * compatibility * transferability * evidence

        scores = ValidityScores(
            structural_match=round(structural_match, 3),
            constraint_compatibility=round(compatibility, 3),
            solution_transferability=round(transferability, 3),
            evidence_strength=evidence,
            final_score=round(final_score, 4)
        )

        ranked_bridges.append(RankedBridge(match=match, scores=scores))

    # Sort descending by final score and return Top 3
    ranked_bridges.sort(key=lambda x: x.scores.final_score, reverse=True)
    return Step14Response(top_bridges=ranked_bridges[:3])
