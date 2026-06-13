import asyncio
from typing import List
from schemas.layer3 import MergedResult
from services.agent_factory import AgentFactory


async def detect_contradictions(merged_results: List[MergedResult]) -> List[MergedResult]:
    """
    Step 11.5 Contradiction Detector:
    Passes merged findings to the 3-Agent Swarm (Proposer → Skeptic → Synthesizer)
    to debate and identify structural contradictions between sources.

    Fixes L3-3: MergedResult is a Pydantic v2 BaseModel which is frozen
        (immutable) by default. Direct assignment `merged.contradiction_analysis = x`
        raises `ValidationError: Instance is frozen`. Fixed by using
        `model_copy(update={...})` to produce a new immutable instance.
    """
    # Fixes ERR-B27: Filter the list first rather than appending dummy coroutines
    items_to_debate = [m for m in merged_results if len(m.source_results) > 1]

    debate_map = {}
    if items_to_debate:
        tasks = [AgentFactory.conduct_adversarial_debate(m.source_results) for m in items_to_debate]
        debates = await asyncio.gather(*tasks, return_exceptions=True)
        # Map the debate results back using the object ID as the key
        debate_map = {id(m): res for m, res in zip(items_to_debate, debates)}

    processed_results = []
    for merged in merged_results:
        debate_result = debate_map.get(id(merged))

        if isinstance(debate_result, Exception):
            # Log and continue — debate failure should not block the pipeline
            print(f"[contradiction_detector] Debate error for '{merged.title}': {debate_result}")
            processed_results.append(merged)
            continue

        if debate_result:
            # Fixes L3-3: model_copy(update=...) creates a new Pydantic v2 instance
            # instead of mutating the frozen model in place.
            updated = merged.model_copy(update={"contradiction_analysis": debate_result})
            processed_results.append(updated)
        else:
            processed_results.append(merged)

    return processed_results
