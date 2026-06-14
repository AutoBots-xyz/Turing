import asyncio
from typing import List
from schemas.layer3 import MergedResult
from services.agent_factory import AgentFactory


# dummy coroutine removed


async def detect_contradictions(merged_results: List[MergedResult]) -> List[MergedResult]:
    """
    Step 11.5 Contradiction Detector:
    Passes merged findings to the 3-Agent Swarm (Proposer → Skeptic → Synthesizer)
    to debate and identify structural contradictions between sources.

    Fixes L3-2 / ERR-B27: No longer uses a dummy coroutine to satisfy asyncio.gather.
    Properly filters the list to only include multi-source results before gathering.

    Fixes L3-3: MergedResult is a Pydantic v2 BaseModel which is frozen
    (immutable) by default. Direct assignment `merged.contradiction_analysis = x`
    raises `ValidationError: Instance is frozen`. Fixed by using
    `model_copy(update={...})` to produce a new immutable instance.
    """
    debate_tasks = []
    debate_indices = []

    for idx, merged in enumerate(merged_results):
        if len(merged.source_results) > 1:
            debate_tasks.append(AgentFactory.conduct_adversarial_debate(merged.source_results))
            debate_indices.append(idx)

    # return_exceptions=True ensures one failed debate doesn't kill the whole batch
    debates = await asyncio.gather(*debate_tasks, return_exceptions=True) if debate_tasks else []

    # Reconstruct results
    debate_map = dict(zip(debate_indices, debates))
    
    processed_results = []
    for idx, merged in enumerate(merged_results):
        if idx in debate_map:
            debate_result = debate_map[idx]
            if isinstance(debate_result, Exception):
                print(f"[contradiction_detector] Debate error for '{merged.title}': {debate_result}")
                processed_results.append(merged)
            elif debate_result is not None:
                updated = merged.model_copy(update={"contradiction_analysis": debate_result})
                processed_results.append(updated)
            else:
                processed_results.append(merged)
        else:
            processed_results.append(merged)

    return processed_results
