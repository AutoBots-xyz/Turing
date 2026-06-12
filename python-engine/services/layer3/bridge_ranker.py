import asyncio

from schemas.layer3 import Step14Request, Step14Response, IsomorphismMatch, MatchType, SearchSource, ValidityScores, RankedBridge
from services.anthropic_client import evaluate_compatibility_and_transferability

def calculate_evidence_strength(match: IsomorphismMatch) -> float:
    """
    Factor 4: Evidence Strength
    Scores evidence based on the sources that contributed to the extracted mechanism.
    """
    sources = match.mechanism.source_result.sources
    
    if SearchSource.PATENT in sources:
        return 0.95  # Deployed in production / legal precise mechanisms -> highest
    elif SearchSource.PAPER in sources:
        return 0.90  # Academic papers -> very high
    elif SearchSource.WIKIPEDIA in sources:
        return 0.75  # Established knowledge -> high/medium
    elif SearchSource.WEB in sources:
        return 0.50  # Industry whitepapers/blogs -> medium/low
        
    return 0.30

async def rank_bridges(request: Step14Request) -> Step14Response:
    """
    Step 14: Bridge Validity Ranker
    Scores surviving matches on 4 factors and returns the Top 3.
    """
    ranked_bridges = []
    
    # Filter out discarded matches
    valid_matches = [m for m in request.matches if m.match_type != MatchType.DISCARDED]
    
    tasks = []
    for match in valid_matches:
        # We need context string representing the candidate mechanism
        candidate_mechanism_str = match.mechanism.source_result.merged_summary
        
        # Simulate LLM extracting Factor 2 & Factor 3
        # In reality, we'd pass the target domain context too
        tasks.append(evaluate_compatibility_and_transferability("Domain context", candidate_mechanism_str))
        
    llm_scores = await asyncio.gather(*tasks)
    
    for match, (compatibility, transferability) in zip(valid_matches, llm_scores):
        # Factor 1: Structural Match (from Step 13, convert percentage to 0.0-1.0 float)
        structural_match = match.isomorphism_score / 100.0
        
        # Factor 4: Evidence Strength
        evidence = calculate_evidence_strength(match)
        
        # Final Score (Geometric product)
        final_score = structural_match * compatibility * transferability * evidence
        
        scores = ValidityScores(
            structural_match=structural_match,
            constraint_compatibility=compatibility,
            solution_transferability=transferability,
            evidence_strength=evidence,
            final_score=final_score
        )
        
        ranked_bridges.append(RankedBridge(match=match, scores=scores))
        
    # Sort descending by final score
    ranked_bridges.sort(key=lambda x: x.scores.final_score, reverse=True)
    
    # Return Top 3
    return Step14Response(top_bridges=ranked_bridges[:3])
