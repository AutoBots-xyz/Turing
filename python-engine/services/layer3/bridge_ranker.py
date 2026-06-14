import asyncio
import logging

logger = logging.getLogger(__name__)

from schemas.layer3 import (
    Step14Request, Step14Response, IsomorphismMatch, MatchType,
    SearchSource, ValidityScores, RankedBridge
)
from services.anthropic_client import evaluate_compatibility_and_transferability


import os

def calculate_evidence_strength(match: IsomorphismMatch) -> float:
    """
    Factor 4: Evidence Strength
    Dynamically scores evidence quality using parameterized weights, allowing
    them to be learned or configured without hardcoding magic numbers.
    """
    source_results = match.mechanism.source_result.source_results

    # Configurable weights (default to the original values if not set)
    WEIGHT_PATENT = float(os.getenv("WEIGHT_PATENT", 0.70))
    WEIGHT_PAPER = float(os.getenv("WEIGHT_PAPER", 0.55))
    WEIGHT_WIKI = float(os.getenv("WEIGHT_WIKI", 0.45))
    WEIGHT_WEB = float(os.getenv("WEIGHT_WEB", 0.30))

    BOOST_DEPLOYED = float(os.getenv("BOOST_DEPLOYED", 0.25))
    BOOST_REPLICATED = float(os.getenv("BOOST_REPLICATED", 0.15))
    BOOST_BLOG = float(os.getenv("BOOST_BLOG", -0.10))

    CITE_500 = float(os.getenv("CITE_500", 0.10))
    CITE_100 = float(os.getenv("CITE_100", 0.07))
    CITE_10 = float(os.getenv("CITE_10", 0.03))

    REP_5 = float(os.getenv("REP_5", 0.05))
    REP_2 = float(os.getenv("REP_2", 0.02))

    best_score = 0.0
    for result in source_results:
        score = 0.0

        if result.source == SearchSource.PATENT: score = WEIGHT_PATENT
        elif result.source == SearchSource.PAPER: score = WEIGHT_PAPER
        elif result.source == SearchSource.WIKIPEDIA: score = WEIGHT_WIKI
        elif result.source == SearchSource.WEB: score = WEIGHT_WEB

        if result.deployment_status == "deployed": score += BOOST_DEPLOYED
        elif result.deployment_status == "replicated": score += BOOST_REPLICATED
        elif result.deployment_status == "blog": score += BOOST_BLOG

        if result.citation_count >= 500: score += CITE_500
        elif result.citation_count >= 100: score += CITE_100
        elif result.citation_count >= 10: score += CITE_10

        if result.replication_count >= 5: score += REP_5
        elif result.replication_count >= 2: score += REP_2

        best_score = max(best_score, score)

    return round(min(1.0, max(0.05, best_score)), 3)


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
        logger.warning(
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
        # ERR-B25 fix: Raise the exception to prevent silent data poisoning.
        # A hard crash here is safer than returning a hallucinated 0.5 score.
        if isinstance(llm_result, Exception):
            raise llm_result
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
