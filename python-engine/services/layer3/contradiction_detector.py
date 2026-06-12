import asyncio
from typing import List
from schemas.layer3 import MergedResult
from services.agent_factory import AgentFactory


async def _no_debate():
    """
    Placeholder coroutine returned for single-source results that have no
    contradicting source to debate against.

    Fixes L3-2: replaces the invalid `asyncio.sleep(0, result=None)` call
    (asyncio.sleep does NOT accept a `result` keyword argument — that API
    belongs to asyncio.Future/Task, not sleep). This crashes with:
        TypeError: sleep() got an unexpected keyword argument 'result'
    """
    return None


async def detect_contradictions(merged_results: List[MergedResult]) -> List[MergedResult]:
    """
    Step 11.5 Contradiction Detector:
    Passes merged findings to the 3-Agent Swarm (Proposer → Skeptic → Synthesizer)
    to debate and identify structural contradictions between sources.

    Fixes L3-2: Uses a proper `_no_debate()` coroutine instead of the invalid
        `asyncio.sleep(0, result=None)` call.

    Fixes L3-3: MergedResult is a Pydantic v2 BaseModel which is frozen
        (immutable) by default. Direct assignment `merged.contradiction_analysis = x`
        raises `ValidationError: Instance is frozen`. Fixed by using
        `model_copy(update={...})` to produce a new immutable instance.
    """
    tasks = []
    for merged in merged_results:
        if len(merged.source_results) > 1:
            # Run the full 3-agent debate when multiple sources exist
            tasks.append(AgentFactory.conduct_adversarial_debate(merged.source_results))
        else:
            # Single source — nothing to debate, return None
            tasks.append(_no_debate())

    # return_exceptions=True ensures one failed debate doesn't kill the whole batch
    debates = await asyncio.gather(*tasks, return_exceptions=True)

    processed_results = []
    for merged, debate_result in zip(merged_results, debates):
        if isinstance(debate_result, Exception):
            # Log and continue — debate failure should not block the pipeline
            print(f"[contradiction_detector] Debate error for '{merged.title}': {debate_result}")
            processed_results.append(merged)
            continue

        if debate_result is not None:
            # Fixes L3-3: model_copy(update=...) creates a new Pydantic v2 instance
            # instead of mutating the frozen model in place.
            updated = merged.model_copy(update={"contradiction_analysis": debate_result})
            processed_results.append(updated)
        else:
            processed_results.append(merged)

    return processed_results
